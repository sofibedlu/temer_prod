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

from pkg_resources import require

from odoo import models, fields, api,_
from odoo.exceptions import ValidationError
import re
import base64

from markupsafe import Markup

from odoo.tools.populate import compute


class PropertyPaymentType(models.Model):
    _name = "property.payment.type"
    _rec_name = 'name'
    name = fields.Char(string="Name", required=True)
    site_id = fields.Many2one('property.site',
                           required=True,string="site")
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
    payment_term_id = fields.Many2one('property.payment.term', string="Payment Term", required=True)
    price = fields.Float( string="price per m2", required=True)


class PropertySiteType(models.Model):
    _name = 'property.site.type'
    name=fields.Char(string="Name", required=True)
    multi_payment_method=fields.Boolean(string="Multi Payment Method", default=False)
    property_type = fields.Selection(
        [
            ("residential", "Residential"),
            ("commercial", "Commercial"),
            ("mixed", "Mixed Use"),
        ],
        string="Type",
        required=True,
        help="The type of the property",
    )

class PropertyFloor(models.Model):
    _name = 'property.floor'
    name=fields.Char(string="name", required=True)
    _sql_constraints = [
        ('unique_name', 'unique(name)', 'The floor must be unique.'),
    ]
class PropertySaleCancel(models.Model):
    _name = 'property.sale.cancel.reason'
    name=fields.Char(string="Reason", required=True)


class SitPropertyTypeLine(models.Model):
    _name = 'site.property.type.line'
    _rec_name = 'property_type_id'
    property_type_id=fields.Many2one('property.type', string="Property Type", required=True)
    site=fields.Many2one('property.site',string="Site")
    number_be_room=fields.Integer(string="Number of bed room", compute='compute_attach_fields_list')
    number_bath_room=fields.Integer(string="Number of bath room",compute='compute_attach_fields_list')
    has_maid_room=fields.Boolean(string="has maid room",compute='compute_attach_fields_list')
    net_area=fields.Float(string="Net area",compute='compute_attach_fields_list')
    gross_area=fields.Float(string="Gross Area",compute='compute_attach_fields_list')
    image=fields.Binary(string="Image",compute='compute_attach_fields_list')

    @api.depends('property_type_id')
    def compute_attach_fields_list(self):
        for rec in self:
            rec.number_be_room=rec.property_type_id.number_be_room
            rec.number_bath_room=rec.property_type_id.number_bath_room
            rec.has_maid_room=rec.property_type_id.has_maid_room
            rec.net_area=rec.property_type_id.net_area
            rec.gross_area=rec.property_type_id.gross_area
            rec.image=rec.property_type_id.image




class PropertyType(models.Model):
    _name = 'property.type'
    _rec_name = 'code'
    code=fields.Char(string="Code", required=True)
    number_be_room=fields.Integer(string="Number of bed room")
    number_bath_room=fields.Integer(string="Number of bath room")
    has_maid_room=fields.Boolean(string="has maid room")
    net_area=fields.Float(string="Net area")
    gross_area=fields.Float(string="Gross Area")
    image=fields.Binary(string="Floor Plan")
    
    
    
    _sql_constraints = [
        ('unique_code', 'unique(code)', 'The code must be unique.'),
    ]

    @api.constrains('gross_area')
    def validate_gross_and_net_area(self):
        for rec in self:
            if rec.gross_area <= 0:
                raise ValidationError("Gross Area Must be > 0")
            # if rec.net_area <= 0:
            #     raise ValidationError("Net Area Must be > 0")

    @api.constrains('gross_area')
    def check_gross_net_area(self):
        for rec in self:
            if rec.gross_area<=0:
                raise ValidationError("Gross Area must be > 0")
            # if rec.net_area<=0:
            #     raise ValidationError("Net Area  must be > 0")




class PropertySiteCity(models.Model):
    _name = 'property.site.city'
    country_id = fields.Many2one(
        "res.country",
        string="Country",
        ondelete="restrict",
        required=True,
        help="The name of the country",
    )
    name=fields.Char(string="City", required=True)

class PropertySiteSubcity(models.Model):
    _name = 'property.site.subcity'
    city_id=fields.Many2one('property.site.city',string="City", required=True)
    name=fields.Char(string="Subcity", required=True)

class PropertySiteFacility(models.Model):
    _name = 'property.site.facility'
    site_id=fields.Many2one('property.site',string="Site")
    facility_id=fields.Many2one('property.facility',string="Facility", required=True)

class PropertySite(models.Model):
    _name = 'property.site'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string="Site name", required=True, tracking = True)
    country_id = fields.Many2one(
        "res.country",
        string="Country",
        ondelete="restrict",
        required=True,
        help="The name of the country",
    )
    city_id = fields.Many2one('property.site.city',string="City", required=True,domain="[('country_id', '=', country_id)]", tracking = True)
    sub_city_id = fields.Many2one('property.site.subcity',string="Sub City", domain="[('city_id', '=', city_id)]", required=True, tracking = True)
    wereda = fields.Char(string="Woreda", required=True, tracking = True)
    house_no = fields.Char(string="House No")
    area = fields.Char(string="Area name")
    phone = fields.Char(string="Telephone Number", required=True)
    email = fields.Char(string="Email Address")
    lessee_name = fields.Char(string="Lessee's Full name", required=True,tracking = True )
    leasehold_certificate = fields.Binary(string="Leasehold Certificate", required=True)
    title_deed_no = fields.Char(string="Title deed no")
    plot_area = fields.Float(string="Plot area(m2)", required=True,tracking = True)
    site_type = fields.Many2one('property.site.type',required=True, string="Site Type")
    floor_structure = fields.Char(string="Floor Structure")
    car_parking = fields.Integer(string="Car Parking Floor", required=True)
    commercial_certificate = fields.Binary(string="Commercial Registration Certificate", required=True)
    taxpayer_certificate = fields.Binary(string="Taxpayer Registration Certificate", required=True)
    # allowed_reservation_days = fields.Integer(string="Allowed Reservation Days")
    payment_structure = fields.Char(string="Payment Structure")
    payment_structure_id = fields.Many2one('property.payment.term',string="Payment Structure")
    currency_id = fields.Many2one('res.currency', string="Currency", required=True,
                                  default=lambda self: self.env.company.currency_id)
    price_per_m2 = fields.Monetary(string="Price per m2", required=True, currency_field='currency_id', tracking=True)
    message_main_attachment_id = fields.Many2one(
        string="Main Attachment",
        comodel_name='ir.attachment')
    payment_term_line_ids=fields.One2many('property.site.payment.term.line', inverse_name='site_id')
    payment_line_ids=fields.One2many('property.payment.type', inverse_name='site_id')
    property_type_lin_ids=fields.One2many('site.property.type.line', inverse_name='site')
    facility_ids=fields.One2many('property.site.facility', string="Facilities", inverse_name='site_id')
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

    latitude = fields.Float(
        string="Latitude",
        digits=(16, 5),
        help="The latitude of where the property is " "situated")
    longitude = fields.Float(
        string="Longitude",
        digits=(16, 5),
        help="The longitude of where the property is " "situated",
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("active", "active"),
            ("archived", "archived"),
        ],
        required=True,
        string="Status",
        default="draft",
    )
    is_multi =fields.Boolean(compute='compute_is_multi_payment')

    @api.depends('site_type')
    def compute_is_multi_payment(self):
        for rec in self:
            rec.is_multi=rec.site_type.multi_payment_method

    def activate_site(self):
        for rec in self:
            rec.state='active'

    def archive_site(self):
        for rec in self:
            properties = self.env['property.property'].search([('site', '=', rec.id)])
            if len(properties)>0:
                raise ValidationError("Cannot archive: available properties exist on this site")
            rec.state='archived'


    @api.onchange('city_id')
    def _onchange_city_id(self):
        self.sub_city_id = False

    @api.onchange('country_id')
    def _onchange_city_id(self):
        self.city_id = False

    @api.onchange('leasehold_certificate')
    def compute_visible_image(self):
        for rec in self:
            if rec.leasehold_certificate:
                attachment = self.env['ir.attachment'].create({
                    'name': 'Leasehold Certificate',
                    'type': 'binary',
                    'datas': rec.taxpayer_certificate,
                    'res_model':'property.site',
                    'res_id': rec.id,
                })
                rec.message_main_attachment_id=attachment.id
            else:
                rec.message_main_attachment_id=False




    @api.constrains('email')
    def _check_email(self):
        # Define a regex pattern for validating an email
        email_pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'

        for record in self:
            if record.email and not re.match(email_pattern, record.email):
                raise ValidationError("Please provide a valid email address.")






class PropertyBlock(models.Model):
    _name = 'property.block'

    name = fields.Char()
    site = fields.Many2one('property.site')

class PropertyUniqueIdentification(models.Model):
    _name = 'property.unique.identification'

    name = fields.Char()

class PropertyPaymentTermLine(models.Model):
    _name = 'property.payment.term.line'

    name = fields.Char()
    percentage = fields.Float()
    payment_term_id = fields.Many2one('property.payment.term','payment_term_id')
    sequence = fields.Integer(default=10)
    sequence_no = fields.Integer(default=1, string="Payment Sequence")


class PropertyPaymentTerm(models.Model):
    _name = 'property.payment.term'

    name = fields.Char()
    apply_discount = fields.Boolean(string="Apply Discount")
    payment_line = fields.One2many('property.payment.term.line','payment_term_id', copy=True)
    discount_line = fields.One2many('property.payment.discount','payment_term_id', copy=True)
    discount_start_from = fields.Selection(
        [
            ("1", "First Payment Term"),
            ("2", "Last Payment Term"),
        ],
        string="Discount Apply From",
        required=True,
        default="1")

    def copy(self, default=None):
        for rec in self:
            if default is None:
                default = {}
            default['name'] = f"{rec.name} Copy"

        return super().copy(default)

    @api.model
    def create(self, vals):
        total_percentage = 0.0
        payment_lines = vals.get('payment_line', [])
        for line in payment_lines:
            if line[0] == 0 and 'percentage' in line[2]:
                total_percentage += line[2].get('percentage', 0.0)
                total_percentage = round(total_percentage, 2)
        if total_percentage != 100:
            raise ValidationError("Total percentage of payment lines must equal 100%.")
        return super(PropertyPaymentTerm, self).create(vals)

    def write(self, vals):
        # if 'payment_line' in vals:
            # total_percentage = sum(line.percentage for line in self.payment_line)
            # for line in vals.get('payment_line', []):
            #     command = line[0]
            #     if command == 0:  # Add new line
            #         total_percentage += line[2].get('percentage', 0.0)
            #     elif command == 1:  # Update existing line
            #         line_id = line[1]
            #         existing_line = self.payment_line.filtered(lambda l: l.id == line_id)
            #         if existing_line:
            #             total_percentage += line[2].get('percentage', 0.0) - existing_line.percentage
            #     elif command == 2:  # Remove existing line
            #         line_id = line[1]
            #         existing_line = self.payment_line.filtered(lambda l: l.id == line_id)
            #         if existing_line:
            #             total_percentage -= existing_line.percentage
            # total_percentage = round(total_percentage, 2)
            # if abs(total_percentage - 100) > 0.01:  # Tolerance of 0.01
            #     # raise ValidationError("Total percentage of payment lines must equal 100%.")
            #     error_details = "\n".join([f"ID: {line.id}, Percentage: {line.percentage}" for line in self.payment_line])

            #     raise ValidationError(
            #         f"Total percentage of payment lines must equal 100%. "
            #         f"Current total: {total_percentage:.2f}%, "
            #         f"Deviation: {abs(total_percentage - 100):.2f}%\n"
            #         f"Existing Lines:\n{error_details}"
            #     )

        result=super(PropertyPaymentTerm, self).write(vals)
        total_percentage = sum(line.percentage for line in self.payment_line)
        if round(total_percentage, 2) !=100:
            raise ValidationError("Total percentage of payment lines must equal 100%.")
        return result

class PropertyPaymentDiscount(models.Model):
    _name = 'property.payment.discount'
    sequence = fields.Integer(default=10)
    name = fields.Char(string="Name")
    payment_term_id = fields.Many2one('property.payment.term','payment term')
    amount_from = fields.Float(string="From(%)")
    amount_to = fields.Float(string="To(%)")
    amount = fields.Float(string="Amount(%)")
    is_from_paid = fields.Boolean(string="From paid amount")
    discount_start_from = fields.Selection(
        [
            ("1", "First Payment Term"),
            ("2", "Last Payment Term"),
            ("all", "All"),
        ],
        string="Apply From",
        required=True,
        default="2")

    @api.constrains('amount_from','amount_to','amount')
    def validate_amounts(self):
        for rec in self:
            if rec.amount_to>100 or rec.amount_to < 0:
                raise ValidationError("Amount to must be between 0 and 100")
            if rec.amount_from>100 or rec.amount_from < 0:
                raise ValidationError("Amount From must be between 0 and 100")
            if rec.amount>100 or rec.amount < 0:
                raise ValidationError("Amount must be between 0 and 100")
            if rec.amount_from > rec.amount_to:
                raise ValidationError("Amount From must be  > Amount to")



class PropertySitePaymentTermLine(models.Model):
    _name = 'property.site.payment.term.line'

    site_id = fields.Many2one('property.site', string="Site", required=True)
    payment_term_id = fields.Many2one('property.payment.term', string="Payment Term", required=True)
