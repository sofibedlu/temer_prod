from odoo import models, fields, api
import logging  
from odoo.exceptions import UserError,ValidationError
from datetime import datetime
_logger = logging.getLogger(__name__)


class PropertyReservation(models.Model):
    _inherit = 'property.reservation'

    is_special = fields.Boolean('is Special ', compute='check_is_special_reservation',store=True)

    reservation_type_id = fields.Many2one('property.reservation.configuration',
                                          string="Reservation Type",tracking = True,  required=True)
    property_id = fields.Many2one('property.property',
                                  domain=[('state', 'in', ['available'])],
                                  string="Property",  required=True)
    reservation_type_id = fields.Many2one('property.reservation.configuration',
                                          string="Reservation Type",tracking = True,  required=True)
    payment_line_ids=fields.One2many('property.reservation.payment' , inverse_name='reservation_id')
    site_id = fields.Many2one(
        'property.site',
        related='property_id.site',
        store=True,
        string="Site"
    )
    
    @api.depends('reservation_type_id')
    def check_is_special_reservation(self):
        for rec in self:
            if rec.reservation_type_id and rec.reservation_type_id.reservation_type=='special':
                rec.is_special=True
            else:
                rec.is_special=False

    
 

class PropertyProperty(models.Model):
    _inherit = 'property.property'

    site = fields.Many2one('property.site',
                           required=True,
                           domain=[('state', 'not in', ['archived'])],
                           string="Site")
    payment_structure_id = fields.Many2one('property.payment.term', string="Payment Structure")
    site_payment_structure_id = fields.Many2one('property.payment.type',
                                                domain="[('site_id', '=', site),('property_type','=',property_type)]",
                                                string="Payment Structure")
    price = fields.Float('Price(m2)',compute="compute_unit_price",store=True)


    property_type_id = fields.Many2one('property.type',required=True, help="Property Type")

    gross_area = fields.Float('Gross Area(m2)', compute='compute_property_details',store=True)
    net_area = fields.Float('Net Area(m2)', compute='compute_property_details',store=True)
    bedroom = fields.Integer(
        string="Bedrooms", help="Number of bedrooms in the property", compute='compute_property_details',store=True
    )
    bathroom = fields.Integer(
        string="Bathrooms", help="Number of bathrooms in the property",compute='compute_property_details',store=True
    )

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


    @api.depends('property_type_id')
    def compute_property_details(self):
        for rec in self:
            rec.bedroom = rec.property_type_id.number_be_room
            rec.bathroom = rec.property_type_id.number_bath_room
            rec.net_area = rec.property_type_id.net_area
            rec.gross_area = rec.property_type_id.gross_area

class PropertySale(models.Model):
    _inherit = 'property.sale'

    contract_id = fields.One2many('contract.application', 'property_sale_id', string='Contract')
    
    contract_number = fields.Char(
        related='contract_id.name', store=True, precompute=True,
        index=True,
        copy=False,
    )
    template_id = fields.Many2one('contract.template', string='Contract Template')
    
    def gregorian_to_ethiopian(self):
        # Get the current Gregorian year
        current_gregorian_year = datetime.now().year
        
        # Calculate the Ethiopian year
        # Ethiopian year is behind by 7 or 8 years depending on whether the new year has started
        # Ethiopian new year starts on Meskerem 1, which is September 11 (or September 12 in a Gregorian leap year)
        today = datetime.now()
        ethiopian_year = current_gregorian_year - 8 if today.month < 9 or (today.month == 9 and today.day < 11) else current_gregorian_year - 7
        
        return ethiopian_year
    
    def action_confirm(self):
        res = super().action_confirm()
        #sequence = self.env['ir.sequence'].search([('id', '=', self.template_id.developer_id.sequence.id)])

        if getattr(self, 'skip_contract_generation', False):
            return res

        # Check if the site-based numbering module provides the specific sequence to use
        sequence = False
        if hasattr(self, '_get_sequence_for_sale'):
            sequence = self._get_sequence_for_sale(self, self.template_id)
            
        # Fallback to the developer's default sequence if no site sequence applies
        if not sequence:
            sequence = self.env['ir.sequence'].search([('id', '=', self.template_id.developer_id.sequence.id)])
            
        if not sequence:
            raise ValidationError("Please select Contact Template to create contract!")
        ethiopian_year = self.gregorian_to_ethiopian()
        # sequence_no = sequence.next_by_id()
        sequence_no = sequence.number_next_actual
        sequence.next_by_id()
        template_code = self.template_id.sub_prefix or 'UNKNOWN'
        contract_application = self.env['contract.application'].search([('property_sale_id', '=', self.id)])
        contract_year = contract_application.contract_date_char[-4:]

        contruct_name= f"{sequence.prefix}/{template_code}/{sequence_no}/{contract_year}"

        contract_application.write({
            'name': contruct_name,
        })

    def action_open_contract_form(self):
        self.ensure_one()
        if self.contract_id:
            raise UserError('A contract already exists for this property sale!')
            
        new_contract = self.env['contract.application'].create({
            'property_sale_id': self.id,
        })
        view_id = self.env.ref('contract_sections.view_contract_application_form1').id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Contract Application',
            'view_mode': 'form',
            'res_model': 'contract.application',
            'target': 'current',
            'res_id': new_contract.id,
            'views': [[view_id, 'form']],
        }
    def action_view_contract(self):
        self.ensure_one()
        if self.contract_id:
            # If contract exists, open it
            return {
                'name': 'Contract',
                'type': 'ir.actions.act_window',
                'res_model': 'contract.application',
                'res_id': self.contract_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            # If no contract exists, create new one
            return self.action_open_contract_form()

    def action_print_contract(self):

        # contract.person checck if there is at least one person
        if not self.contract_id.person_ids:
            raise UserError('Please Add Buyer first!')

        self.ensure_one()
        if not self.contract_id:
            raise UserError('Please create a contract first!')
            
        # Get matching sections based on state
        sections = self.env['contract.template'].search([('id','=',self.template_id.id)], order='id')
        
        if not sections:
            raise UserError('No contract sections found for current state!')
            
        section_data = []
        for section in sections:
            
            # section_contents =  section.section_content_ids.sorted(key=lambda r: r.sequence).mapped(lambda c: {
            #         'content': c.content,
            #         'sequence': c.sequence,
            #         'is_title_printed': c.is_title_printed,
            #         'main_title': c.main_title,
            #         'subtitle': c.subtitle,
            #         'dynamic_code': c.dynamic_code,
            #         'is_dynamic_content': c.is_dynamic_content,
            #     })

    
            section_data = []
            for section in sections:
                contract_date = datetime.strptime(self.contract_id.contract_date_char, '%d/%m/%Y')
                contract_date = f"{contract_date.day} ቀን {contract_date.month} ወር {contract_date.year} ዓም"
                section_contents = []
                for content in section.section_content_ids.sorted(lambda r: r.sequence):
                    # Pass the content record instead of creating a dictionary
                    if content.is_dynamic_content:
                        rendered_content = content.render_dynamic_content(self)
                    else:
                        static_content = content.content
                        # _logger.info(f"static_content==============: {static_content}")
                        if static_content:
                            rendered_content = static_content.replace('{today}', str(contract_date))
                        else:
                            rendered_content = static_content

                    content_data = {
                        'sequence': content.sequence,
                        'is_title_printed': content.is_title_printed,
                        'main_title': content.main_title,
                        'subtitle': content.subtitle,
                        'is_dynamic_content': content.is_dynamic_content,
                        'dynamic_code': content.dynamic_code,
                        'content': rendered_content,
                    }
                        
                    section_contents.append(content_data)
            
                section_data.append({
                    'name': section.name,
                    'contents': section_contents,
                    
                    
                })
            
        data = {
            'docs': self,
            'sections': section_data
        }
        # _logger.info(f"self.id: {self.id}")

        
        return self.env.ref("contract_sections.action_report_contract").report_action(
            [], data = {
               
            'docs': self,
            'property': self.id,
            'sections': section_data
        }
        )