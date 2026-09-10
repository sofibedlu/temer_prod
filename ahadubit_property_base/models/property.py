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
from odoo import models, fields, api,_
import logging
from odoo.exceptions import ValidationError
from odoo.tools.populate import compute
_logger = logging.getLogger(__name__)


 


class PropertyInherit(models.Model):
    """A class for the model property to represent the property"""

    _inherit = "property.property"
    _order = 'name asc, create_date desc'

    name = fields.Char(
        string="Name", 
        required=False, 
        copy=True,
        compute='_compute_property_name',
        store=True,
        help="Name of the Property"
    )    

    # name = fields.Char(
    #     string="Name", required=False, copy=True,
    #     default=lambda self: _("New"),
    #     help="Name of the Property"
    # )

    property_type = fields.Selection(
        [
            ("residential", "Residential"),
            ("commercial", "Commercial"),
        ],
        string="Type",
        required=True,
        help="The type of the property",
    )
    
    site = fields.Many2one('property.site',required=True,
                           string="site",)
    site_property_type_id = fields.Many2one('site.property.type.line',string="Property Type",
                                            domain="[('site', '=', site)]",
                                            required=True, help="Property Type")
    property_type_id = fields.Many2one('property.type',related='site_property_type_id.property_type_id', required=True, help="Property Type", store=True)
    block = fields.Many2one('property.block',required=True,string="Block No"
                            , domain="[('site', '=', site)]", store=True, readonly=False)
    unique_identification = fields.Many2one('property.unique.identification')
    floor_ids_domian = fields.Many2many('property.floor',compute="_onchange_floor_ids")
    floor_ids = fields.Many2many(
        'property.floor',
        domain="[('id', 'not in', floor_ids_domian)]",
        string='Floor #',
        required=True,
        store=False,
        selectable=False
    )

    floor_id = fields.Many2one(
        'property.floor', string='Floor #'
    )
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
            ("pending_sales", "Pending Sales"),
            ("sold", "Sold"),
        ],
        required=False,
        string="Status",
        default=False,
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
    furnishing = fields.Selection(
        [
            ("no_furnished", "Not Furnished"),
            ("half_furnished", "Partially Furnished"),
            ("furnished", "Fully Furnished"),
        ],
        string="Furnishing",
        help="Whether the residence is fully furnished or partially/half "
             "furnished or not at all furnished",
    )
    finishing = fields.Selection(
        [
            ("sumi_finished", "Semi Finished"),
            ("fully_finished", "Fully Finished"),
            ("none", "None"),
        ],
        string="Finishing",
        help="Whether the residence is fully Finished or partially/half "
             "finished or not at all furnished",
    )
    is_show_address=fields.Boolean(compute="compute_show_address")
    reservation_end_date=fields.Datetime(compute="compute_reservation_end_date")
    _sql_constraints = [
        ('unique_name', 'unique(name)', 'The Name must be unique.'),
    ]

    @api.depends('state')
    def compute_reservation_end_date(self):
        for rec in self:
            last_reservation = self.env['property.reservation'].search([('property_id', '=', rec.id),('status', '=', 'reserved')],order='expire_date asc', limit=1)
            if last_reservation:
                rec.reservation_end_date=last_reservation.expire_date
            else:
                rec.reservation_end_date =False


    @api.onchange('site_property_type_id')
    def add_property_type_image(self):
        for rec in self:
            if rec.property_type_id and rec.property_type_id.image:
                rec.property_image_ids = [(5, 0, 0)]  # Remove existing records
                rec.property_image_ids = [(0, 0, {
                    'name': "Property type image",
                    'image': rec.site_property_type_id.image,
                })]

    @api.depends('site','block','site_property_type_id')
    def _onchange_floor_ids(self):
        for rec in self:
            if rec.site and rec.block and rec.site_property_type_id:
                existing_property=self.env['property.property'].search([('site','=',rec.site.id),('block','=',rec.block.id),('site_property_type_id','=',rec.site_property_type_id.id)])
                floor_ids = existing_property.mapped('floor_id')
                rec.floor_ids_domian=floor_ids
            else:
                rec.floor_ids_domian = []


    @api.onchange('site')
    def property_type_filter_domains(self):
        for rec in self:
            if rec.site:
                property_type_ids = rec.site.property_type_lin_ids.mapped('property_type_id').ids
                return {'domain': {'property_type_id': [('id', 'in', property_type_ids)]}}
            else:
                return {'domain': {'property_type_id': []}}

    @api.depends('name')
    def compute_show_address(self):
        show_address_detail = self.env['ir.config_parameter'].sudo().get_param('ahadubit_property_base.show_address_detail', default=False)
        for rec in self:
            rec.is_show_address=show_address_detail

    @api.onchange('site')
    def compute_finishing(self):
        for rec in self:
            rec.finishing = rec.site.finishing if rec.site else 'none'

    @api.depends('property_type_id','site')
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
    def write(self, vals):
        if 'state' in vals and vals['state']:
            state= vals['state']
            if state != "reserved":
                channel = self.env['discuss.channel'].search([('name', '=', 'general')], limit=1)
                if channel:
                    if state == "sold" and self.state == 'pending_sales':
                        channel.message_post(
                            body=(f"Property {self.name} is now sold"),
                            message_type='comment',
                            subtype_xmlid='mail.mt_comment',
                        )
                    elif state == "available":
                        channel.message_post(
                            body=(f"Property {self.name} is now available"),
                            message_type='comment',
                            subtype_xmlid='mail.mt_comment',
                        )
        records = super(PropertyInherit, self).write(vals)
        return records
#===================================================================
               #Added By Shimelis Mulugeta 06-11-2025
#===================================================================    
    
    @api.depends('site.name', 'block.name', 'floor_id.name', 'property_type_id.code')
    def _compute_property_name(self):
        for rec in self:
            if rec.site and rec.block and rec.floor_id and rec.property_type_id:
                rec.name = f"{rec.site.name}-{rec.block.name}-F{rec.floor_id.name}-{rec.property_type_id.code}"
            else:
                rec.name = _("New")

    @api.model
    def create(self, vals):
        if 'site_property_type_id' in vals and 'property_type_id' not in vals:
            site_property_type = self.env['site.property.type.line'].browse(vals['site_property_type_id'])
            vals['property_type_id'] = site_property_type.property_type_id.id

        site = self.env['property.site'].browse(vals["site"])
        block = self.env['property.block'].browse(vals["block"])
        pro_type = self.env['site.property.type.line'].browse(vals["site_property_type_id"])

        created_records = self.env['property.property']

        if 'floor_ids' in vals:
            floor_ids = []
            for command in vals["floor_ids"]:
                if command[0] == 6:
                    floor_ids.extend(command[2])
                elif command[0] == 4:
                    floor_ids.append(command[1])

            for floor_id in floor_ids:
                floor = self.env['property.floor'].browse(floor_id)
                
                # Remove the manual name generation since it's now computed
                # The name will be automatically computed based on the related fields
                
                record_vals = vals.copy()
                record_vals.update({
                    "floor_id": floor_id,
                    "state": "draft",
                })

                created_record = super(PropertyInherit, self).create(record_vals)
                
                # Check for duplicates using the computed name
                if created_record.name != _("New"):
                    existing = self.env['property.property'].search([
                        ('name', '=', created_record.name),
                        ('id', '!=', created_record.id)
                    ], limit=1)
                    if existing:
                        created_record.unlink()
                        raise ValidationError(f'Property with the detail "{created_record.name}" already exists.')
                
                created_records |= created_record
        else:
            vals["state"] = "draft"
            created_records = super(PropertyInherit, self).create(vals)
        
        return created_records

    # @api.model
    # def create(self, vals):
    #     if 'site_property_type_id' in vals and 'property_type_id' not in vals:
    #         site_property_type = self.env['site.property.type.line'].browse(vals['site_property_type_id'])
    #         vals['property_type_id'] = site_property_type.property_type_id.id

    #     site = self.env['property.site'].browse(vals["site"])
    #     block = self.env['property.block'].browse(vals["block"])
    #     pro_type = self.env['site.property.type.line'].browse(vals["site_property_type_id"])

    #     created_records = self.env['property.property']

    #     if 'floor_ids' in vals:
    #         floor_ids = []
    #         for command in vals["floor_ids"]:
    #             if command[0] == 6:  # Replace all with new IDs
    #                 floor_ids.extend(command[2])
    #             elif command[0] == 4:  # Add a single ID
    #                 floor_ids.append(command[1])

    #         for floor_id in floor_ids:
    #             floor = self.env['property.floor'].browse(floor_id)
    #             floor_name = floor.name

    #             property_name = f"{site.name}-{block.name}-F{floor_name}-{pro_type.property_type_id.code}"

    #             old_property = self.env['property.property'].search([('name', '=', property_name)], limit=1)
    #             if old_property:
    #                 raise ValidationError(f'Property with the detail "{property_name}" already exists.')

    #             record_vals = vals.copy()
    #             record_vals.update({
    #                 "name": property_name,
    #                 "floor_id": floor_id,
    #                 "state": "draft",
    #             })

    #             created_records |= super(PropertyInherit, self).create(record_vals)
    #     else:
    #         vals["state"] = "draft"
    #         created_records = super(PropertyInherit, self).create(vals)
    #     return created_records


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
            facility_ids = rec.site.facility_ids.mapped('facility_id')
            rec.facility_ids = facility_ids


    @api.onchange('site')
    def _onchange_site(self):
        for rec in self:
            rec.block = False

    @api.onchange('site_property_type_id')
    def _onchange_site_property_type(self):
        """Update property_type_id when site_property_type_id changes"""
        for rec in self:
            if rec.site_property_type_id:
                rec.property_type_id = rec.site_property_type_id.property_type_id
            else:
                rec.property_type_id = False


    def action_available(self):
        for rec in self:
            if rec.state in ["draft","reserved"]:
                rec.state='available'

    def action_draft(self):
        for rec in self:
            rec.state='draft'

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

    def sold_property(self):
        for rec in self:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Amendment Reservation',
                'res_model': 'property.sale',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_property_id': rec.id,
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
        self.sudo().write({'is_invoiced': True})

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
   
    
    def write(self, vals):
        res = super().write(vals)
        if vals.get('state') == 'confirm':
            payment_terms = self.env['property.sale.payment.term.line'].search([('property_sale', '=', self.id)])
            for payment_term in payment_terms:
                _logger.info("----payment_term.is_invoiced")
                _logger.info(payment_term.is_invoiced )
                if payment_term.is_invoiced == False:
                    payment_term.sudo().write({'invoice_state':True})
                else:
                    payment_term.sudo().write({'invoice_state':False})

           
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

#===================================================================
               #Added By Shimelis Mulugeta 06-11-2025
#===================================================================            
 
class PropertySite(models.Model):
    _inherit = "property.site"
    
    def action_update_property_names(self):
        """Manual button to update property names"""
        properties = self.env['property.property'].search([('site', 'in', self.ids)])
        # Trigger the compute method
        properties._compute_property_name()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': f'Updated names for {len(properties)} properties',
                'type': 'success',
                'sticky': False,
            }
        }        