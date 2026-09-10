from odoo.exceptions import ValidationError, UserError
import logging
from datetime import datetime, timedelta
from odoo import api, fields, models, _
_logger = logging.getLogger(__name__)

from odoo import models, api
from odoo.exceptions import UserError



class PropertyPaymentTermLine(models.Model):
    _inherit = 'property.payment.term.line'

    amount = fields.Float(string="Amount")
    due_date_term = fields.Integer(string="Due Date Term (Days)")
    construction_progress = fields.Float(string="Construction Progress (%)")
    payment_type = fields.Selection(
        [
            ("fixed", "Fixed"),
            ("percentage", "Percentage"),
        ],
        related='payment_term_id.payment_type',
        string="Payment Type",
        store=True
    )
    cash_collection = fields.Selection(
        [
            ("by_time", "By Time"),
            ("by_site", "By Construction Site"),
        ],
        string="Cash Collection",
        related='payment_term_id.cash_collection',
        store=True
    )
    # 1) One2many back‑reference to progress entries
    progress_entry_ids = fields.One2many(
        'property.site.construction.progress',
        'payment_term_line_id',
        string="Construction Progress Entries",
    )

    # 2) Boolean flag, stored, computed from the above
    is_used_in_progress = fields.Boolean(
        string="Used in Construction Progress",
        compute='_compute_is_used_in_progress',
        store=True,
    )

    @api.depends('progress_entry_ids')
    def _compute_is_used_in_progress(self):
        """Mark True if there's at least one progress that references this line."""
        for line in self:
            line.is_used_in_progress = bool(line.progress_entry_ids)


class PropertyPaymentTerm(models.Model):
    _inherit = 'property.payment.term'

    property_ids = fields.One2many(
        'property.property',
        'payment_structure_id',
        string="Properties Using This Term",
    )

    payment_type = fields.Selection(
        [
            ("fixed", "Fixed"),
            ("percentage", "Percentage"),
        ],
        string="Payment Type",
        required=True, default="percentage",
        help="Defines whether the payment is a fixed amount or a percentage."
    )

    cash_collection = fields.Selection(
        [
            ("by_time", "By Time"),
            ("by_site", "By Construction Site"),
            ("none", "Other"),
        ],
        string="Cash Collection",
        required=True, default="none",
        help="Indicates how cash will be collected for this payment term."
    )


    # Add new validation methods
    @api.model
    def create(self, vals):
        record = super(models.Model, self).create(vals)
        if vals.get('payment_type') == 'percentage' or vals.get('cash_collection') == 'by_site':
            record._validate_percentage_total()
        return record

    def write(self, vals):
        res = super(models.Model, self).write(vals)
        for term in self:
            new_type = vals.get('payment_type', term.payment_type)
            if new_type == 'percentage':
                term._validate_percentage_total()
        return res

    def _validate_percentage_total(self):
        """Validate percentage terms sum to 100% (with tolerance)"""
        self.ensure_one()
        total = sum(self.payment_line.mapped('percentage'))
        if not (99.99 <= round(total, 2) <= 100.01):
            raise ValidationError(_(
                "Total percentage of payment lines must equal 100 %%\n" 
                "Please adjust your payment percentages. Current total: %.2f%% "
            ) % (total))

    def _validate_site_total(self):
        """Validate percentage terms sum to 100% (with tolerance)"""
        self.ensure_one()
        total = sum(self.payment_line.mapped('construction_progress'))
        if not (99.99 <= round(total, 2) <= 100.01):
            raise ValidationError(_(
                "Total progress of payment lines must equal 100 %%\n" 
                "Please adjust your payment progress percentages. Current total: %.2f%% "
            ) % (total))



class PropertyProperty(models.Model):
    _inherit = 'property.property'

    payment_term_line_ids = fields.One2many(
        'property.payment.term.line',
        compute='_compute_payment_term_lines',
        string='Payment Term Lines',
        store=False,
    )


    @api.depends('payment_structure_id')
    def _compute_payment_term_lines(self):
        for record in self:
            if record.payment_structure_id:
                record.payment_term_line_ids = record.payment_structure_id.payment_line
            else:
                record.payment_term_line_ids = False

    construction_progress_ids = fields.One2many(
        'property.site.construction.progress',
        compute='_compute_construction_progress',
        string="Construction Progress",
        help="Construction progress associated with this property's site and payment structure"
    )

    def _compute_construction_progress(self):
        for prop in self:
            # Get progress records for this property's site and payment structure
            progress_records = self.env['property.site.construction.progress'].search([
                ('site_id', '=', prop.site.id),
                ('payment_term_id', '=', prop.payment_structure_id.id)
            ])
            prop.construction_progress_ids = progress_records


    current_progress = fields.Float(
        string="Current Progress (%)",
        compute='_compute_current_progress',
        store=True,
        digits=(5, 2)
    )
    last_progress_date = fields.Date(
        string="Last Progress Update",
        compute='_compute_current_progress',
        store=True
    )
    @api.depends('construction_progress_ids', 'construction_progress_ids.progress_percentage', 'construction_progress_ids.date')
    def _compute_current_progress(self):
        for prop in self:
            if prop.construction_progress_ids:
                # get latest by date
                latest = max(prop.construction_progress_ids, key=lambda p: p.date)
                prop.current_progress = latest.progress_percentage
                prop.last_progress_date = latest.date
            else:
                prop.current_progress = 0.0
                prop.last_progress_date = False


class PropertyPaymentLine(models.Model):
    _inherit = 'property.payment.line'

    @api.depends('expected', 'sale_id.new_sale_price', 'payment_term_id')
    def compute_expected_amount(self):
        for rec in self:
            term = rec.payment_term_id
            if term.payment_type == 'fixed':
                rec.expected_amount = term.amount or 0.0
            else:
                rec.expected_amount = rec.expected * rec.sale_id.new_sale_price / 100.0


class PropertySale(models.Model):
    _inherit = 'property.sale'

    def create_payment_term_line(self, sale_id, _unused_term, reservation_id, sale_price, sale_rec):
        sale = self.browse(sale_id)
        term = sale.property_payment_term
        payments = self.env['property.reservation.payment'].search([
            ('reservation_id', '=', reservation_id),
            ('payment_status', '!=', 'canceled'),
        ])
        total_paid = sum(p.amount for p in payments)

        # ----- FIXED TERM -----
        if term.payment_type == 'fixed':
            remaining = total_paid
            for line in term.payment_line.sorted(key=lambda l: l.id):
                exp_amt = line.amount or 0.0
                paid_amt = min(remaining, exp_amt) if remaining > 0 else 0.0
                remaining -= paid_amt

                self.env['property.payment.line'].create({
                    'sale_id':         sale_id,
                    'payment_term_id': line.id,
                    'expected':        0.0,
                    'expected_amount': exp_amt,
                    'paid_amount':     paid_amt,
                })
            return

        # ----- PERCENTAGE TERM (untouched) -----
        rate = total_paid / sale_price if sale_price else 0.0
        discounts = self.env['property.payment.discount'].search([
            ('payment_term_id', '=', term.id),
            ('amount_from', '<=', rate),
            ('amount_to',   '>=', rate),
        ], limit=1)
        if discounts and discounts.is_from_paid:
            return self.create_sale_payment_term(discounts, total_paid, sale_rec)
        if discounts and discounts.discount_start_from == 'all':
            sale_price = sale_price * (1 - discounts.amount)
        remaining = total_paid
        for line in term.payment_line.sorted(key=lambda l: l.id):
            pct     = line.percentage
            exp_amt = sale_price * pct / 100.0
            paid_amt= min(remaining, exp_amt) if remaining > 0 else 0.0
            remaining -= paid_amt
            self.env['property.payment.line'].create({
                'sale_id':         sale_id,
                'payment_term_id': line.id,
                'expected':        pct,
                'expected_amount': exp_amt,
                'paid_amount':     paid_amt,
            })

