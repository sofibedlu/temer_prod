# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import re


class PropertyBulkRegistration(models.Model):
    _name = 'property.bulk.registration'
    _description = 'Bulk Property Registration'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Reference', readonly=True, copy=False, default=lambda self: _('New'))
    state = fields.Selection([
        ('draft', 'Draft'),
        ('generated', 'Generated'),
        ('done', 'Done'),
    ], string='Status', default='draft', required=True)

    # Site & block
    site_id = fields.Many2one('property.site', string='Site', required=True, ondelete='restrict')
    block_id = fields.Many2one('property.block', string='Block', required=True, ondelete='restrict',
                               domain="[('site', '=', site_id)]")

    # Read-only site summary (one row)
    site_project_number = fields.Char(related='site_id.project_number', string='Project Number', readonly=True)
    company_abbreviation = fields.Char(string='Company Abbreviation', compute='_compute_company_abbreviation', store=False, readonly=True)
    payment_structure_name = fields.Char(string='Payment Structure', compute='_compute_payment_structure', store=False, readonly=True)
    site_address_summary = fields.Char(string='Address', compute='_compute_site_address_summary', store=False, readonly=True)
    site_price_detail = fields.Char(string='Price (m²)', compute='_compute_site_price_detail', store=False, readonly=True)
    site_summary_one_row = fields.Char(string='Site summary', compute='_compute_site_summary_one_row', store=False, readonly=True)
    # Price per m²: from site by default, editable
    site_price_per_m2 = fields.Float(compute='_compute_site_price_per_m2', store=False, readonly=True)
    currency_id = fields.Many2one('res.currency', related='site_id.currency_id', readonly=True)
    price_per_m2_override = fields.Float(copy=False)  # stored override; empty = use site
    price_per_m2 = fields.Float(
        string='Price (m²)',
        compute='_compute_price_per_m2',
        inverse='_inverse_price_per_m2',
        store=True,
        help='From site by default; editable.',
    )
    use_manual_estimated_sales_price = fields.Boolean(default=False, copy=False)
    manual_estimated_sales_price = fields.Monetary(currency_field='currency_id', copy=False)
    estimated_sales_price = fields.Monetary(
        string='Estimated Sales Price',
        compute='_compute_estimated_sales_price',
        inverse='_inverse_estimated_sales_price',
        store=True,
        currency_field='currency_id',
        help='Calculated from Price (m²) × Gross Area; you can edit to use a different value.',
    )

    # When site type is mixed: select residential or commercial
    is_mixed_site = fields.Boolean(compute='_compute_is_mixed_site', store=False, string='Is Mixed Site')
    display_property_type = fields.Selection([
        ('residential', 'Residential'),
        ('commercial', 'Commercial'),
    ], string='Type', compute='_compute_display_property_type', store=False)
    property_type = fields.Selection([
        ('residential', 'Residential'),
        ('commercial', 'Commercial'),
    ], string='Type', required=False, default='residential')
    commercial_location = fields.Selection([
        ('inside', 'Inside'),
        ('outside', 'Outside'),
    ], string='Site Location (Inside/Outside)', required=False,
       help='Required when type is Commercial')

    # Floor selection: range (from-to) or multiple — only floors of the selected site
    floor_selection_mode = fields.Selection([
        ('range', 'Range (From - To)'),
        ('multiple', 'Multiple Selection'),
    ], string='Floor Selection', default='range', required=True)
    site_floor_ids = fields.Many2many(
        'property.floor',
        compute='_compute_site_floor_ids',
        store=False,
        string='Floors of site',
        help='Floors belonging to the selected site (from existing properties or all if none)',
    )
    floor_from_id = fields.Many2one(
        'property.floor',
        string='Floor From',
        ondelete='restrict',
        domain="[('id', 'in', site_floor_ids)]",
    )
    floor_to_id = fields.Many2one(
        'property.floor',
        string='Floor To',
        ondelete='restrict',
        domain="[('id', 'in', site_floor_ids)]",
    )
    floor_ids = fields.Many2many(
        'property.floor',
        string='Floors (Multiple)',
        relation='bulk_registration_floor_rel',
        domain="[('id', 'in', site_floor_ids)]",
        help='Select multiple floors when mode is Multiple',
    )

    # House number: start (e.g. 01) and count per floor (e.g. 4)
    house_number_start = fields.Char(string='House Number Start', default='01', required=True,
                                     help='e.g. 01 - first unit number')
    units_per_floor = fields.Integer(string='Units per Floor', default=1, required=True,
                                     help='e.g. 4 means 01,02,03,04 on floor 1; 05,06,07,08 on floor 2...')

    # Optional link to site type line (legacy; prefer property_type_* below)
    site_property_type_id = fields.Many2one(
        'site.property.type.line',
        string='Property Type (optional)',
        required=False,
        domain="[('site', '=', site_id)]",
        ondelete='set null',
    )
    # Property type details (direct values, like property_type_details module)
    property_type_bedroom = fields.Integer(
        string="Number of bed room",
        default=0,
        help="Number of bedrooms for each generated property",
    )
    property_type_bathroom = fields.Integer(
        string="Number of bath room",
        default=0,
        help="Number of bathrooms for each generated property",
    )
    property_type_has_maid_room = fields.Boolean(
        string="Has maid room",
        default=False,
        help="Whether the property has a maid room",
    )
    property_type_gross_area = fields.Float(
        string="Gross Area",
        default=0.0,
        help="Gross area of each property",
    )
    property_type_net_area = fields.Float(
        string="Net area",
        default=0.0,
        help="Net area of each property",
    )
    property_type_floor_plan = fields.Binary(
        string="Floor Plan",
        help="Floor plan image of the property",
    )
    property_type_floor_plan_filename = fields.Char(
        string="Floor Plan Filename",
        help="Filename of the floor plan",
    )
    finishing = fields.Selection([
        ('sumi_finished', 'Semi Finished'),
        ('fully_finished', 'Fully Finished'),
        ('none', 'None'),
    ], string='Finishing', default='none')

    property_line_ids = fields.One2many(
        'property.bulk.registration.line',
        'bulk_id',
        string='Properties',
        copy=False,
    )
    property_count = fields.Integer(compute='_compute_property_count', store=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Bulk registration number must be unique.'),
    ]

    @api.depends('property_line_ids')
    def _compute_property_count(self):
        for rec in self:
            rec.property_count = len(rec.property_line_ids)

    @api.depends('site_id')
    def _compute_company_abbreviation(self):
        for rec in self:
            if rec.site_id and hasattr(rec.site_id, 'company_id') and rec.site_id.company_id:
                company = rec.site_id.company_id
                if hasattr(company, 'abbreviation') and company.abbreviation and company.abbreviation.strip():
                    rec.company_abbreviation = company.abbreviation.strip().upper()
                else:
                    rec.company_abbreviation = (company.name or '')[:3].upper()
            else:
                rec.company_abbreviation = ''

    @api.depends('site_id')
    def _compute_payment_structure(self):
        for rec in self:
            if rec.site_id and rec.site_id.payment_structure_id:
                rec.payment_structure_name = rec.site_id.payment_structure_id.name
            else:
                rec.payment_structure_name = rec.site_id.payment_structure or ''

    @api.depends('site_id')
    def _compute_site_address_summary(self):
        for rec in self:
            if not rec.site_id:
                rec.site_address_summary = ''
                continue
            parts = []
            if rec.site_id.area:
                parts.append(rec.site_id.area)
            if rec.site_id.wereda:
                parts.append(rec.site_id.wereda)
            if rec.site_id.sub_city_id and rec.site_id.sub_city_id.name:
                parts.append(rec.site_id.sub_city_id.name)
            if rec.site_id.city_id and rec.site_id.city_id.name:
                parts.append(rec.site_id.city_id.name)
            rec.site_address_summary = ', '.join(parts) if parts else '-'

    @api.depends('site_id', 'site_id.site_type.property_type', 'property_type')
    def _compute_display_property_type(self):
        """Display correct type: from site when commercial/residential, else user's choice (mixed)."""
        for rec in self:
            if rec.site_id and rec.site_id.site_type:
                st = rec.site_id.site_type.property_type
                if st == 'commercial':
                    rec.display_property_type = 'commercial'
                elif st == 'residential':
                    rec.display_property_type = 'residential'
                else:
                    rec.display_property_type = rec.property_type or 'residential'
            else:
                rec.display_property_type = rec.property_type or 'residential'

    @api.depends('site_id')
    def _compute_is_mixed_site(self):
        for rec in self:
            rec.is_mixed_site = bool(
                rec.site_id and rec.site_id.site_type
                and getattr(rec.site_id.site_type, 'property_type', None) == 'mixed'
            )

    @api.depends('site_id')
    def _compute_site_price_detail(self):
        for rec in self:
            if not rec.site_id:
                rec.site_price_detail = ''
                continue
            if getattr(rec.site_id, 'is_multi', False) and rec.site_id.payment_line_ids:
                # Multi: show first price or "Multiple"
                first = rec.site_id.payment_line_ids[:1]
                rec.site_price_detail = '%.2f %s' % (first.price, rec.site_id.currency_id.symbol or '') if first else 'Multiple'
            else:
                rec.site_price_detail = '%.2f %s' % (rec.site_id.price_per_m2, rec.site_id.currency_id.symbol or '')

    @api.depends('site_id')
    def _compute_site_summary_one_row(self):
        for rec in self:
            parts = []
            if rec.site_project_number:
                parts.append(rec.site_project_number)
            if rec.company_abbreviation:
                parts.append(rec.company_abbreviation)
            if rec.payment_structure_name:
                parts.append(rec.payment_structure_name)
            if rec.site_address_summary:
                parts.append(rec.site_address_summary)
            if rec.site_price_detail:
                parts.append(_('Price (m²) %s') % rec.site_price_detail)
            rec.site_summary_one_row = ' | '.join(parts) if parts else ''

    @api.depends('site_id')
    def _compute_site_price_per_m2(self):
        for rec in self:
            if not rec.site_id:
                rec.site_price_per_m2 = 0.0
                continue
            if getattr(rec.site_id, 'is_multi', False) and rec.site_id.payment_line_ids:
                first = rec.site_id.payment_line_ids[:1]
                rec.site_price_per_m2 = float(first.price) if first else 0.0
            else:
                rec.site_price_per_m2 = float(rec.site_id.price_per_m2 or 0.0)

    @api.depends('site_price_per_m2', 'price_per_m2_override')
    def _compute_price_per_m2(self):
        for rec in self:
            rec.price_per_m2 = rec.price_per_m2_override if rec.price_per_m2_override else rec.site_price_per_m2

    def _inverse_price_per_m2(self):
        for rec in self:
            rec.price_per_m2_override = rec.price_per_m2

    @api.onchange('site_id')
    def _onchange_site_id_price_per_m2(self):
        """When site changes, pre-fill price from site so it persists on save (avoids saving 0)."""
        if self.site_id and not self.price_per_m2_override:
            self.price_per_m2_override = self.site_price_per_m2

    def write(self, vals):
        """Ensure price_per_m2 persists: if override is 0 and site has a price, store it."""
        res = super().write(vals)
        for rec in self:
            if rec.site_id and (not rec.price_per_m2_override) and rec.site_price_per_m2:
                super(PropertyBulkRegistration, rec).write({'price_per_m2_override': rec.site_price_per_m2})
        return res

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.site_id and (not rec.price_per_m2_override) and rec.site_price_per_m2:
                rec.write({'price_per_m2_override': rec.site_price_per_m2})
        return records

    @api.depends(
        'site_id', 'site_price_per_m2', 'price_per_m2',
        'property_type_gross_area', 'site_property_type_id', 'site_property_type_id.gross_area',
        'use_manual_estimated_sales_price', 'manual_estimated_sales_price',
    )
    def _compute_estimated_sales_price(self):
        """One field: calculated (Price/m² × Gross Area) by default; if user edited, use their value."""
        for rec in self:
            if rec.use_manual_estimated_sales_price:
                rec.estimated_sales_price = rec.manual_estimated_sales_price
            else:
                price_m2 = rec.price_per_m2
                gross = rec.property_type_gross_area or (rec.site_property_type_id and rec.site_property_type_id.gross_area) or 0.0
                rec.estimated_sales_price = price_m2 * gross

    def _inverse_estimated_sales_price(self):
        """When user edits the field, store as manual value and use it from now on."""
        for rec in self:
            rec.use_manual_estimated_sales_price = True
            rec.manual_estimated_sales_price = rec.estimated_sales_price

    @api.depends('site_id')
    def _compute_site_floor_ids(self):
        """Floors from site: if site has floor_id (floor number per site), use floors 1 to N. Otherwise from existing properties or all floors."""
        Property = self.env['property.property']
        Floor = self.env['property.floor']
        for rec in self:
            if not rec.site_id:
                rec.site_floor_ids = Floor
                continue
            # Site floor count (temer_property_modify): floor_id.name = N means floors 1 to N
            site_floor_count = None
            if hasattr(rec.site_id, 'floor_id') and rec.site_id.floor_id and rec.site_id.floor_id.id:
                try:
                    n = rec.site_id.floor_id.name
                    site_floor_count = int(n) if isinstance(n, (int, float)) else int(str(n).strip())
                except (ValueError, TypeError):
                    pass
            if site_floor_count is not None and site_floor_count >= 1:
                # Get floors 1, 2, ..., N (name can be int or char)
                names = list(range(1, site_floor_count + 1)) + [str(x) for x in range(1, site_floor_count + 1)]
                floors = Floor.search([('name', 'in', names)], order='name')
                rec.site_floor_ids = floors.sorted('name')
            else:
                used_floors = Property.search([('site', '=', rec.site_id.id)]).mapped('floor_id')
                if used_floors:
                    rec.site_floor_ids = used_floors.sorted('name')
                else:
                    rec.site_floor_ids = Floor.search([]).sorted('name')

    @api.onchange('site_id')
    def _onchange_site_id(self):
        self.block_id = False
        self.floor_from_id = False
        self.floor_to_id = False
        self.floor_ids = [(5, 0, 0)]
        if self.site_id and self.site_id.site_type:
            st = self.site_id.site_type.property_type
            if st in ('residential', 'commercial'):
                self.property_type = st
            elif st == 'mixed':
                self.property_type = 'residential'
        # Auto-set floor range when site has floor count (1 to N)
        if self.site_id and self.site_floor_ids:
            self.floor_from_id = self.site_floor_ids[0]
            self.floor_to_id = self.site_floor_ids[-1]

    @api.constrains('floor_from_id', 'floor_to_id', 'floor_selection_mode')
    def _check_floor_range(self):
        for rec in self:
            if rec.floor_selection_mode == 'range' and rec.floor_from_id and rec.floor_to_id:
                if rec.floor_from_id.id == rec.floor_to_id.id:
                    raise ValidationError(_('Floor From and Floor To must be different.'))

    def unlink(self):
        for rec in self:
            if rec.state in ('generated', 'done'):
                raise ValidationError(_('Cannot delete a bulk registration that has been generated or completed.'))
        return super().unlink()

    @api.constrains('property_type', 'commercial_location')
    def _check_commercial_location(self):
        for rec in self:
            if rec.property_type == 'commercial' and not rec.commercial_location:
                raise ValidationError(_('Site Location (Inside/Outside) is required when Type is Commercial.'))

    @api.constrains('units_per_floor')
    def _check_units_per_floor(self):
        for rec in self:
            if rec.units_per_floor < 1:
                raise ValidationError(_('Units per Floor must be at least 1.'))

    @api.model
    def create(self, vals):
        # Sequential unique bulk number from sequence (e.g. BULK-00001, BULK-00002, ...)
        if not vals.get('name') or vals.get('name') == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('property.bulk.registration') or _('New')
        return super().create(vals)

    def _floor_sort_key(self, floor):
        """Sort floors numerically: 1, 2, 3, 10, 11 (not 1, 10, 11, 2, 3)."""
        try:
            n = floor.name
            return (0, int(n) if isinstance(n, (int, float)) else int(str(n).strip()))
        except (ValueError, TypeError):
            return (1, str(floor.name or ''))

    def _get_floors_to_use(self):
        """Use only site_floor_ids; filter by range with numeric ordering (1-3 = floors 1,2,3 only)."""
        self.ensure_one()
        valid = self.site_floor_ids
        if not valid:
            return self.env['property.floor']
        sorted_floors = sorted(valid, key=self._floor_sort_key)
        if self.floor_selection_mode == 'range' and self.floor_from_id and self.floor_to_id:
            from_ids = {self.floor_from_id.id, self.floor_to_id.id}
            indices = {}
            for i, f in enumerate(sorted_floors):
                if f.id in from_ids:
                    indices[f.id] = i
            from_idx = indices.get(self.floor_from_id.id)
            to_idx = indices.get(self.floor_to_id.id)
            if from_idx is not None and to_idx is not None:
                lo, hi = (from_idx, to_idx) if from_idx <= to_idx else (to_idx, from_idx)
                return self.env['property.floor'].browse([f.id for f in sorted_floors[lo:hi + 1]])
        if self.floor_selection_mode == 'multiple' and self.floor_ids:
            valid_ids = {f.id for f in sorted_floors}
            return self.floor_ids.filtered(lambda f: f.id in valid_ids).sorted(key=self._floor_sort_key)
        return self.env['property.floor']

    def action_generate_lines(self):
        """Generate property lines from current settings (floors × units per floor)."""
        self.ensure_one()
        if self.state == 'done':
            raise ValidationError(_('Cannot regenerate: bulk registration is already saved.'))

        floors = self._get_floors_to_use()
        if not floors:
            raise ValidationError(_('Please select at least one floor (Range or Multiple).'))

        # Gross and net are optional - we can use 0.0 if not set

        # Parse start number (e.g. "01" -> 1)
        start_str = (self.house_number_start or '01').strip()
        numbers = re.findall(r'\d+', start_str)
        start_num = int(numbers[0]) if numbers else 1

        # Delete existing lines (draft/generated can regenerate)
        self.property_line_ids.unlink()

        # Use direct property_type_* or fallback to site_property_type_id
        st = self.site_property_type_id
        gross = self.property_type_gross_area or (st and st.gross_area) or 0.0
        net = self.property_type_net_area or (st and st.net_area) or 0.0
        bed = self.property_type_bedroom or (st and st.number_be_room) or 0
        bath = self.property_type_bathroom or (st and st.number_bath_room) or 0
        maid = self.property_type_has_maid_room or bool(st and st.has_maid_room)

        line_vals_list = []
        seq = 0
        for floor in floors:
            for i in range(self.units_per_floor):
                unit_num = start_num + i  # reset per floor
                unit_str = str(unit_num).zfill(2) if unit_num < 100 else str(unit_num)
                seq += 1
                # Site type commercial must stay commercial; mixed uses user choice
                site_ptype = (self.site_id.site_type.property_type
                              if self.site_id and self.site_id.site_type else None)
                if site_ptype == 'commercial':
                    ptype = 'commercial'
                    cloc = self.commercial_location or False
                elif site_ptype == 'residential':
                    ptype = 'residential'
                    cloc = False
                else:
                    ptype = self.property_type or 'residential'
                    cloc = self.commercial_location if ptype == 'commercial' else False
                line_vals_list.append({
                    'bulk_id': self.id,
                    'sequence': seq,
                    'floor_id': floor.id,
                    'unit_number': unit_str,
                    'site_property_type_id': self.site_property_type_id.id if self.site_property_type_id else False,
                    'property_type': ptype,
                    'commercial_location': cloc,
                    'gross_area': gross,
                    'net_area': net,
                    'bedroom': bed,
                    'bathroom': bath,
                    'has_maid_room': maid,
                    'finishing': self.finishing,
                    'property_type_bedroom': bed,
                    'property_type_bathroom': bath,
                    'property_type_has_maid_room': maid,
                    'property_type_gross_area': gross,
                    'property_type_net_area': net,
                    'property_type_floor_plan': self.property_type_floor_plan,
                    'property_type_floor_plan_filename': self.property_type_floor_plan_filename,
                    'price_per_m2_override': self.price_per_m2,
                    'estimated_sales_price_override': self.estimated_sales_price or 0.0,
                })
        self.env['property.bulk.registration.line'].create(line_vals_list)

        self.state = 'generated'
        count = len(line_vals_list)
        self.message_post(body=_('%s property line(s) generated.') % count)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'property.bulk.registration',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_save_as_draft(self):
        """Create property.property for each line with state=draft."""
        return self._action_save_properties(state='draft')

    def action_save_as_available(self):
        """Create property.property for each line with state=available."""
        return self._action_save_properties(state='available')

    def _action_save_properties(self, state='draft'):
        self.ensure_one()
        if self.state == 'done':
            raise ValidationError(_('Properties were already created.'))

        if not self.property_line_ids:
            raise ValidationError(_('Generate property lines first (click Generate Properties).'))

        Property = self.env['property.property']
        created = Property
        for line in self.property_line_ids:
            if line.property_id:
                continue
            vals = line._prepare_property_vals()
            vals['state'] = state
            vals['bulk_registration_id'] = self.id
            prop = Property.create(vals)
            # Base property create() forces state='draft'; set to available when requested
            if state == 'available':
                prop.write({'state': 'available'})
            line.property_id = prop.id
            created |= prop

        self.state = 'done'
        return {
            'type': 'ir.actions.act_window',
            'name': _('Created Properties'),
            'res_model': 'property.property',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', created.ids)],
            'context': dict(self.env.context),
        }
