# -*- coding: utf-8 -*-
##############################################################################
#
#    Ahadubit Technologies
#    Copyright (C) 2024-TODAY Ahadubit Technologies(<https://ahadubit.com>).
#    Author: Ahadubit Technologies (<https://ahadubit.com>)
#    you can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    GENERAL PUBLIC LICENSE (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from email.policy import default

from odoo import models, fields,api, _
from odoo.exceptions import ValidationError

class PropertySale(models.Model):
    _inherit = 'property.sale'
    _description = 'Property Sale'
    _order = 'create_date desc'

    site_id = fields.Many2one('property.site', string='Site', related='property_id.site', store=True)
    state = fields.Selection([('draft', 'Draft'), ('request_for_confirm', 'Request for Confirmation'),('confirm', 'Confirm'),('cancel', 'Cancel')], default=False, string="State", tracking=True)
    discount = fields.Monetary(
        string="Special Discount",
        readonly=True,
    )

    payment_based_discount = fields.Monetary(
        string="Discount",
        compute="compute_payment_based_discount",
    )

    has_discount = fields.Boolean(
        string="Has Discount",
        compute="compute_discount_of_sales"
    )
    has_payment_based_discount = fields.Boolean(
        string="Has Discount",
        compute="compute_discount_of_sales"
    )

    sale_price = fields.Monetary(string="Sale Price",
                                 readonly=False,
                                 related=False,
                                 compute="compute_sale_rice",
                                 store=True,
                                 help='The price of the property')
    payment_installment_line_ids=fields.One2many('property.payment.line', inverse_name='sale_id')
    cancel_reason=fields.Char(string="Cancel Reason")
    discount_line_id=fields.Many2one('property.payment.discount')

    total_discount = fields.Float(
        string="Total Discount",
        compute="compute_total_discount",
        store=True
    )

    total_paid = fields.Float(
        string="Paid",
        compute="compute_total_paid",
        store = True
    )
    remaining = fields.Float(
        string="Remaining",
        compute="compute_remaining",
        store = True
    )
    new_sale_price = fields.Float(
        string="New Sale Price",
        compute="compute_new_sale_price",
        store=True
    )
    is_from_reservation = fields.Boolean(
        string="is from Reservation"
    )
    show_new_price = fields.Boolean(
        related="discount_line_id.is_from_paid"
    )
    is_verified = fields.Boolean(string="Verified", compute="compute_is_verified")
    order_date = fields.Date(string="Order Date",
                             default=fields.date.today(),
                             help='The order date of property')

    @api.depends('sale_price','discount_line_id','total_paid')
    def compute_new_sale_price(self):
        for rec in self:
            if rec.discount_line_id and rec.discount_line_id.is_from_paid:
                rec.new_sale_price=rec.sale_price - rec.total_paid*rec.discount_line_id.amount
            else:
                rec.new_sale_price = rec.sale_price


    def compute_is_verified(self):
        for rec in self:
            print("Checking verification for record:", rec)
            if rec.reservation_id:
                payment_list = self.env['property.reservation.payment'].search([
                    ('is_verifed', '=', False),
                    ('reservation_id', '=', rec.reservation_id.id)
                ])
                rec.is_verified = not payment_list
            else:
                rec.is_verified = True

    @api.depends('payment_based_discount','discount')
    def compute_total_discount(self):
        for rec in self:
            rec.total_discount=rec.payment_based_discount + rec.discount


    @api.depends('payment_installment_line_ids')
    def compute_total_paid(self):
        for rec in self:
            rec.total_paid = sum(line.paid_amount for line in rec.payment_installment_line_ids)


    @api.depends('total_paid','payment_based_discount','discount')
    def compute_remaining(self):
        for rec in self:
            rec.remaining = rec.sale_price - (rec.total_paid + rec.payment_based_discount + rec.discount)

    @api.depends('sale_price', 'discount_line_id', 'total_paid')
    def compute_payment_based_discount(self):
        for rec in self:
            if rec.property_payment_term.apply_discount:
                paid_amount=sum(line.paid_amount for line in rec.payment_installment_line_ids)
                rate = (paid_amount/rec.sale_price)
                discounts = self.env['property.payment.discount'].search([('payment_term_id', '=', rec.property_payment_term.id),
                    ('amount_from', '<=', rate),('amount_to', '>=', rate)],limit=1)
                if discounts:
                    rec.discount_line_id=discounts.id
                    if discounts.is_from_paid:
                        rec.payment_based_discount = rec.total_paid * discounts.amount
                    else:
                        rec.payment_based_discount = rec.sale_price * discounts.amount


                else:
                    rec.payment_based_discount=0
            else:
                rec.payment_based_discount=0


    def request_for_confirmation_action(self):
        for rec in self:
            rec.state="request_for_confirm"


    def action_cancel_sale(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Cancel Reservation',
            'res_model': 'cancellation.sale.reason.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_sale_id': self.id,
            }
        }

    def compute_discount_of_sales(self):
        for rec in self:
            rec.has_discount =rec.discount>0
            rec.has_payment_based_discount =rec.payment_based_discount>0

    @api.depends('property_id','partner_id')
    def compute_sale_rice(self):
        for rec in self:
            discount_amount = 0.0
            total = 0.0
            discounts = self.env['property.special.discount'].search([
                ('partner_id', '=', rec.partner_id.id),
                ('property_id', '=', rec.property_id.id),
                ('status', '=', 'approved')
            ])
            for dis in discounts:
                total += dis.discount
            if rec.property_id.sale_rent == "for_sale":
                discount_amount = rec.property_id.unit_price - (rec.property_id.unit_price * total)
            elif rec.property_id.sale_rent == "for_tenancy":
                discount_amount = rec.property_id.rent_month - (rec.property_id.rent_month * total)

            rec.sale_price=rec.property_id.unit_price
            rec.discount=rec.property_id.unit_price - discount_amount

    @api.model
    def create(self, vals):
        property_id = vals.get("property_id")
        if property_id:
            sold_property = self.env['property.property'].search([('id', '=', property_id)], limit=1)
            if sold_property:
                sold_property.sudo().write({'state': 'sold'})
        vals["state"] = "draft"
        # Create the record
        res = super(PropertySale, self).create(vals)
        self.create_payment_term_line(res.id, res.property_payment_term,res.reservation_id.id,(res.sale_price - res.discount),res)
        self.add_discount_on_payment_term(res)
        self.add__special_discount_on_payment_term(res)
        return res

    def create_payment_term_line(self, sale_id, payment_term,reservation_id, sale_price,res):
            if payment_term:
                payment_list=self.env['property.reservation.payment'].search([('reservation_id', '=', reservation_id),('payment_status', '!=', 'canceled')])
                total_payment=sum(payment.amount for payment in payment_list)
                rate = (total_payment /sale_price)
                discounts = self.env['property.payment.discount'].search(
                    [('payment_term_id', '=', payment_term.id),
                     ('amount_from', '<=', rate), ('amount_to', '>=', rate)], limit=1)

                if discounts and discounts.is_from_paid:
                    self.create_sale_payment_term(discounts,total_payment,res)
                else:
                    if discounts and discounts.discount_start_from == "all":
                        sale_price = sale_price -( sale_price * discounts.amount)
                    for line in payment_term.payment_line:
                        paid_amount=0
                        if total_payment>0:
                            expected=sale_price*line.percentage/100
                            if total_payment>expected:
                                total_payment=total_payment - expected
                                paid_amount =expected
                            else:
                                paid_amount = total_payment
                                total_payment=0
                        self.env['property.payment.line'].create({
                            'sale_id': sale_id,
                            'payment_term_id': line.id,
                            'expected': line.percentage,
                            'paid_amount': paid_amount,
                        })

    def create_sale_payment_term(self,discounts,total_payment,res):
        sale_price=res.sale_price
        sale_price = sale_price - (total_payment * discounts.amount)
        new_rate = (total_payment/sale_price)*100
        is_first=True
        total_rate=new_rate
        for line in res.property_payment_term.payment_line:
            if total_rate < 100:
                if is_first:
                    self.env['property.payment.line'].create({
                            'sale_id': res.id,
                            'payment_term_id': line.id,
                            'expected': new_rate,
                            'paid_amount': total_payment,
                        })
                    is_first=False
                else:
                    if (total_rate + line.percentage)>100:
                        pres=100 - total_rate
                    else:
                        pres = line.percentage

                    self.env['property.payment.line'].create({
                        'sale_id': res.id,
                        'payment_term_id': line.id,
                        'expected': pres,
                        'paid_amount': 0,
                    })

                    total_rate+=line.percentage



    def add_discount_on_payment_term(self, res):
        if res.has_payment_based_discount:
            payment_lines=[]
            if res.discount_line_id and not res.discount_line_id.is_from_paid:
                discount = res.payment_based_discount
                this_disc = 0
                if res.discount_line_id.discount_start_from == "all":
                    payment_lines = self.env['property.payment.line'].search(
                        [('sale_id', '=', res.id)])
                    for line in payment_lines:
                        line.write({
                            'discount':discount*(line.expected/100)
                        })
                else:
                    if res.discount_line_id.discount_start_from=="1":
                        payment_lines = self.env['property.payment.line'].search(
                            [('sale_id', '=', res.id),('state', 'in', ['partial','not_paid'])],
                            order="sequence asc"
                        )
                    elif res.discount_line_id.discount_start_from == "2":
                        payment_lines = self.env['property.payment.line'].search(
                            [('sale_id', '=', res.id),('state', 'in', ['partial','not_paid'])],
                            order="sequence desc"
                        )
                    for line in payment_lines:
                        if (line.expected_amount - line.paid_amount) > discount:
                            this_disc=discount
                            discount=0
                        else:
                            this_disc = line.expected_amount - line.paid_amount
                            discount = discount - (line.expected_amount - line.paid_amount)
                        line.write({
                            'discount':this_disc
                        })

    def add__special_discount_on_payment_term(self, res):
        if res.discount and res.discount > 0:
            payment_lines = self.env['property.payment.line'].search(
                [('sale_id', '=', res.id)])
            for line in payment_lines:
                line.write({
                    'discount':line.discount + (res.discount*line.expected/100)
                })









