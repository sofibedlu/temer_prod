from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_round
from datetime import timedelta
import re

class PropertyLegacySale(models.Model):
    _name = 'property.legacy.sale'
    _description = 'Legacy Property Sale Staging'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'

    name = fields.Char(string="Reference", default="New", readonly=True)
    partner_id = fields.Many2one('res.partner', string="Customer", required=True)
    salesperson_id = fields.Many2one('res.users', string="Salesperson")
    property_id = fields.Many2one(
        'property.property', 
        string="Property", 
        required=True, 
        domain="[('is_legacy', '=', True), ('state', '=', 'available')]"
    )
    
    contract_number = fields.Char(string="Contract Number", required=True)
    contract_date_char = fields.Char(string="Contract Date", required=True, help="Format: dd/mm/yyyy")
    sale_price = fields.Float(string="Sale Price", required=True)
    date = fields.Date(string="Order Date", default=fields.Date.today, required=True)
    
    payment_term_id = fields.Many2one('property.payment.term', string="Payment Term")
    
    installment_ids = fields.One2many('property.legacy.sale.line', 'legacy_sale_id', string="Installments")
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('checked', 'Checked'), 
        ('approved', 'Approved')
    ], default='draft', string="Status", tracking=True)
    
    created_sale_id = fields.Many2one('property.sale', string="Created Sale", readonly=True)

    # UI helper: total of legacy installments and flag/message when it exceeds sale price
    installment_total = fields.Float(string="Installments Total", compute='_compute_installment_totals')
    installment_exceeds = fields.Boolean(string="Installments Exceed Sale Price", compute='_compute_installment_totals', store=False)
    installment_exceed_message = fields.Char(string="Installments Warning", compute='_compute_installment_totals')
    # flag/message when installments total is below sale price
    installment_below = fields.Boolean(string="Installments Below Sale Price", compute='_compute_installment_totals', store=False)
    installment_below_message = fields.Char(string="Installments Info", compute='_compute_installment_totals')

    @api.constrains('contract_date_char')
    def _check_contract_date_format(self):
        date_pattern = re.compile(r'^\d{2}/\d{2}/\d{4}$')
        for record in self:
            if record.contract_date_char and not date_pattern.match(record.contract_date_char):
                raise ValidationError("The Contract Date must be in 'dd/mm/yyyy' format.")

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('property.legacy.sale') or 'New'
        return super(PropertyLegacySale, self).create(vals)
    
    @api.depends('installment_ids.amount', 'sale_price')
    def _compute_installment_totals(self):
        for rec in self:
            total = sum(rec.installment_ids.mapped('amount') or [0.0])
            rec.installment_total = total
            rec.installment_exceeds = False
            rec.installment_exceed_message = ''
            rec.installment_below = False
            rec.installment_below_message = ''
            if rec.sale_price:
                if float_compare(total, rec.sale_price, precision_digits=2) > 0:
                    rec.installment_exceeds = True
                    rec.installment_exceed_message = _(
                        "Installments total (%.2f) exceeds sale price (%.2f)."
                    ) % (total, rec.sale_price or 0.0)
                elif float_compare(total, rec.sale_price, precision_digits=2) < 0:
                    rec.installment_below = True
                    rec.installment_below_message = _(
                        "Installments total (%.2f) is below sale price (%.2f)."
                    ) % (total, rec.sale_price or 0.0)
                else:
                    rec.installment_below_message = _("Installments total matches sale price.")

    @api.onchange('property_id')
    def _onchange_property_id(self):
        if self.property_id:
            self.sale_price = self.property_id.unit_price or self.property_id.total_price

    @api.onchange('payment_term_id', 'sale_price', 'date')
    def _onchange_payment_term_id(self):
        if not self.payment_term_id:
            return

        installments = []
        base_date = self.date or fields.Date.today()
        sale_price = self.sale_price or 0.0
        sorted_lines = self.payment_term_id.payment_line.sorted(key=lambda l: l.sequence)

        for line in sorted_lines:
            amount = 0.0
            payment_type = getattr(self.payment_term_id, 'payment_type', 'percentage')
            
            if payment_type == 'fixed':
                amount = getattr(line, 'amount', 0.0)
            else:
                amount = (sale_price * line.percentage) / 100.0
            installments.append((0, 0, {
                'name': line.name or 'Installment',
                'amount': amount,
                'percentage': line.percentage,
                'paid_amount': 0.0,
                'discount': 0.0,
                'payment_term_line_id': line.id,
            }))
        
        self.installment_ids = [(5, 0, 0)] + installments
    
    def action_check(self):
        self.ensure_one()
        if self.state != 'draft':
            return
        self.write({'state': 'checked'})

    def action_approve(self):
        self.ensure_one()

        # Prevent duplicate contract numbers
        dup_legacy = self.search([
            ('contract_number', '=', self.contract_number),
            ('id', '!=', self.id),
        ], limit=1)
        if dup_legacy:
            raise UserError(_("Contract Number %s already exists in Legacy Sales.") % self.contract_number)

        dup_sale = self.env['property.sale'].search([
            ('contract_number', '=', self.contract_number),
            ('state', '!=', 'cancel'),
        ], limit=1)
        if dup_sale:
            raise UserError(_("Contract Number %s already exists on Property Sale %s.") % (self.contract_number, dup_sale.name))
        
        if self.state != 'checked':
            raise UserError(_("You must check the record before approving."))
        
        # --- Validation: only the FIRST installment may have paid_amount > 0 ---
        if self.installment_ids:
            first = self.installment_ids[0]
            offending = self.installment_ids[1:].filtered(lambda l: (l.paid_amount or 0.0) > 0.0)
            if offending:
                names = ', '.join(offending.mapped('name') or [])
                raise UserError(_(
                    "Only the first installment (downpayment) may have a paid amount.\n"
                    "Please remove paid amounts from: %s"
                ) % names)
        
        # Fetch 'regular' reservation configuration
        reservation_type = self.env['property.reservation.configuration'].search(
            [('reservation_type', '=', 'regular')], limit=1)
        if not reservation_type:
            raise UserError(_("No Reservation Type with reservation_type='regular' found. Please configure one."))

        # Determine salesperson: use provided salesperson or leave empty
        salesperson = self.salesperson_id.id if self.salesperson_id else False
        
        # Create reservation
        reservation_vals = {
            'partner_id': self.partner_id.id,
            'property_id': self.property_id.id,
            'reservation_type_id': reservation_type.id,
            'status': 'reserved',
            'salesperson_ids': salesperson,
        }
        reservation = self.env['property.reservation'].sudo().create(reservation_vals)

        # 1. Create the Property Sale record
        sale_vals = {
            'partner_id': self.partner_id.id,
            'property_id': self.property_id.id,
            'sale_price': self.sale_price,
            'order_date': self.date,
            'is_legacy': True,
            'legacy_contract_number': self.contract_number,
            'property_payment_term': self.payment_term_id.id,
            'state': 'draft',
            'reservation_id': reservation.id,
            'sales_person': salesperson,
        }
        # create sale with context flag
        Sale = self.env['property.sale'].with_context(legacy_import=True)
        sale = Sale.create(sale_vals)

        # remove the auto-generated lines
        auto_lines = self.env['property.payment.line'].search([
            ('sale_id', '=', sale.id),
            ('legacy_created', '=', False),
        ])
        if auto_lines:
            auto_lines.unlink()

        # 3. Create Legacy Installments exactly as entered.
        for line in self.installment_ids:
            percentage = line.percentage or 0.0
            if not percentage and self.sale_price:
                percentage = (line.amount / self.sale_price) * 100

            term_line_id = line.payment_term_line_id.id if line.payment_term_line_id else False

            # If no payment term line provided, create a minimal term-line so the payment line has a name
            if not term_line_id:
                TermLine = self.env['property.payment.term.line']
                # Create a detached (not linked to a template) term-line so we don't modify templates
                term_vals = {
                    'name': f"{line.name or 'Installment'}",
                }
                if hasattr(TermLine, 'percentage'):
                    term_vals['percentage'] = percentage
                if hasattr(TermLine, 'amount'):
                    term_vals['amount'] = line.amount
                # don't set 'payment_term_id' here — this avoids updating the configured payment term
                term_line = TermLine.sudo().create(term_vals)
                term_line_id = term_line.id
            # create the actual property.payment.line with exact legacy values
            self.env['property.payment.line'].create({
                'sale_id': sale.id,
                'payment_term_id': term_line_id,
                'expected': percentage,
                'expected_amount': line.amount,
                'paid_amount': line.paid_amount or 0.0,
                'discount': 0.0,
                'legacy_created': True,
            })

        # 3. Confirm the sale
        sale.action_confirm()

        # Update the contract application with the legacy date
        contract_app = self.env['contract.application'].search([('property_sale_id', '=', sale.id)], limit=1)
        if contract_app:
            contract_app.sudo().write({
                'contract_date_char': self.contract_date_char
            })

        # mark the property as sold for legacy-created sale
        if sale.property_id and sale.property_id.state != 'sold':
            sale.property_id.sudo().write({'state': 'sold'})

        # Mark reservation sold 
        if reservation.status != 'sold':
            reservation.sudo().write({'status': 'sold'})

        # Update this record
        self.write({
            'state': 'approved',
            'created_sale_id': sale.id
        })

        return True

class PropertyLegacySaleLine(models.Model):
    _name = 'property.legacy.sale.line'
    _description = 'Legacy Sale Installment'

    legacy_sale_id = fields.Many2one('property.legacy.sale', string="Legacy Sale")
    name = fields.Char(string="Description", required=True)
    percentage = fields.Float(string="Percentage")
    amount = fields.Float(string="Amount", compute="_compute_amount", inverse="_inverse_amount", store=True)
    paid_amount = fields.Float(string="Paid Amount", default=0.0)
    discount = fields.Float(string="Discount", default=0.0)
    remaining = fields.Float(string="Remaining", compute="_compute_remaining", store=True)
    payment_term_line_id = fields.Many2one('property.payment.term.line', string="Term Line")
    status = fields.Selection(
        [('unpaid', 'Unpaid'), ('partial', 'Partial'), ('paid', 'Paid')],
        string='Status', compute='_compute_status', store=True
    )

    @api.onchange('amount')
    def _onchange_amount(self):
        for rec in self:
            if rec.legacy_sale_id and rec.legacy_sale_id.sale_price:
                rec.percentage = (rec.amount / rec.legacy_sale_id.sale_price) * 100

    @api.depends('percentage', 'legacy_sale_id.sale_price')
    def _compute_amount(self):
        for rec in self:
            price = rec.legacy_sale_id.sale_price or 0.0
            rec.amount = (price * (rec.percentage or 0.0) / 100.0) if price else 0.0

    def _inverse_amount(self):
        for rec in self:
            price = rec.legacy_sale_id.sale_price or 0.0
            rec.percentage = (rec.amount / price * 100.0) if price else 0.0

    @api.depends('amount', 'paid_amount', 'discount')
    def _compute_remaining(self):
        for rec in self:
            rec.remaining = float_round(rec.amount - rec.paid_amount - rec.discount, precision_digits=2)

    @api.depends('amount', 'paid_amount', 'discount')
    def _compute_status(self):
        for rec in self:
            paid_total = rec.paid_amount + rec.discount
            if float_compare(paid_total, rec.amount, precision_digits=2) >= 0:
                rec.status = 'paid'
            elif float_compare(paid_total, 0.0, precision_digits=2) > 0:
                rec.status = 'partial'
            else:
                rec.status = 'unpaid'