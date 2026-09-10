# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
import re


class PropertyBulkRegistrationLine(models.Model):
    _name = 'property.bulk.registration.line'
    _description = 'Bulk Property Registration Line'
    _order = 'bulk_id, sequence, id'

    bulk_id = fields.Many2one('property.bulk.registration', string='Bulk Registration', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=1)

    site_id = fields.Many2one('property.site', related='bulk_id.site_id', store=True, readonly=True)
    block_id = fields.Many2one('property.block', related='bulk_id.block_id', store=True, readonly=True)
    floor_id = fields.Many2one('property.floor', string='Floor', required=True, ondelete='restrict')
    unit_number = fields.Char(string='House Number', required=True)

    property_type = fields.Selection([
        ('residential', 'Residential'),
        ('commercial', 'Commercial'),
    ], string='Type', required=False)
    commercial_location = fields.Selection([
        ('inside', 'Inside'),
        ('outside', 'Outside'),
    ], string='Site Location')

    site_property_type_id = fields.Many2one('site.property.type.line', string='Property Type', required=False, ondelete='set null')
    gross_area = fields.Float(string='Gross Area (m²)')
    net_area = fields.Float(string='Net Area (m²)')
    bedroom = fields.Integer(string='Bedrooms')
    bathroom = fields.Integer(string='Bathrooms')
    has_maid_room = fields.Boolean(string='Has Maid Room')
    finishing = fields.Selection([
        ('sumi_finished', 'Semi Finished'),
        ('fully_finished', 'Fully Finished'),
        ('none', 'None'),
    ], string='Finishing')

    # Property Type Detail Fields (mirror of property_type_details)
    property_type_bedroom = fields.Integer(string="Number of bed room")
    property_type_bathroom = fields.Integer(string="Number of bath room")
    property_type_has_maid_room = fields.Boolean(string="Has maid room")
    property_type_gross_area = fields.Float(string="Gross Area")
    property_type_net_area = fields.Float(string="Net area")
    property_type_floor_plan = fields.Binary(string="Floor Plan")
    property_type_floor_plan_filename = fields.Char(string="Floor Plan Filename")

    # Price: per-line override; computed display
    currency_id = fields.Many2one('res.currency', related='bulk_id.currency_id', readonly=True)
    price_per_m2_override = fields.Float(string='Price (m²)', help='Leave empty to use site/bulk price.')
    estimated_sales_price_override = fields.Monetary(
        string='Estimated Sales Price', currency_field='currency_id',
        help='Override calculated price. Calculated as Price (m²) × Gross Area when empty.',
    )
    price_per_m2 = fields.Float(string='Price (m²)', compute='_compute_price_display', store=False)
    estimated_sales_price = fields.Monetary(
        string='Estimated Price', currency_field='currency_id',
        compute='_compute_price_display', store=False,
    )

    @api.depends('price_per_m2_override', 'estimated_sales_price_override', 'bulk_id.price_per_m2', 'property_type_gross_area', 'gross_area')
    def _compute_price_display(self):
        for line in self:
            price_m2 = line.price_per_m2_override or (line.bulk_id.price_per_m2 if line.bulk_id else 0.0)
            gross = line.property_type_gross_area or line.gross_area or 0.0
            line.price_per_m2 = price_m2
            line.estimated_sales_price = line.estimated_sales_price_override or (price_m2 * gross)

    # Display name and reference (same logic as property)
    line_name = fields.Char(string='Name', compute='_compute_line_name_reference', store=True)
    line_reference = fields.Char(string='Reference Number', compute='_compute_line_name_reference', store=True)

    property_id = fields.Many2one('property.property', string='Property', readonly=True, copy=False,
                                   help='Set when Save as Draft/Available is used')

    @api.depends('site_id', 'block_id', 'floor_id', 'unit_number', 'property_type', 'commercial_location', 'site_property_type_id')
    def _compute_line_name_reference(self):
        for line in self:
            if not line.site_id or not line.block_id or not line.floor_id or not line.unit_number:
                line.line_name = _('New')
                line.line_reference = ''
                continue
            # Name: site-block-F{floor}-unit (unique per unit)
            line.line_name = '%s-%s-F%s-%s' % (
                line.site_id.name or '',
                line.block_id.name or '',
                line.floor_id.name,
                line.unit_number or '',
            )
            # Reference: same format as advanced_property_unit_naming
            line.line_reference = line._get_computed_reference()

    def _get_computed_reference(self):
        """Build reference like SiteCode-OwnerCode[ProjectNumber]/BlockNumber/FloorNumber-UnitNumber[Suffix]"""
        self.ensure_one()
        if not self.site_id or not self.unit_number or not self.unit_number.strip():
            return ''
        try:
            site_name = self.site_id.name or ''
            site_code = ''
            if site_name:
                clean = re.sub(r'[^A-Za-z0-9]', '', site_name.strip())
                if clean:
                    site_code = clean[:3].upper()
            if not site_code:
                return ''

            owner_code = ''
            if hasattr(self.site_id, 'company_id') and self.site_id.company_id:
                company = self.site_id.company_id
                if hasattr(company, 'abbreviation') and company.abbreviation and company.abbreviation.strip():
                    owner_code = re.sub(r'[^A-Za-z0-9]', '', company.abbreviation.strip().upper())
                elif hasattr(company, 'name') and company.name:
                    owner_code = re.sub(r'[^A-Za-z0-9]', '', company.name.strip())[:3].upper()

            project_no = (getattr(self.site_id, 'project_number', None) or '').strip() or ''

            block_no = ''
            if self.block_id and hasattr(self.block_id, 'name') and self.block_id.name:
                block_str = str(self.block_id.name).strip()
                # If purely numeric, zero-pad; otherwise keep as-is (e.g. c2, A1)
                if block_str.isdigit():
                    block_no = block_str.zfill(2)
                else:
                    block_no = block_str.upper()

            floor_no = 'F%s' % self.floor_id.name if self.floor_id else ''

            unit_str = (self.unit_number or '').strip()
            nums = re.findall(r'\d+', unit_str)
            unit_no = nums[0].zfill(2) if nums else unit_str.upper()[:3]

            suffix = ''
            if self.property_type == 'commercial' and self.commercial_location:
                suffix = 'I' if self.commercial_location == 'inside' else 'O'

            ref_parts = [site_code]
            if owner_code:
                ref_parts.append('-%s' % owner_code)
                if project_no:
                    ref_parts.append(project_no)
            if block_no or floor_no:
                ref_parts.append('/%s/%s' % (block_no, floor_no))
            ref_parts.append('-%s%s' % (unit_no, suffix))
            return ''.join(ref_parts)
        except Exception:
            return ''

    def _prepare_property_vals(self):
        """Build vals for creating property.property from this line."""
        self.ensure_one()
        site_ptype = (self.site_id.site_type.property_type
                      if self.site_id and self.site_id.site_type else None)
        if site_ptype == 'commercial':
            ptype = 'commercial'
        elif site_ptype == 'residential':
            ptype = 'residential'
        else:
            ptype = self.property_type or (self.bulk_id.property_type if self.bulk_id else 'residential') or 'residential'
        price_m2 = self.price_per_m2_override or (self.bulk_id.price_per_m2 if self.bulk_id else 0.0)
        gross = self.property_type_gross_area or self.gross_area or 0.0
        est_price = self.estimated_sales_price_override or (price_m2 * gross)
        vals = {
            'site': self.site_id.id,
            'block': self.block_id.id,
            'floor_id': self.floor_id.id,
            'floor_ids': [(6, 0, [self.floor_id.id])],
            'site_property_type_id': self.site_property_type_id.id if self.site_property_type_id else False,
            'property_type': ptype,
            'commercial_location': self.commercial_location if ptype == 'commercial' else False,
            'unit_number': self.unit_number,
            'finishing': self.finishing,
            'sale_rent': 'for_sale',
            # Property Type Details (property_type_details module)
            'property_type_bedroom': self.property_type_bedroom or self.bedroom,
            'property_type_bathroom': self.property_type_bathroom or self.bathroom,
            'property_type_has_maid_room': self.property_type_has_maid_room or self.has_maid_room,
            'property_type_gross_area': self.property_type_gross_area or self.gross_area,
            'property_type_net_area': self.property_type_net_area or self.net_area,
            'property_type_floor_plan': self.property_type_floor_plan,
            'property_type_floor_plan_filename': self.property_type_floor_plan_filename,
        }
        if self.bulk_id.site_id.finishing:
            vals.setdefault('finishing', self.bulk_id.site_id.finishing)
        # Price override (temer_property_price_m2_edit) and manual price (temer_configuration_modify)
        if hasattr(self.env['property.property'], 'override_price_m2'):
            vals['override_price_m2'] = price_m2
        if hasattr(self.env['property.property'], 'manual_unit_price'):
            vals['manual_unit_price'] = est_price
        return vals

    def action_edit_line(self):
        """Open wizard to edit this line (sales price, price m², house number, property type details)."""
        self.ensure_one()
        if self.property_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Info'),
                    'message': _('Property already created. Edit from the property form.'),
                    'type': 'info',
                    'sticky': False,
                }
            }
        wizard = self.env['bulk.edit.line.wizard'].create({
            'line_id': self.id,
            'unit_number': self.unit_number,
            'floor_id': self.floor_id.id,
            'property_type': self.property_type,
            'commercial_location': self.commercial_location or False,
            'price_per_m2_override': self.price_per_m2_override or (self.bulk_id and self.bulk_id.price_per_m2 or 0.0),
            'estimated_sales_price_override': self.estimated_sales_price_override,
            'property_type_bedroom': self.property_type_bedroom,
            'property_type_bathroom': self.property_type_bathroom,
            'property_type_has_maid_room': self.property_type_has_maid_room,
            'property_type_gross_area': self.property_type_gross_area,
            'property_type_net_area': self.property_type_net_area,
            'finishing': self.finishing,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Edit property line'),
            'res_model': 'bulk.edit.line.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
            'context': dict(self.env.context),
        }

    def action_open_property(self):
        """Open the linked property form, or show a message if not yet created."""
        self.ensure_one()
        if self.property_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'property.property',
                'res_id': self.property_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Info'),
                'message': _('Save as Draft or Save as Available first to create the property.'),
                'type': 'info',
                'sticky': False,
            }
        }
