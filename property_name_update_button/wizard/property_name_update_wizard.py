# -*- coding: utf-8 -*-
import re
import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class PropertyNameUpdateWizard(models.TransientModel):
    _name = 'property.name.update.wizard'
    _description = 'Update Property Name & Reference Number'

    property_id = fields.Many2one('property.property', string='Property', required=True, readonly=True)

    current_name = fields.Char(string='Current Name', readonly=True)
    current_reference = fields.Char(string='Current Reference', readonly=True)

    new_name = fields.Char(string='New Name', required=True)
    new_reference = fields.Char(string='New Reference')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        prop_id = self.env.context.get('default_property_id')
        if prop_id:
            prop = self.env['property.property'].browse(prop_id)
            res['property_id'] = prop.id
            res['current_name'] = prop.name
            res['current_reference'] = getattr(prop, 'computed_reference', None) or prop.code or ''
            res['new_name'] = self._generate_name(prop)
            # Prefer the already-stored computed_reference to avoid logic discrepancy
            res['new_reference'] = getattr(prop, 'computed_reference', None) or self._generate_reference(prop)
        return res

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _get_unit(self, prop):
        """Return unit number: prefer unit_number field, else extract from existing name."""
        unit = (getattr(prop, 'unit_number', None) or '').strip()
        if unit:
            return unit
        # Fall back: last segment of the current name after the last '-'
        if prop.name and prop.name != _('New'):
            parts = prop.name.strip().split('-')
            if len(parts) >= 2:
                candidate = parts[-1].strip()
                if candidate:
                    return candidate
        return ''

    def _get_floor(self, prop):
        """Return floor name from floor_id (stored Many2one) or first of floor_ids."""
        floor_id = getattr(prop, 'floor_id', None)
        if floor_id and floor_id.name:
            return floor_id.name
        floor_ids = getattr(prop, 'floor_ids', None)
        if floor_ids:
            return floor_ids[0].name or ''
        return ''

    # ── Name generation ──────────────────────────────────────────────────────
    def _generate_name(self, prop):
        if not prop.site or not prop.block:
            return prop.name or _('New')

        site = prop.site.name or ''
        block = prop.block.name or ''
        floor = self._get_floor(prop)
        unit = self._get_unit(prop)

        parts = [site, block]
        if floor:
            parts.append(f'F{floor}')
        if unit:
            parts.append(unit)
        return '-'.join(parts)

    # ── Reference generation ─────────────────────────────────────────────────
    def _generate_reference(self, prop):
        if not prop.site:
            return ''

        unit = self._get_unit(prop)
        if not unit:
            return ''

        try:
            # 1. Site code — first 3 alphanumeric chars of site name
            site_name = prop.site.name or ''
            clean_site = re.sub(r'[^A-Za-z0-9]', '', site_name.strip())
            site_code = clean_site[:3].upper() if clean_site else ''
            if not site_code:
                return ''

            # 2. Owner code — from site company abbreviation
            owner_code = ''
            site_company = getattr(prop.site, 'company_id', None)
            if site_company:
                abbr = getattr(site_company, 'abbreviation', None)
                if abbr and abbr.strip():
                    owner_code = re.sub(r'[^A-Za-z0-9]', '', abbr.strip().upper())
                elif getattr(site_company, 'name', None):
                    owner_code = re.sub(r'[^A-Za-z0-9]', '', site_company.name.strip())[:3].upper()

            # 3. Project number
            project_no = str(getattr(prop.site, 'project_number', '') or '').strip()

            # 4. Block number — extract digits, zero-pad to 2; else first 2 chars
            block_no = ''
            if prop.block and prop.block.name:
                nums = re.findall(r'\d+', prop.block.name)
                block_no = nums[0].zfill(2) if nums else prop.block.name[:2].upper()

            # 5. Floor number — from floor_id or floor_ids
            floor_no = ''
            floor_name = self._get_floor(prop)
            if floor_name:
                nums = re.findall(r'\d+', floor_name)
                floor_no = f'F{nums[0]}' if nums else floor_name[:3].upper()

            # 6. Unit number — extract digits, zero-pad; else use as-is
            nums = re.findall(r'\d+', unit)
            unit_no = nums[0].zfill(2) if nums else unit.upper()[:3]

            # Build reference
            parts = [site_code]
            if owner_code:
                parts.append(f'-{owner_code}')
                if project_no:
                    parts.append(project_no)

            location_parts = [p for p in [block_no, floor_no] if p]
            if location_parts:
                parts.append('/' + '/'.join(location_parts))

            suffix = ''
            if getattr(prop, 'property_type', '') == 'commercial':
                loc = getattr(prop, 'commercial_location', '')
                if loc == 'inside':
                    suffix = 'I'
                elif loc == 'outside':
                    suffix = 'O'

            parts.append(f'-{unit_no}{suffix}')

            ref = ''.join(parts)
            return ref if len(ref) > 3 else ''

        except Exception as e:
            _logger.error("Wizard reference generation error for property %s: %s", prop.id, e)
            return ''

    # ── Save ─────────────────────────────────────────────────────────────────
    def action_confirm(self):
        self.ensure_one()
        prop = self.property_id.sudo()
        vals = {'name': self.new_name}
        if self.new_reference:
            vals['computed_reference'] = self.new_reference
        prop.write(vals)
        return {'type': 'ir.actions.act_window_close'}
