# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class PropertyProperty(models.Model):
    """Extend property model to validate unique house numbers within same floor and site"""
    
    _inherit = "property.property"

    @api.model
    def _normalize_unit_number(self, value):
        """Normalize unit numbers so '8' and '08' are treated the same."""
        if not value:
            return ''
        s = str(value).strip()
        if not s:
            return ''
        # If purely digits, normalize by integer value (removes leading zeros)
        if s.isdigit():
            try:
                return str(int(s))
            except Exception:
                return s.lstrip('0') or '0'
        # For mixed values (e.g. A08), normalize common spacing/casing only
        return s.upper()

    @api.model
    def _extract_m2m_ids(self, value):
        """Return a flat list of integer ids from M2M commands or id lists."""
        if not value:
            return []
        # Already a recordset
        if hasattr(value, 'ids'):
            return list(value.ids)
        # Direct list of ints
        if isinstance(value, (list, tuple)) and value and all(isinstance(x, int) for x in value):
            return list(value)
        # Command list
        if isinstance(value, (list, tuple)):
            ids = []
            for command in value:
                if not isinstance(command, (list, tuple)) or not command:
                    continue
                if command[0] == 6:  # replace
                    ids = list(command[2]) if len(command) > 2 and isinstance(command[2], (list, tuple)) else []
                elif command[0] == 4:  # link to existing id
                    if len(command) > 1 and isinstance(command[1], int):
                        ids.append(command[1])
            # Flatten any accidental nested lists
            flat = []
            for x in ids:
                if isinstance(x, int):
                    flat.append(x)
                elif isinstance(x, (list, tuple)):
                    flat.extend([i for i in x if isinstance(i, int)])
            return flat
        return []

    @api.constrains('unit_number', 'floor_ids', 'site', 'block')
    def _check_unique_house_number_per_floor_and_site(self):
        """Validate that house numbers are unique within the same floor AND same site"""
        for record in self:
            self._validate_house_number_uniqueness(record)

    @api.model
    def create(self, vals):
        """Override create to validate before creation"""
        # Check for duplicates before creating
        self._validate_duplicates_before_save(vals)
        return super().create(vals)

    def write(self, vals):
        """Override write to validate before updating"""
        # Check for duplicates before writing
        for record in self:
            # Create a copy of vals with current values for missing fields
            check_vals = vals.copy()
            if 'unit_number' not in check_vals:
                check_vals['unit_number'] = record.unit_number
            if 'site' not in check_vals:
                check_vals['site'] = record.site.id if record.site else False
            if 'block' not in check_vals:
                check_vals['block'] = record.block.id if record.block else False
            if 'floor_ids' not in check_vals:
                check_vals['floor_ids'] = [(6, 0, record.floor_ids.ids)] if record.floor_ids else False
            
            self._validate_duplicates_before_save(check_vals, record.id)
        
        return super().write(vals)

    def _validate_duplicates_before_save(self, vals, exclude_id=None):
        """Validate duplicates before save operation"""
        # Extract values from vals
        unit_number = vals.get('unit_number')
        site_id = vals.get('site')
        block_id = vals.get('block')
        floor_id = vals.get('floor_id')
        floor_ids = vals.get('floor_ids')
        
        # Skip if missing required fields
        if not unit_number or not site_id or not block_id:
            return

        floors = []
        if isinstance(floor_id, int) and floor_id:
            floors = [floor_id]
        else:
            floors = self._extract_m2m_ids(floor_ids)

        if not floors:
            return
        
        normalized = self._normalize_unit_number(unit_number)

        # Check for any floor in the list (use stored floor_id, not floor_ids which is store=False)
        for fl_id in floors:
            floor_domain = [
                ('site', '=', site_id),
                ('block', '=', block_id),
                ('floor_id', '=', fl_id),
                ('unit_number', '!=', False),
            ]
            if exclude_id:
                floor_domain.append(('id', '!=', exclude_id))
            
            candidates = self.search(floor_domain)
            duplicates = candidates.filtered(lambda r: self._normalize_unit_number(r.unit_number) == normalized)
            if duplicates:
                # Get floor name
                floor = self.env['property.floor'].browse(fl_id)
                floor_name = floor.display_name or _("Floor %s") % fl_id
                
                # Get block name
                block = self.env['property.block'].browse(block_id)
                block_name = block.display_name or f"Block {block_id}"
                
                # Get site name
                site = self.env['property.site'].browse(site_id)
                site_name = site.display_name or f"Site {site_id}"
                
                # Human readable message
                raise ValidationError(
                    _(
                        "Duplicate house number.\n\n"
                        "House number '%(unit)s' already exists on floor '%(floor)s' in block '%(block)s', site '%(site)s'.\n"
                        "Choose a different house number for this floor and block."
                    )
                    % {'unit': unit_number, 'floor': floor_name, 'block': block_name, 'site': site_name}
                )

    def _validate_house_number_uniqueness(self, record):
        """Helper method to validate uniqueness"""
        if not record.unit_number or not record.site or not record.block:
            return

        normalized = self._normalize_unit_number(record.unit_number)

        floors = record.floor_id or record.floor_ids
        if not floors:
            return

        # For each floor in the property (search using stored floor_id)
        for floor in floors:
            # Search for other properties with:
            # - Same site
            # - Same block
            # - Same floor
            # - Same unit number
            candidates = self.search([
                ('id', '!=', record.id),
                ('site', '=', record.site.id),
                ('block', '=', record.block.id),
                ('floor_id', '=', floor.id),
                ('unit_number', '!=', False),
            ])

            duplicate_properties = candidates.filtered(lambda r: self._normalize_unit_number(r.unit_number) == normalized)
            if duplicate_properties:
                # Get the names/locations of duplicate properties
                duplicate_names = ', '.join(duplicate_properties.mapped('name'))
                site_name = record.site.display_name
                block_name = record.block.display_name or "Unknown Block"
                floor_name = floor.display_name or "Unknown Floor"

                # Human readable message
                raise ValidationError(
                    _(
                        "Duplicate house number.\n\n"
                        "House number '%(unit)s' already exists on floor '%(floor)s' in block '%(block)s', site '%(site)s'.\n"
                        "Already used by: %(dupes)s\n\n"
                        "Choose a different house number for this floor and block."
                    )
                    % {'unit': record.unit_number, 'floor': floor_name, 'block': block_name, 'site': site_name, 'dupes': duplicate_names}
                )

    @api.onchange('unit_number', 'floor_ids', 'site', 'block')
    def _onchange_house_number_validation(self):
        """Real-time warning when unit number, floor, site, or block changes"""
        floors = self.floor_id or self.floor_ids
        if self.unit_number and floors and self.site and self.block:
            normalized = self._normalize_unit_number(self.unit_number)
            for floor in floors:
                candidates = self.search([
                    ('id', '!=', self.id or 0),
                    ('site', '=', self.site.id),
                    ('block', '=', self.block.id),
                    ('floor_id', '=', floor.id),
                    ('unit_number', '!=', False),
                ])

                duplicate_properties = candidates.filtered(lambda r: self._normalize_unit_number(r.unit_number) == normalized)
                if duplicate_properties:
                    site_name = self.site.display_name
                    block_name = self.block.display_name or "Unknown Block"
                    floor_name = floor.display_name or "Unknown Floor"
                    duplicate_names = ', '.join(duplicate_properties.mapped('name'))
                    
                    # Human readable message
                    return {
                        'warning': {
                            'title': _('Duplicate house number'),
                            'message': (
                                _(
                                    "House number '%(unit)s' already exists on floor '%(floor)s' in block '%(block)s', site '%(site)s'.\n"
                                    "Used by: %(dupes)s\n\n"
                                    "You cannot save until you change the house number."
                                )
                                % {'unit': self.unit_number, 'floor': floor_name, 'block': block_name, 'site': site_name, 'dupes': duplicate_names}
                            ),
                        }
                    }