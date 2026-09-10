from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging  
from odoo.exceptions import UserError
_logger = logging.getLogger(__name__)

from datetime import datetime

class ContractPerson(models.Model):
    _name = 'contract.person'
    _description = 'Contract Person Information'
    _rec_name = 'father_name'

    contract_id = fields.Many2one('contract.application', string='Contract')
    person_type = fields.Selection([
        ('buyers', 'Buyers'),
        ('legal_representatives', 'Legal Representatives'),
        ('witness', 'Witness')
    ], string='Person Type', required=True)
    
    first_name = fields.Char(string='የገዢ የስም', tracking=True) 
    father_name = fields.Char(string='የአባት ስም', tracking=True)
    gfather_name = fields.Char(string='የአያት ስም', tracking=True)
    house_number = fields.Char(string='የቤት ቁጥር')
    city = fields.Char(string='ከተማ')
    subcity = fields.Char(string='ክ/ከተማ')
    woreda = fields.Char(string='ወረዳ')
    # subcity = fields.Char(string='ዞን/ክ.ከ.ቂ.')
    phone = fields.Char(string='ስልክ ቁጥር')
    mobile = fields.Char(string='ተ/ስልክ')
    email = fields.Char(string='ኢሜል')
    pobox = fields.Char(string='ፖ/ሳ.ቁ.')
    id_number = fields.Char(string='የት/መ.ቁ.')

    @api.constrains('contract_id', 'person_type')
    def _check_legal_representative_limit(self):
        for person in self:
            if person.person_type == 'legal_representatives':
                legal_reps_count = self.env['contract.person'].search_count([
                    ('contract_id', '=', person.contract_id.id),
                    ('person_type', '=', 'legal_representatives'),
                    ('id', '!=', person.id)  # Exclude current record
                ])
                if legal_reps_count > 0:
                    raise ValidationError('Only one legal representative is allowed per contract.')


class ContractApplication(models.Model):
    _name = 'contract.application'
    _description = 'Contract Application Form'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    


    person_ids = fields.One2many(
        'contract.person',
        'contract_id',
        string='Persons'
    )


    contract_date = fields.Date(string='Contract Date',default=fields.Date.today, tracking=True)
    contract_date_char = fields.Char(string='Contract Date',help='Enter the contract date in dd/mm/yyyy format')
    # Witness Information (ሐ)
    witness_father_name = fields.Char(string='የአባት ስም', tracking=True)
    witness_gfather_name = fields.Char(string='የአያት ስም', tracking=True)
    witness_house_number = fields.Char(string='የቤት ቁጥር')
    witness_kebele = fields.Char(string='ክ/ከተማ')
    witness_woreda = fields.Char(string='ወረዳ')
    witness_email = fields.Char(string='ኢሜል')
    witness_id_number = fields.Char(string='የመ.ካርድ ቁጥር')
    witness_issue_date = fields.Date(string='የተሰጠበት ቀን')

    # Additional Information
    previous_contract_number = fields.Char(string='ግዥ የፈጸሙት አፓርትመንት ቤት ቁጥር',compute='_compute_contract_info')
    previous_contract_type = fields.Char(string='ግዥ የፈጸሙት ህንጻ አይነት',compute='_compute_contract_info')
    current_contract_number = fields.Char(string='የመረጡት አፓርትመንት ቤት ጠቅላላ',compute='_compute_contract_info')
    current_contract_block = fields.Char(string='አፓርትመንት ቤት ብሎክ',compute='_compute_contract_info')
    current_contract_floor = fields.Char(string='ጠቅላላ ፎቅ',compute='_compute_contract_info')
    payment_amount = fields.Float(string='የተመረጠዉ አፓርትመንት ቤት ጠቅላላ የመሸጫ ዋጋ በብር',compute='_compute_contract_info')
    advance_payment = fields.Float(string='ውል ሲፈራረሙ የተከፈለ ቅድመ ክፍያ በብር',compute='_compute_contract_info')
    advance_payment_date = fields.Date(string='በመቶኛ')
    
    is_previous_owner = fields.Selection([
        ('yes', 'በፊት'),
        ('no', 'በሌላ')
    ], string='ቤቱዉ ቤቱዉን ያስተዋወቁዉ')
    
    previous_owner_name = fields.Char(string='በሌላ ከሆነ በማን?')
    previous_owner_date = fields.Date(string='ዝርዝር')


    # Computed fields for easier access
    first_person_id = fields.Many2one(
        'contract.person',
        string='First Person',
        compute='_compute_persons',
        store=True
    )
    second_person_id = fields.Many2one(
        'contract.person',
        string='Second Person',
        compute='_compute_persons',
        store=True
    )

    name = fields.Char(string='Contract Number', readonly=True, default='New')
    property_sale_id = fields.Many2one('property.sale', string='Property Sale', 
                                     tracking=True, required=True, ondelete='cascade')
    

    property_description = fields.Html(string='', )
    
    _sql_constraints = [
        ('unique_property_sale', 'unique(property_sale_id)', 
         'Only one contract is allowed per property sale!')
    ]
    


    def number_to_amharic(self, num):
        amharic_numbers = {
            1: 'አንድ',
            2: 'ሁለት',
            3: 'ሶስት',
            4: 'አራት',
            5: 'አምስት',
            6: 'ስድስት',
            7: 'ሰባት',
            8: 'ስምንት',
            9: 'ዘጠኝ',
            10: 'አስር'
        }
        return amharic_numbers.get(num, "Number out of range")

    def get_property_description(self, property_id):
        has_maid_room = property_id.site_property_type_id.has_maid_room
        bedroom = property_id.bedroom
        bathroom = property_id.bathroom
        salon = "አንድ"
        salon_no = 1
        if has_maid_room:
            kitchen = "አንድ"
            kitchen_no = 1
        else:
            kitchen = "-"
            kitchen_no = 0
         
        sum = bedroom + bathroom + salon_no + kitchen_no
        sum_amharic = self.number_to_amharic(sum)
        bedroom_amharic = self.number_to_amharic(bedroom)
        bathroom_amharic = self.number_to_amharic(bathroom)
        if kitchen:
            kitchen_amharic = self.number_to_amharic(kitchen)
        else:
            kitchen_amharic = "-"
        return f"""3.4. ገዥ የገዛው የመኖሪያ አፓርታማ ቤት {bedroom_amharic} የመኝታ ክፍሎች፣ {salon} ሳሎንና መመገቢያ ክፍል በአንድ ላይ፣
{kitchen_amharic} ወጥ ቤት፣ {bathroom_amharic} መታጠቢያ ክፍሎች፣ በአጠቃላይ {sum_amharic} ክፍሎች ይኖሩታል፡፡"""

    def _compute_contract_info(self):
        for record in self:
            record.previous_contract_number = record.property_sale_id.property_id.name
            record.previous_contract_type = record.property_sale_id.property_id.site.site_type.name
            record.current_contract_number = record.name
            record.current_contract_block = record.property_sale_id.property_id.block.name
            record.current_contract_floor = record.property_sale_id.property_id.site.floor_structure
            record.payment_amount = record.property_sale_id.new_sale_price if record.property_sale_id.new_sale_price else record.property_sale_id.sale_price 
            record.advance_payment = record.property_sale_id.total_paid

    @api.constrains('contract_date_char')
    def _check_date_format(self):
        import re
        date_pattern = re.compile(r'^\d{2}/\d{2}/\d{4}$')
        for record in self:
            if record.contract_date_char and not date_pattern.match(record.contract_date_char):
                raise ValidationError("The date must be in 'dd/mm/yyyy' format.")
            
    def get_new_contract_name(self, current_year):

        contract_name = self.name
        new_contract_name = contract_name[:-4] + current_year if len(contract_name) > 4 else ""
        # _logger.info(f"new_contract_name: {new_contract_name}")
        return new_contract_name

    def gregorian_to_ethiopian(self):
        # Get the current Gregorian year
        current_gregorian_year = datetime.now().year
        
        # Calculate the Ethiopian year
        # Ethiopian year is behind by 7 or 8 years depending on whether the new year has started
        # Ethiopian new year starts on Meskerem 1, which is September 11 (or September 12 in a Gregorian leap year)
        today = datetime.now()
        ethiopian_year = current_gregorian_year - 8 if today.month < 9 or (today.month == 9 and today.day < 11) else current_gregorian_year - 7
        
        return ethiopian_year

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                property_sale_id = vals.get('property_sale_id')
                property_sale = self.env['property.sale'].browse(property_sale_id)
                # template_code = property_sale.template_id.code
                
                
                template_code = property_sale.template_id.sub_prefix or 'UNKNOWN'
                if vals.get('contract_date_char'):
                    current_year =vals.get('contract_date_char')[-4:]
                else:
                    current_year = str(datetime.now().year)
                
                # sequence = self.env['ir.sequence'].search([('id', '=', property_sale.template_id.developer_id.sequence.id)])
                # if not sequence:
                #     raise ValidationError("Please select Contact Template to create contract!")
                # ethiopian_year = self.gregorian_to_ethiopian()
                # # sequence_no = sequence.next_by_id()
                # sequence_no = sequence.number_next_actual
                # sequence.next_by_id()

                vals['name'] = "Draft Contract"

                vals['property_description'] = self.get_property_description(property_sale.property_id)
        res =super().create(vals_list)
        return res

    # def write(self, vals):
    #     for record in self:
    #         _logger.info(f"Record: {record}")
    #         _logger.info(f"Record: {record.name}")
    #         # Get the new template_code based on the updated property_sale_id
    #         # property_sale = self.env['property.sale'].browse(self.property_sale_id)
    #         # date_str = vals.get('contract_date_char')
    #         # if vals.get('contract_date_char'):
    #         #     new_template_code = self.get_new_contract_name(date_str[-4:])
    #         #     vals['name'] = new_template_code
           
        
    #     return super().write(vals)

    @api.depends('person_ids', 'person_ids.person_type')
    def _compute_persons(self):
        for record in self:
            record.first_person_id = record.person_ids.filtered(
                lambda r: r.person_type == 'first'
            )[:1]
            record.second_person_id = record.person_ids.filtered(
                lambda r: r.person_type == 'second'
            )[:1]

    # Method to create persons
    def action_add_person(self):
        self.ensure_one()
        return {
            'name': 'Add Person',
            'type': 'ir.actions.act_window',
            'res_model': 'contract.person',
            'view_mode': 'form',
            'target': 'new',
            'flags': {
                'mode': 'edit',
                'preserve_context': True,  # This helps maintain context
            },
            'context': {
                'default_contract_id': self.id,
                'parent_id': self.id,  # Track parent form
                'form_view_ref': 'contract_sections.view_contract_person_form',
            }
        }
    
    def save_contract(self):
        return {
            'type': 'ir.actions.act_window_close'
        }

    def action_add_person(self):
        self.ensure_one()
        return {
            'name': 'Add Person',
            'type': 'ir.actions.act_window',
            'res_model': 'contract.person',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_contract_id': self.id,
                'form_view_initial_mode': 'edit',
            }
        }

