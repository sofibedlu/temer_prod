# -*- coding: utf-8 -*-
import re
import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class PropertyProperty(models.Model):
    _inherit = 'property.property'

    # Pending values — populated when user clicks "Update Name" / "Update Reference"
    pending_name = fields.Char(string='Pending Name', store=True, copy=False)
    pending_reference = fields.Char(string='Pending Reference', store=True, copy=False)

    # Flags to control panel visibility
    show_name_panel = fields.Boolean(string='Show Name Panel', store=True, copy=False, default=False)
    show_reference_panel = fields.Boolean(string='Show Reference Panel', store=True, copy=False, default=False)

    def init(self):
        """Reset panel flags on module upgrade so panels are hidden by default."""
        self.env.cr.execute(
            "UPDATE property_property SET show_name_panel = false, show_reference_panel = false "
            "WHERE show_name_panel = true OR show_reference_panel = true"
        )

    # Mirror fields for display in panels (avoids duplicate field error)
    current_name_display = fields.Char(
        string='Current Name', compute='_compute_current_displays', store=False)
    current_ref_display = fields.Char(
        string='Current Reference', compute='_compute_current_displays', store=False)

    @api.depends('name', 'computed_reference')
    def _compute_current_displays(self):
        for rec in self:
            rec.current_name_display = rec.name
            rec.current_ref_display = getattr(rec, 'computed_reference', '') or ''

    # ── Helpers ──────────────────────────────────────────────────────────────
    def _get_unit(self):
        unit = (getattr(self, 'unit_number', None) or '').strip()
        if unit:
            return unit
        if self.name and self.name != _('New'):
            parts = self.name.strip().split('-')
            if len(parts) >= 2:
                candidate = parts[-1].strip()
                if candidate:
                    return candidate
        return ''

    def _get_floor_name(self):
        floor_id = getattr(self, 'floor_id', None)
        if floor_id and floor_id.name:
            return floor_id.name
        floor_ids = getattr(self, 'floor_ids', None)
        if floor_ids:
            return floor_ids[0].name or ''
        return ''

    def _build_new_name(self):
        if not self.site or not self.block:
            return self.name or ''
        site = self.site.name or ''
        block = self.block.name or ''
        floor = self._get_floor_name()
        unit = self._get_unit()
        parts = [site, block]
        if floor:
            parts.append(f'F{floor}')
        if unit:
            parts.append(unit)
        return '-'.join(parts)

    def _build_new_reference(self):
        """
        Generate reference exactly like advanced_property_unit_naming._compute_property_reference.
        If unit_number is empty, generate with available fields and leave unit part blank.
        """
        if not self.site:
            return ''
        try:
            # 1. Site code — first 3 alphanumeric chars of site name
            clean_site = re.sub(r'[^A-Za-z0-9]', '', (self.site.name or '').strip())
            site_code = clean_site[:3].upper() if clean_site else ''
            if not site_code:
                return ''

            # 2. Owner code — from site company abbreviation or name
            owner_code = ''
            site_company = getattr(self.site, 'company_id', None)
            if site_company:
                abbr = getattr(site_company, 'abbreviation', None)
                if abbr and abbr.strip():
                    owner_code = re.sub(r'[^A-Za-z0-9]', '', abbr.strip().upper())
                elif getattr(site_company, 'name', None):
                    owner_code = re.sub(r'[^A-Za-z0-9]', '', site_company.name.strip())[:3].upper()

            # 3. Project number
            pn = getattr(self.site, 'project_number', None)
            project_no = str(pn).strip() if pn else ''

            # 4. Block number — extract digits zero-padded to 2, else first 2 chars
            block_no = ''
            if self.block and self.block.name:
                block_str = str(self.block.name).strip()
                nums = re.findall(r'\d+', block_str)
                block_no = nums[0].zfill(2) if nums else block_str[:2].upper()

            # 5. Floor number — from floor_id (Many2one, stored) or floor_ids fallback
            floor_no = ''
            floor_obj = getattr(self, 'floor_id', None) or (self.floor_ids[0] if self.floor_ids else None)
            if floor_obj and floor_obj.name:
                floor_str = str(floor_obj.name).strip().upper()
                if floor_str:
                    nums = re.findall(r'\d+', floor_str)
                    if nums:
                        floor_no = f'F{nums[0]}'
                    else:
                        clean_floor = re.sub(r'^(FLOOR|FLR|FL|F)\s*', '', floor_str, flags=re.IGNORECASE)
                        if clean_floor and clean_floor[0].isdigit():
                            floor_no = f'F{clean_floor[0]}'
                        else:
                            floor_no = floor_str[:3]

            # 6. Unit number — from unit_number field only, empty string if not set
            unit_no = ''
            unit_str = (self.unit_number or '').strip()
            if unit_str:
                nums = re.findall(r'\d+', unit_str)
                unit_no = nums[0].zfill(2) if nums else unit_str.upper()[:3]

            # Build reference
            parts = [site_code]
            if owner_code:
                parts.append(f'-{owner_code}')
                if project_no:
                    parts.append(project_no)

            location_parts = [p for p in [block_no, floor_no] if p is not None and p != '']
            if location_parts:
                parts.append('/' + '/'.join(location_parts))

            # Suffix from commercial_location (inside=I, outside=O)
            suffix = ''
            if getattr(self, 'property_type', '') == 'commercial':
                loc = getattr(self, 'commercial_location', '')
                suffix = 'I' if loc == 'inside' else ('O' if loc == 'outside' else '')

            # Always append unit+suffix segment if either exists
            if unit_no or suffix:
                parts.append(f'-{unit_no}{suffix}')

            ref = ''.join(parts)
            return ref if len(ref) > 3 else ''
        except Exception as e:
            _logger.error("Reference generation error for property %s: %s", self.id, e)
            return ''

    # ── Reload helper ─────────────────────────────────────────────────────────
    def _reload_form(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'current',
        }

    # ── Button: generate pending name (requires group_update_property_name) ──
    def action_generate_name(self):
        self.ensure_one()
        self.sudo().write({
            'pending_name': self._build_new_name(),
            'show_name_panel': True,
        })
        return self._reload_form()

    # ── Button: cancel name panel ─────────────────────────────────────────────
    def action_cancel_name(self):
        self.ensure_one()
        self.sudo().write({'show_name_panel': False, 'pending_name': False})
        return self._reload_form()

    # ── Button: save name only ────────────────────────────────────────────────
    def action_save_name(self):
        self.ensure_one()
        vals = {'show_name_panel': False, 'pending_name': False}
        if self.pending_name:
            vals['name'] = self.pending_name
        self.sudo().write(vals)
        return self._reload_form()

    # ── Button: generate pending reference (requires group_update_property_reference)
    def action_generate_reference(self):
        self.ensure_one()
        self.sudo().write({
            'pending_reference': self._build_new_reference(),
            'show_reference_panel': True,
        })
        return self._reload_form()

    # ── Button: cancel reference panel ───────────────────────────────────────
    def action_cancel_reference(self):
        self.ensure_one()
        self.sudo().write({'show_reference_panel': False, 'pending_reference': False})
        return self._reload_form()

    # ── Button: save reference only ───────────────────────────────────────────
    def action_save_reference(self):
        self.ensure_one()
        vals = {'show_reference_panel': False, 'pending_reference': False}
        if self.pending_reference and hasattr(self, 'computed_reference'):
            vals['computed_reference'] = self.pending_reference
        self.sudo().write(vals)
        return self._reload_form()
