# -*- coding: utf-8 -*-
"""Use stored floor_id for computed_reference (floor_ids is not stored)."""
from odoo import api, models
import re
import logging

_logger = logging.getLogger(__name__)


class PropertyProperty(models.Model):
    _inherit = 'property.property'

    def _get_reference_floor(self):
        self.ensure_one()
        if getattr(self, 'floor_id', None):
            return self.floor_id
        if self.floor_ids:
            return self.floor_ids[0]
        return self.env['property.floor']

    def _get_floor_no_for_reference(self):
        """Floor segment F{n} from floor_id, floor_ids, or property name."""
        self.ensure_one()
        floor = self._get_reference_floor()
        if floor and floor.name is not None:
            floor_name = str(floor.name).strip()
            nums = re.findall(r'\d+', floor_name)
            if nums:
                return 'F%s' % nums[0]
            return 'F%s' % floor_name if floor_name else ''
        if self.name:
            match = re.search(r'-F(\d+)-', self.name, re.IGNORECASE)
            if match:
                return 'F%s' % match.group(1)
            match = re.search(r'-F(\d+)$', self.name, re.IGNORECASE)
            if match:
                return 'F%s' % match.group(1)
            for part in self.name.split('-'):
                part = part.strip()
                if part.upper().startswith('F') and re.match(r'^F\d+$', part, re.IGNORECASE):
                    nums = re.findall(r'\d+', part)
                    if nums:
                        return 'F%s' % nums[0]
        return ''

    def _build_reference_string(self):
        self.ensure_one()
        if not self.site or not self.unit_number or not self.unit_number.strip():
            return ''

        try:
            clean_name = re.sub(r'[^A-Za-z0-9]', '', (self.site.name or '').strip())
            site_code = clean_name[:3].upper() if clean_name else ''
            if not site_code:
                return ''

            owner_code = ''
            if hasattr(self.site, 'company_id') and self.site.company_id:
                company = self.site.company_id
                if hasattr(company, 'abbreviation') and company.abbreviation and company.abbreviation.strip():
                    owner_code = re.sub(r'[^A-Za-z0-9]', '', company.abbreviation.strip().upper())
                elif hasattr(company, 'name') and company.name:
                    clean_company = re.sub(r'[^A-Za-z0-9]', '', company.name.strip())
                    if clean_company:
                        owner_code = clean_company[:3].upper()

            project_no = ''
            if hasattr(self.site, 'project_number') and self.site.project_number:
                project_str = str(self.site.project_number).strip()
                if project_str:
                    project_no = project_str

            block_no = ''
            if self.block and getattr(self.block, 'name', None) and self.block.name:
                block_str = str(self.block.name).strip()
                if block_str.isdigit():
                    block_no = block_str.zfill(2)
                else:
                    block_no = block_str.upper()

            floor_no = self._get_floor_no_for_reference()

            unit_str = self.unit_number.strip()
            numbers = re.findall(r'\d+', unit_str)
            unit_no = numbers[0].zfill(2) if numbers else unit_str.upper()[:3]

            ref_parts = [site_code]
            if owner_code:
                ref_parts.append('-%s' % owner_code)
                if project_no:
                    ref_parts.append(project_no)
            if block_no or floor_no:
                location_parts = [p for p in (block_no, floor_no) if p]
                if location_parts:
                    ref_parts.append('/' + '/'.join(location_parts))
            if unit_no:
                suffix = ''
                if self.property_type == 'commercial' and self.commercial_location:
                    suffix = 'I' if self.commercial_location == 'inside' else 'O'
                ref_parts.append('-%s%s' % (unit_no, suffix))

            ref = ''.join(ref_parts)
            return ref if ref and len(ref) > 5 else ''
        except Exception as e:
            _logger.error('Error building reference for property %s: %s', self.id, e)
            return ''

    def _skip_reference_fix_for_installment_non_bulk(self):
        """
        Non-bulk property with a sale that has payment installments: keep reference
        unchanged (installment / contract data may depend on it).
        """
        self.ensure_one()
        if getattr(self, 'bulk_registration_id', None):
            return False
        if 'property.sale' not in self.env:
            return False
        sales = self.env['property.sale'].search([('property_id', '=', self.id)])
        return any(sale.payment_installment_line_ids for sale in sales)

    def _build_new_reference(self):
        """Override Update Reference button (property_name_update_button)."""
        self.ensure_one()
        if self._skip_reference_fix_for_installment_non_bulk():
            return (self.computed_reference or '').strip()
        return self._build_reference_string()

    def _floor_tag_for_reference(self):
        return self._get_floor_no_for_reference()

    def _reference_has_missing_floor_bug(self):
        """True when stored ref is the old auto value missing the floor segment."""
        self.ensure_one()
        if self._skip_reference_fix_for_installment_non_bulk():
            return False
        if not self.site or not (self.unit_number or '').strip():
            return False
        floor_tag = self._get_floor_no_for_reference()
        if not floor_tag:
            return False
        current = (self.computed_reference or '').strip()
        if not current or floor_tag in current:
            return False
        correct = self._build_reference_string().strip()
        if not correct or current == correct:
            return False
        if '/%s' % floor_tag not in correct and '/%s/' % floor_tag not in correct:
            return False
        without_floor = re.sub(r'/%s(?=-)' % re.escape(floor_tag), '', correct)
        if current == without_floor:
            return True
        if current == correct.replace('/%s/' % floor_tag, '/'):
            return True
        # Non-bulk same pattern: /block-unit (e.g. /01-05) but correct has /block/F10-...
        loc = re.search(r'/(?P<blk>[^/]+)-', current)
        if loc:
            blk = loc.group('blk')
            if '/%s/%s' % (blk, floor_tag) in correct:
                return True
        return False

    @api.model
    def action_fix_buggy_references_ui(self):
        fixed = self._fix_buggy_computed_references()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Reference fix',
                'message': '%s property reference(s) updated (system bug only).' % fixed,
                'type': 'success',
                'sticky': False,
            },
        }

    @api.model
    def _fix_buggy_computed_references(self):
        """One-time fix: all properties with system wrong ref (missing floor segment)."""
        props = self.search([
            ('site', '!=', False),
            ('unit_number', '!=', False),
            ('computed_reference', '!=', False),
        ])
        to_fix = props.filtered(lambda p: p._reference_has_missing_floor_bug())
        if not to_fix:
            _logger.info('property_reference_floor_id: no buggy references to fix.')
            return 0
        has_bulk = 'bulk_registration_id' in self._fields
        n_bulk = len(to_fix.filtered(lambda p: p.bulk_registration_id)) if has_bulk else 0
        _logger.info(
            'property_reference_floor_id: fixing %s of %s (%s bulk, %s other).',
            len(to_fix), len(props), n_bulk, len(to_fix) - n_bulk,
        )
        for prop in to_fix:
            correct = prop._build_reference_string()
            if correct:
                old = prop.computed_reference
                prop.sudo().with_context(skip_reference_recompute=True).write({
                    'computed_reference': correct,
                })
                _logger.info(
                    'property_reference_floor_id: property %s %s -> %s',
                    prop.id, old, correct,
                )
        return len(to_fix)

    @api.depends(
        'name',
        'site.name',
        'site',
        'block',
        'floor_id',
        'floor_id.name',
        'floor_ids',
        'property_type',
        'commercial_location',
        'unit_number',
    )
    def _compute_property_reference(self):
        if self.env.context.get('skip_reference_recompute'):
            return
        for prop in self:
            if prop._skip_reference_fix_for_installment_non_bulk():
                prop.computed_reference = prop.computed_reference or ''
                continue
            prop.computed_reference = prop._build_reference_string()
