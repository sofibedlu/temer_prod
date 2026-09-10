# -*- coding: utf-8 -*-
from email.policy import default

from odoo import models, fields, api,_
import logging
from odoo.exceptions import ValidationError
from odoo.tools.populate import compute

_logger = logging.getLogger(__name__)


class PropertyCommission(models.Model):
    _inherit = "property.commission"
    type = fields.Selection(
        [
            ("sales", "Sales"),
            ("other", "Other"),
        ],
        string="Type",
        default='sales')
    self_rate = fields.Float('Self Rate')
    commission = fields.Float(string='Hierarchy Commission Rate')

    @api.constrains('self_rate')
    def validate_self_rate(self):
        for rec in self:
            if rec.self_rate<=0:
                raise ValidationError("Self Rate must be > 0")





class PropertyInherit(models.Model):
    """A class for the model property to represent the property"""

    _inherit = "property.property"
    name = fields.Char(
        string="Name", required=False, copy=True,
        default=lambda self: _("New"),
        help="Name of the Property"
    )


    site = fields.Many2one('property.site',
                           required=True,
                           domain=[('state', 'not in', ['archived'])],
                           string="site")
    block = fields.Many2one('property.block',required=True,string="Block No"
                            , domain="[('site', '=', site)]", store=True, readonly=False )
    unique_identification = fields.Many2one('property.unique.identification')
    floor_no = fields.Char('Floor #', required=True,)
    gross_area = fields.Float('Gross Area(m2)', compute='compute_property_details')
    net_area = fields.Float('Net Area(m2)', compute='compute_property_details')
    bedroom = fields.Integer(
        string="Bedrooms", help="Number of bedrooms in the property", compute='compute_property_details'
    )
    bathroom = fields.Integer(
        string="Bathrooms", help="Number of bathrooms in the property",compute='compute_property_details'
    )
    # no_of_Bathrooms = fields.Integer('Number Of Bathrooms', compute='compute_property_details')
    # no_of_bedrooms = fields.Integer('Number Of Bedrooms', compute='compute_property_details')
    price = fields.Float('Price(m2)',compute="compute_unit_price")
    unit_price = fields.Monetary('Sales Price?', compute="compute_total_price")
    rent_month = fields.Monetary('Rent/Month', compute="compute_total_price")
    sale_rent = fields.Selection(
        [
            ("for_sale", "For Sale"),
            ("for_tenancy", "For Rent"),
            ("for_auction", "For Auction"),
        ],
        string="Sale | Rent",
        required=False,
        default='for_sale'
    )
    property_type = fields.Selection(
        [
            ("residential", "Residential"),
            ("commercial", "Commercial"),
            ("industry", "Industry"),
            ("land", "Land"),
        ],
        string="Type",
        required=True,
        default="residential",
        help="The type of the property",
    )

    state  = fields.Selection(
        [
            ("draft", "Draft"),
            ("available", "Available"),
            ("rented", "Rented"),
            ("reserved", "Reserved"),
            ("sold", "Sold"),
        ],
        required=True,
        string="Status",
        default="draft",
        help="* The 'Draft' status is used when the property is in draft.\n"
             "* The 'Available' status is used when the property is "
             "available or confirmed\n"
             "* The 'Rented' status is used when the property is rented.\n"
             "* The 'sold' status is used when the property is sold.\n",
    )
    country_id = fields.Many2one(
        "res.country",
        string="Country",
        ondelete="restrict",
        required=True,
        help="The name of the country",
        compute='set_address_information'
    )
    city_id = fields.Many2one('property.site.city',compute='set_address_information', string="City", tracking=True)
    sub_city_id = fields.Many2one('property.site.subcity',compute='set_address_information', string="Sub City", domain="[('city_id', '=', city_id)]",
                                   tracking=True)
    wereda = fields.Char(string="Woreda",compute='set_address_information',  tracking=True)
    area = fields.Char(string="Area name", compute='set_address_information')
    street = fields.Char(string="Street", required=False, help="The street name")
    property_type_id = fields.Many2one('property.type',required=True, help="Property Type")
    sequence = fields.Integer(default=1)

    responsible_id = fields.Many2one(
        "res.users",
        string="Stock Manager",
        help="The responsible person for " "this property",
        default=lambda self: self.env.user,
    )
    payment_structure_id = fields.Many2one('property.payment.term', string="Payment Structure")
    site_payment_structure_id = fields.Many2one('property.payment.type',
                                                domain="[('site_id', '=', site),('property_type','=',property_type)]",
                                                string="Payment Structure")
    is_multi = fields.Boolean(compute='compute_is_multi_payment')

    is_show_address=fields.Boolean(compute="compute_show_address")

    @api.depends('name')
    def compute_show_address(self):
        show_address_detail = self.env['ir.config_parameter'].sudo().get_param('realestate_base.show_address_detail', default=False)
        for rec in self:
            rec.is_show_address=show_address_detail


    _sql_constraints = [
        ('unique_name', 'unique(name)', 'The Name must be unique.'),
    ]


    @api.depends('property_type_id')
    def compute_property_details(self):
        for rec in self:
            rec.bedroom = rec.property_type_id.number_be_room
            rec.bathroom = rec.property_type_id.number_bath_room
            rec.net_area = rec.property_type_id.net_area
            rec.gross_area = rec.property_type_id.gross_area

    @api.constrains('gross_area','net_area')
    def validate_gross_and_net_area(self):
        for rec in self:
            if rec.gross_area<=0:
                raise  ValidationError("Gross Area Must be > 0")
            if rec.net_area <= 0:
                raise  ValidationError("Net Area Must be > 0")


    @api.depends('site','payment_structure_id','site_payment_structure_id')
    def compute_unit_price(self):
        for rec in self:
            if rec.site.site_type.multi_payment_method:
                if rec.site_payment_structure_id:
                    rec.price=rec.site_payment_structure_id.price
                else:
                    rec.price=0
            else:
                rec.price=rec.site.price_per_m2


    @api.depends('site')
    def compute_is_multi_payment(self):
        for rec in self:
            rec.is_multi = rec.site.site_type.multi_payment_method

    @api.onchange('site','property_type')
    def select_payment_term(self):
        for rec in self:
            if not rec.site.site_type.multi_payment_method:
                rec.payment_structure_id=rec.site.payment_structure_id.id
            else:
               property_line=self.env['property.payment.type'].search([('site_id', '=', rec.site.id),('property_type', '=', rec.property_type)], limit=1)
               if len(property_line)>0:
                   rec.payment_structure_id=property_line.payment_term_id.id
               else:
                   return {
                       'domain': {
                           'payment_structure_id': [('id', 'in', rec.site.payment_line_ids.payment_term_id.ids)]
                       }
                   }


    @api.model
    def create(self, vals):
        site=self.env['property.site'].search([('id', '=', vals["site"])], limit=1)
        block=self.env['property.block'].search([('id', '=', vals["block"])], limit=1)
        pro_type=self.env['property.type'].search([('id', '=', vals["property_type_id"])], limit=1)
        floor=vals["floor_no"]
        vals["name"]=f"{site.name}-{block.name}-F{floor}-{pro_type.code}"
        property = self.env['property.property'].search([('name', '=', vals["name"])], limit=1)
        if len(property)>0:
            raise  ValidationError('Property with the given detail already exist')
        res = super(PropertyInherit, self).create(vals)
        return res


    def copy(self, default=None):
        for rec in self:
            if default is None:
                default = {}
            default['name'] = f"{rec.name} Copy"

        return super().copy(default)

    @api.depends('site')
    def set_address_information(self):
        for rec in self:
            rec.country_id=rec.site.country_id
            rec.city_id=rec.site.city_id
            rec.sub_city_id=rec.site.sub_city_id
            rec.wereda=rec.site.wereda
            rec.area=rec.site.area
            rec.latitude =rec.site.latitude
            rec.longitude=rec.site.longitude



    @api.onchange('site')
    def _onchange_site(self):
        for rec in self:
            rec.block = False


    def action_available(self):
        for rec in self:
            rec.state='available'

    @api.depends('site', 'gross_area','sale_rent','price')
    def compute_total_price(self):
        for rec in self:
            if rec.sale_rent=="for_sale":
                rec.unit_price=rec.price*rec.gross_area
                rec.rent_month=0
            elif  rec.sale_rent=="for_tenancy":
                rec.rent_month = rec.price * rec.gross_area
                rec.unit_price = 0
            else:
                rec.unit_price=0
                rec.rent_month=0


class PropertySiteCommision(models.Model):
    _name = 'property.site.commission'

    property_sale = fields.Many2one('property.sale')
    partner = fields.Many2one('res.partner')
    commition_type = fields.Many2one('property.commission')
    commission_percentage = fields.Float('Percentage')
    commission_amount = fields.Float('Commission')
    state = fields.Selection(related='property_sale.state', string="State", store=True, readonly=True)
    is_billed = fields.Boolean(default=False)
    bill_state = fields.Boolean(default=False)

    @api.onchange("state","is_invoiced")
    def _onchange_state(self):
        if self.state == 'confirm' and self.is_billed == False:
            self.bill_state = True

    def commission_bill(self):
        """Generate Bills Based on the Monetary Values and return
            Bills Form View"""
        self.write({'is_billed': True})
        return {
            'name': _('Commission Bill'),
            'view_mode': 'form',
            'res_model': 'account.move',
            'target': 'current',
            'type': 'ir.actions.act_window',
            'context': {
                'default_move_type': 'in_invoice',
                'default_company_id': self.env.user.company_id.id,
                'default_partner_id': self.property_sale.broker_id.id,
                'default_property_order_id': self.id,
                'default_invoice_line_ids': [fields.Command.create({
                    'name': self.property_sale.name+" for " + self.partner.name +"-"+self.commition_type.name,
                    'price_unit': self.commission_amount,
                    'currency_id': self.env.user.company_id.currency_id.id,
                })]
            }
        }

class PropertySalePaymentTermLine(models.Model):
    _name = 'property.sale.payment.term.line'

    property_sale = fields.Many2one('property.sale')
    property_payment_term = fields.Many2one('property.payment.term')
    property_payment_term_line = fields.Many2one('property.payment.term.line')
    percentage = fields.Float('Percentage')
    amount = fields.Float('Amount')
    is_invoiced = fields.Boolean(default=False)
    state = fields.Selection(related='property_sale.state', string="State", store=True, readonly=True)
    invoice_state = fields.Boolean(default=False)

    @api.onchange("state","is_invoiced")
    def _onchange_state(self):
        if self.state == 'confirm' and self.is_invoiced == False:
            self.invoice_state = True

    def generate_invoice(self):
           
        """Generate Invoice Based on the Monetary Values and return
        Invoice Form View"""
        # Ensure the invoiced status is updated correctly
        self.write({'is_invoiced': True})

        # Generate the invoice action
        return {
            'name': _('Invoice'),
            'view_mode': 'form',
            'res_model': 'account.move',
            'target': 'current',
            'type': 'ir.actions.act_window',
            'context': {
                'default_move_type': 'out_invoice',
                'default_company_id': self.env.user.company_id.id,
                'default_partner_id': self.property_sale.partner_id.id,
                'default_property_order_id': self.property_sale.id,
                'default_invoice_line_ids': [fields.Command.create({
                    'name': self.property_payment_term_line.name,
                    'price_unit': self.amount,
                    'currency_id': self.env.user.company_id.currency_id.id,
                })],
            }
        }

class Property(models.Model):
    """A class for the model property to represent the property"""

    _inherit = "property.sale"

   
    property_payment_term = fields.Many2one('property.payment.term')
    property_payment_term_line = fields.One2many('property.sale.payment.term.line','property_sale')
    commission_detail = fields.One2many('property.site.commission','property_sale')
    commission_type = fields.Char(
        string="Commission Type",
        help='The type of the commission')
    
    def write(self, vals):
        # _logger.info("----write.is_invoiced")
        # _logger.info(vals)
        res = super().write(vals)
        if vals.get('state') == 'confirm':
            payment_terms = self.env['property.sale.payment.term.line'].search([('property_sale', '=', self.id)])
            for payment_term in payment_terms:
                # _logger.info("----payment_term.is_invoiced")
                # _logger.info(payment_term.is_invoiced )
                if payment_term.is_invoiced == False:
                    payment_term.write({'invoice_state':True})
                else:
                    payment_term.write({'invoice_state':False})

            bill_terms = self.env['property.site.commission'].search([('property_sale', '=', self.id)])
            for bill_term in bill_terms:
                if bill_term.is_billed == False:
                    bill_term.write({'bill_state':True})
                else:
                    bill_term.write({'bill_state':False})
        return res

   


    @api.onchange("property_payment_term")
    def _onchange_property_payment_term(self):
        for rec in self:
            payment_lines = []
            for payment_line in rec.property_payment_term.payment_line:
                amount = rec.sale_price * payment_line.percentage/100


                payment_lines_value = {
                    'property_payment_term_line': payment_line.id,
                    'percentage': payment_line.percentage,
                    'amount': amount,
                }
                payment_lines.append((0, 0, payment_lines_value))
            rec.property_payment_term_line = payment_lines


    @api.depends('commission_plan_id', 'sale_price')
    def _compute_commission_and_commission_type(self):
        for rec in self:
            total_commission = 0
            for detail in self.commission_detail:
                total_commission += detail.commission_amount
            
            rec.commission = total_commission
            rec.commission_type = ""
  

    
    def calculatecommission(self):
        # Clear existing commission details
        self.commission_detail.unlink()

        commission_detail = []
        total_commission = 0
        partner_id = self.broker_id

        def calculate_commission_amount(entity, use_self_rate=False):
            """Helper function to calculate commission based on type and rate."""
            if entity.commision_type.commission_type == 'percentage':
                rate = entity.commision_type.self_rate if use_self_rate else entity.commision_type.commission
                return self.sale_price * rate / 100
            return entity.commision_type.self_rate if use_self_rate else entity.commision_type.commission

        def add_commission_detail(entity, use_self_rate=False):
            """Helper function to add commission details."""
            commission_amount = calculate_commission_amount(entity, use_self_rate)
            commission_detail_values = {
                'partner': entity.id,
                'commition_type': entity.commision_type.id,
                'commission_amount': commission_amount,
                'commission_percentage': entity.commision_type.self_rate if use_self_rate else entity.commision_type.commission
            }
            commission_detail.append((0, 0, commission_detail_values))
            return commission_amount

        if partner_id.commision_type.type != 'other':
            user_id = self.env['res.users'].search([('partner_id', '=', partner_id.id)]).id
            crm_team = self.env['crm.team.member'].search([('user_id', '=', user_id)])
            manager, supervisor = crm_team.crm_team_id.manager, crm_team.crm_team_id.user_id

            if user_id not in (manager.id, supervisor.id):
                total_commission += add_commission_detail(partner_id)
                if manager:
                    total_commission += add_commission_detail(manager.partner_id)
                if supervisor:
                    total_commission += add_commission_detail(supervisor.partner_id)
            elif user_id == supervisor.id:
                if manager:
                    total_commission += add_commission_detail(manager.partner_id)
                total_commission += add_commission_detail(supervisor.partner_id, use_self_rate=True)
            elif user_id == manager.id:
                total_commission += add_commission_detail(manager.partner_id, use_self_rate=True)
        else:
            total_commission += add_commission_detail(partner_id, use_self_rate=True)

        # Update the commission details and total commission
        self.commission_detail = commission_detail
        self.commission = total_commission

        