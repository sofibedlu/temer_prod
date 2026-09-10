from odoo import models, fields, api
from datetime import datetime
import logging  
from odoo.exceptions import UserError
_logger = logging.getLogger(__name__)
import base64
from io import BytesIO
import base64
from PIL import Image
import re 

class ContractSection(models.Model):
    _name = 'contract.template'
    _description = 'Contract Section'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id'

    name = fields.Char(string='Template Name', required=True, tracking=True)
    developer_id = fields.Many2one('site.developer', string='Developer', tracking=True)
    sequence = fields.Many2one('ir.sequence', related='developer_id.sequence', string='Sequence', tracking=True)

    prefix = fields.Char(related='sequence.prefix', string='Prefix', tracking=True)
    sub_prefix = fields.Char( string='Sub Prefix', tracking=True)
    active = fields.Boolean(default=True)
    description = fields.Text(string='Description')
    
    # Site relation
    site_id = fields.Many2one('property.site', string='Site', tracking=True)
    # code = fields.Char('Code')
    
    # Section contents
    section_content_ids = fields.One2many(
        'contract.template.content', 
        'section_id', 
        string='Section Contents'
    )

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "The template name must be unique!")
    ]


    def copy(self, default=None):
        default = dict(default or {})
        # Ensure the new copy has no section contents initially
        default['section_content_ids'] = []
        
        # Ensure the new copy has a unique name by appending a number
        original_name = self.name
        new_name = f"{original_name} Copy"
        count = self.search_count([('name', '=like', f"{new_name}%")])
        default['name'] = f"{new_name} {count + 1}" if count else new_name

        new_record = super(ContractSection, self).copy(default)
        
        # Copy each section content
        for content in self.section_content_ids:
            content.copy({'section_id': new_record.id})
        return new_record

    @api.model
    def create(self, vals):
        # Create the contract template

        record = super(ContractSection, self).create(vals)
        # return record
        
        # Add default dynamic contents for the newly created contract template
        # record._add_default_dynamic_contents()
        
        return record

    def _add_default_dynamic_contents(self):
        """
        Add default dynamic contents (sale_info, buyer_info, payment_schedule)
        to the contract.template record.
        """
        default_dynamic_contents = [
            {
                'main_title': 'Sale Information',
                'subtitle': 'Details of the sale',
                'is_dynamic_content': True,
                'is_title_printed': False,
                'dynamic_code': "sale_info"
            },
            {
                'main_title': 'Break',
                'subtitle': '',
                'is_dynamic_content': False,
                'is_title_printed': False,
            },
            {
                'main_title': 'contract_number',
                'subtitle': '',
                'is_dynamic_content': True,
                'dynamic_code': "contract_number",
                'is_title_printed': False,
            },
            {
                
                'main_title': 'Buyer Information',
                'subtitle': 'Details of the buyer',
                'is_dynamic_content': True,
                'is_title_printed': False,
                'dynamic_code': "buyer_info"
            },
            {
                'main_title': 'Payment Detail',
                'subtitle': 'Details of the payment information',
                'is_dynamic_content': True,
                'is_title_printed': False,
                'dynamic_code': "payment_details"
            },
            {
                'main_title': 'Payment Schedule',
                'subtitle': 'Details of the payment schedule',
                'is_dynamic_content': True,
                'is_title_printed': False,
                'dynamic_code': "payment_schedule"
            }
        ]

        # Fetch existing titles to avoid duplication
        existing_titles = self.env['contract.template.content'].search([
            ('section_id', '=', self.id),
            ('main_title', 'in', [content['main_title'] for content in default_dynamic_contents])
        ]).mapped('main_title')

        # Create only those default contents that are not already present
        for content in default_dynamic_contents:
            if content['main_title'] not in existing_titles:
                self.env['contract.template.content'].create({
                    'section_id': self.id,
                    'sequence': 10,  # Adjust sequence if needed
                    **content
                })

class ContractSectionContent(models.Model):
    _name = 'contract.template.content'
    _description = 'Contract Section Content'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Sequence', default=10)
    main_title = fields.Char(string='Main Title', required=True)
    subtitle = fields.Char(string='Subtitle')
    content = fields.Html(string='Content')
    section_id = fields.Many2one('contract.template', string='Contract Section')
    is_title_printed = fields.Boolean(string='Is Title Printed', default=True)
    is_dynamic_content = fields.Boolean(string='Is Dynamic Content', default=False)
    dynamic_code = fields.Text(string='Dynamic Code')


    
    def convert_to_ethiopian(self, gregorian_date):
        # Ethiopian calendar conversion logic
        year = gregorian_date.year
        month = gregorian_date.month
        day = gregorian_date.day

        # Ethiopian new year starts on September 11/12
        if month == 9 and day > 10:
            ethiopian_year = year - 7
        elif month > 9:
            ethiopian_year = year - 7
        else:
            ethiopian_year = year - 8

        # Ethiopian months
        ethiopian_months = {
            (9, 11): (1, 1),    # Meskerem
            (10, 11): (2, 1),   # Tikimt
            (11, 10): (3, 1),   # Hidar
            (12, 10): (4, 1),   # Tahsas
            (1, 9): (5, 1),     # Tir
            (2, 8): (6, 1),     # Yekatit
            (3, 10): (7, 1),    # Megabit
            (4, 9): (8, 1),     # Miyazia
            (5, 9): (9, 1),     # Ginbot
            (6, 8): (10, 1),    # Sene
            (7, 8): (11, 1),    # Hamle
            (8, 7): (12, 1),    # Nehase
            (9, 6): (13, 1),    # Pagume
        }
          # Ethiopian month names in Amharic
        eth_month_names = {
            1: "መስከረም",
            2: "ጥቅምት",
            3: "ህዳር",
            4: "ታህሳስ",
            5: "ጥር",
            6: "የካቲት",
            7: "መጋቢት",
            8: "ሚያዚያ",
            9: "ግንቦት",
            10: "ሰኔ",
            11: "ሐምሌ",
            12: "ነሐሴ",
            13: "ጳጉሜ"
        }

        # Find Ethiopian month and day
        ethiopian_month = 1
        ethiopian_day = day
        
        for (greg_m, greg_d), (eth_m, eth_d) in ethiopian_months.items():
            if month == greg_m:
                if day >= greg_d:
                    ethiopian_month = eth_m
                    ethiopian_day = day - greg_d + 1
                else:
                    ethiopian_month = eth_m - 1
                    # Days in previous Ethiopian month
                    if ethiopian_month == 13:
                        prev_month_days = 5 + (ethiopian_year % 4 == 3)
                    else:
                        prev_month_days = 30
                    ethiopian_day = prev_month_days + day - greg_d + 1

        return {
            'day': str(ethiopian_day),
            'month': eth_month_names.get(ethiopian_month, "---"),
            'year': str(ethiopian_year)
        }

    def get_ethiopian_date(self):
        current_date = datetime.now()
        return self.convert_to_ethiopian(current_date)

    def number_to_amharic_words(self, number):
        # Dictionary for Amharic number words
        ones = {
            0: '', 1: 'አንድ', 2: 'ሁለት', 3: 'ሶስት', 4: 'አራት', 5: 'አምስት',
            6: 'ስድስት', 7: 'ሰባት', 8: 'ስምንት', 9: 'ዘጠኝ'
        }
        tens = {
            0: '',1: 'አስር', 2: 'ሃያ', 3: 'ሰላሳ', 4: 'አርባ', 5: 'ሃምሳ',
            6: 'ስድሳ', 7: 'ሰባ', 8: 'ሰማንያ', 9: 'ዘጠና'
        }
        powers = {
            0: '', 3: 'ሺህ', 6: 'ሚሊዮን', 9: 'ቢሊዮን'
        }

        if number == 0:
            return 'ዜሮ'

        def convert_group(n):
            if n == 0:
                return ''
            elif n <= 9:
                return ones[n]
            elif n == 10:
                return tens[1] 
            elif 11 <= n <= 19:
                return 'አስራ ' + ones[n-10] 
            elif n <= 99:
                return tens[n//10] + (' ' + ones[n%10] if n%10 != 0 else '')
            else:
                return ones[n//100] + ' መቶ' + (' ' + convert_group(n%100) if n%100 != 0 else '')

        result = ''
        power = 0
        while number > 0:
            group = number % 1000
            if group != 0:
                group_text = convert_group(group)
                if power > 0:
                    group_text += ' ' + powers[power]
                result = group_text + (' ' if result else '') + result
            number //= 1000
            power += 3

        return result

    def render_dynamic_content(self, property_sale):
        if not self.is_dynamic_content:
            return self.content
        
        if self.dynamic_code == 'sale_info':
            template = """
             <div style="text-align: center;">
            <b>የደንበኛው ሙሉ ስም፡ </b>${customer_name}<br/>     
            <b>ህጋዊ ወኪል ፡- </b>${agent_name}<br/>
            <b>የውል ቁጥር፡- </b>${contract_number}<br/>
            <b>የአፓርትመንቱ መለያ ቁጥር፡- </b>${property_number}<br/>
            <b>ስልክ ቁጥር፡</b>${phone_number}
            </div>
            """
            
            agent_name = self.env['contract.application'].search([('id', '=', property_sale.contract_id.id)], limit=1).person_ids.filtered(lambda r: r.person_type == 'legal_representatives').first_name
            # customer_name = self.env['contract.application'].search([('id', '=', property_sale.contract_id.id)], limit=1).person_ids[0].filtered(lambda r: r.person_type == 'buyers').first_name + ' ' + self.env['contract.application'].search([('id', '=', property_sale.contract_id.id)], limit=1).person_ids.filtered(lambda r: r.person_type == 'buyers').father_name
            # Fetch the contract application once and reuse it
            contract_application = self.env['contract.application'].search([('id', '=', property_sale.contract_id.id)], limit=1)

            # Get the agent's name
            agent = contract_application.person_ids.filtered(lambda r: r.person_type == 'legal_representatives')
            agent_name = f"{agent[0].first_name} {agent[0].father_name}" if agent else '--------------------'
            # _logger.info(f"Agent name: {agent_name}")
            # Get the customer's name by combining first and father's name
            buyers = contract_application.person_ids.filtered(lambda r: r.person_type == 'buyers')
            buyers_name = ''
            if buyers:
                if len(buyers) == 1:
                    buyers_name = f"{buyers[0].first_name} {buyers[0].father_name}"
                else:
                    buyers_name = " እና ".join(
                        [f"{buyer.first_name} {buyer.father_name}" for buyer in buyers]
                    )
            else:
                buyers_name = ""



            values={
                'customer_name': buyers_name or '------------------',
                'agent_name': agent_name or '--------------------',
                'contract_number': property_sale.contract_id.name or '--------------------',
                'property_number': property_sale.property_id.name or '-------------',
                'phone_number': buyers[0].phone or '---------------'
            }
            
            try:
                from string import Template
                template = Template(template)
                return template.safe_substitute(values)
            except Exception as e:
                return f"Error rendering template: {str(e)}"
        
            

        elif self.dynamic_code == 'buyer_info':
            # Get contract application data first
            contract = property_sale.contract_id
            buyers = contract.person_ids.filtered(lambda r: r.person_type == 'buyers')
            buyer1 = buyers[0] if buyers else False
            buyer2 = buyers[1] if len(buyers) > 1 else False
            
            # Get legal representative
            legal_rep = contract.person_ids.filtered(lambda r: r.person_type == 'legal_representatives')
            agent_name = legal_rep[0].first_name if legal_rep else False
            agent_second_name = legal_rep[0].father_name if legal_rep else ""
            agent_last_name = legal_rep[0].gfather_name if legal_rep else ""
            agent_name = f"{agent_name} {agent_second_name} {agent_last_name}" if agent_name else ''
            # Base template
            base_template = """
            <div style="text-align: left;">
                <b>በ1ኛ ገዢ፡- ሙሉ ስም፡ ${buyer1_name}</b><br/>
                የገዥ አድራሻ፡- ${buyer1_city} ከተማ፣ ${buyer1_subcity} ክ/ከተማ፣ ወረዳ ${buyer1_woreda}፣ ቤት ቁ ${buyer1_house_no} ስልክ ቁ ${buyer1_phone}<br/>
            """

            # Add second buyer if exists
            if len(buyers) > 1:
                base_template += """
                <b>በ2ኛ ገዢ፡- ሙሉ ስም፡ ${buyer2_name}</b><br/>
                የገዥ አድራሻ፡- ${buyer2_city} ከተማ፣ ${buyer2_subcity} ክ/ከተማ፣ ወረዳ ${buyer2_woreda}፣ ቤት ቁ ${buyer2_house_no}<br/>
                ስልክ ቁ ${buyer2_phone}<br/>
                """

            # Add agent only if legal representative exists
            if agent_name:
                base_template += """
                <b>የወኪል ስም ፡ ${agent_name}</b>
                """
            first_name = buyer1.first_name if buyer1 else '-------------------'
            father_name = buyer1.father_name if buyer1 else '-------------------'
            gfather_name = buyer1.gfather_name if buyer1 else '-------------------'

            buyer2_first_name = buyer2.first_name if buyer2 else '-------------------'
            buyer2_father_name = buyer2.father_name if buyer2 else '-------------------'
            buyer2_gfather_name = buyer2.gfather_name if buyer2 else '-------------------'
            values = {
                # First Buyer
                'buyer1_name': first_name + ' ' + father_name + ' ' + gfather_name if buyer1 else '-------------------',
                'buyer1_city': buyer1.city or '-------------',
                'buyer1_subcity': buyer1.subcity or '---------',
                'buyer1_woreda': buyer1.woreda or '--------',
                'buyer1_house_no': buyer1.house_number or '--------',
                'buyer1_phone': buyer1.phone or '---------',
                
                # Second Buyer
               
                'buyer2_name': buyer2_first_name + ' ' + buyer2_father_name + ' ' + buyer2_gfather_name if buyer2 else '-------------------',
                'buyer2_city': buyer2.city if buyer2 and buyer2.city else '-------------',
                'buyer2_subcity': buyer2.subcity if buyer2 and buyer2.subcity else '---------',
                'buyer2_woreda': buyer2.woreda if buyer2 and buyer2.woreda else '--------',
                'buyer2_house_no': buyer2.house_number if buyer2 and buyer2.house_number else '--------',
                'buyer2_phone': buyer2.phone if buyer2 and buyer2.phone else '--------------',
                
                # Agent
                'agent_name': agent_name if agent_name else '',
            }
            try:
                from string import Template
                template = Template(base_template)
                return template.safe_substitute(values)
            except Exception as e:
                return f"Error rendering template: {str(e)}"
            
        elif self.dynamic_code == 'contract_date':
            contract = property_sale.contract_id
            # _logger.info(f"Contract date: {contract.contract_date_char}")
            # contract_date = contract.contract_date_char
            contract_date = datetime.strptime(contract.contract_date_char, '%d/%m/%Y')

            # Add date
            base_template = """
                ዛሬ ${day} ቀን ${month} ወር ${year} ዓም በኢትዮጵያ ፍትሐብሔር ህግ ቁጥር 2876 መሠረት በአዲስ አበባ ከተማ ተፈርሟል፡፡<br/>
            </div>
            """
            
            # Get Ethiopian date
            # eth_date = self.get_ethiopian_date()
            eth_date = contract_date
            # _logger.info(f"Ethiopian date: {eth_date}")
            
            values = {
                # First Buyer
             
                'day': eth_date.day,    
                'month': eth_date.month,
                'year': eth_date.year,
            }
            
            try:
                from string import Template
                template = Template(base_template)
                return template.safe_substitute(values)
            except Exception as e:
                return f"Error rendering template: {str(e)}"
            
    
        elif self.dynamic_code == 'contract_date_signature':

            contract = property_sale.contract_id
            # _logger.info(f"Contract date: {contract.contract_date_char}")
            # contract_date = contract.contract_date_char
            contract_date = datetime.strptime(contract.contract_date_char, '%d/%m/%Y')

            contract_application = self.env['contract.application'].search([('id', '=', property_sale.contract_id.id)], limit=1)

            # Get the customer's name by combining first and father's name
            buyer = contract_application.person_ids.filtered(lambda r: r.person_type == 'buyers')
            customer_name = f"{buyer[0].first_name} {buyer[0].father_name}" if buyer else '----------'
            # Add date
            base_template = """
                15.2. ይህ ውል ዛሬ ${day} ቀን ${month} ወር ${year} ዓም የሚከተሉት ምስክሮች ባሉበት በሻጭ ቡራት ሪልእስቴት አክሲዮን ማህበር እና በገዢ <b>${customer_name}</b> መካከል በአዲስ አበባ ከተማ ተፈርሟል፡፡ ይህ ስምምነት በሁለት ኮፒ ተዘጋጅቶ አንድ ኮፒ ለገዢ፣ አንድ ኮፒ ለሻጭ እንዲደርስ ተደርጓል፡፡<br/>
            </div>
            """
            
            # Get Ethiopian date
            # eth_date = self.get_ethiopian_date()
            eth_date = contract_date
            # _logger.info(f"Ethiopian date: {eth_date}")
            
            values = {
                # First Buyer
             
                'day': eth_date.day,    
                'month': eth_date.month,
                'year': eth_date.year,
                'customer_name': customer_name,
            }
            
            try:
                from string import Template
                template = Template(base_template)
                return template.safe_substitute(values)
            except Exception as e:
                return f"Error rendering template: {str(e)}"
            
        elif self.dynamic_code == 'contract_witness':
            base_template = """
                እኛ ስማችን ከዚህ በታች የተጠቀሰው እማኞች ተዋዋይ ወገኖች ከዚህ በላይ በተጻፈው የውል ቃል
            መሠረት ተስማምተው ውሉን ሲፈጽሙ ያየንና የሰማን መሆናችንን በፊርማችን እናረጋግጣለን፡፡
            <div style="text-align: center;">
               <table style="width: 100%;">
              
           <thead>
        <tr >
            <th style='width: 30%;'> ስም፡ </th>
            <th style='width: 30%;'>ፊርማ</th>
            <th style='width: 30%;'>አድራሻ</th>
            </tr>
            </thead>
            """
            
            agent_names = self.env['contract.person'].search([('contract_id', '=', property_sale.contract_id.id)])
            # _logger.info(f"Agent names***********: {agent_names}")
            for agent in agent_names:
                # _logger.info(f"Agent***********: {agent}")
                # _logger.info(f"Agent type***********: {agent.person_type}")
                address = f"<b>ከተማ:</b> {agent.city if agent.city else ''}  <b>ክ/ከተማ:</b> {agent.subcity if agent.subcity else ''}  <b>ወረዳ:</b> {agent.woreda if agent.woreda else ''}  <b>ቤት ቁ:</b> {agent.house_number if agent.house_number else ''}  <b>ስልክ ቁ:</b> {agent.phone if agent.phone else ''}<br/>"
                name = f"{agent.first_name if agent.first_name else ''} {agent.father_name if agent.father_name else ''} {agent.gfather_name if agent.gfather_name else ''}     "
                if agent.person_type == 'witness':
                    agent_template = f"""
                        <tr >
                        <td style='padding: 20px;'>{name}</td>
                        <td style='padding: 20px;'>             </td>
                        <td style='padding: 20px;'>{address}</td>
                        </tr>
                    """
                    
                    
                    base_template += agent_template
            
            base_template += "</table></div>"
            try:
                from string import Template
                template = Template(base_template)
                return template.substitute()  # No values dictionary needed as we're using f-strings
            except Exception as e:
                return f"Error rendering template: {str(e)}"
            
            

        elif self.dynamic_code == 'payment_schedule':
            # Get payment terms and total price
            property = property_sale.property_id
            payment_term = property_sale.payment_installment_line_ids
            total_price = property_sale.new_sale_price if property_sale.new_sale_price else property_sale.sale_price  # Assuming this is the total price field

            if not payment_term:
                return "No payment terms defined"

            # Create table header
            template = """
            <div style="text-align: center;">
                <table class="table table-bordered" style="width: 100%; margin: auto;">
                    <thead>
                        <tr>
                            <th style="text-align: center;">ተ.ቁ</th>
                            <th style="text-align: center;">ከጠቅላላው የቤት ዋጋ ክፍያ በመቶኛ</th>
                            <th style="text-align: center;">የክፍያ መጠን</th>
                            <th style="text-align: center;">የክፍያ ጊዜ</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${payment_rows}
                    </tbody>
                </table>
            </div>
            """
            sequence = 1
            # Generate payment rows
            payment_rows = ""
            for line in payment_term.sorted(lambda l: l.sequence):
                if sequence > 1:
                    amount = line.expected_amount
                    payment_rows += f"""
                        <tr>
                            <td style="text-align: center;">{sequence}ኛ ክፍያ</td>
                            <td style="text-align: center;">ከቤቱ ጠቅላላ የመሸጫ ዋጋ ላይ {line.expected:,.2f}%</td>
                            <td style="text-align: center;">{amount:,.2f}ብር</td>
                            <td style="text-align: center;">{line.payment_term_id.name}</td>
                        </tr>
                    """
                sequence += 1

            # Replace the payment_rows placeholder
            template = template.replace("${payment_rows}", payment_rows)
            return template
        
        elif self.dynamic_code =='property_info':
            property = property_sale.property_id
            base_template = f"""
            3.3. ገዥው የገዛው የመኖሪያ አፓርታማ ቤት {property.floor_id.name} ወለል ላይ የሚገኘውና የቤት ቁጥሩ <b>{property.name}</b> የሆነው
ነው፡
            """
            return base_template

            
        elif self.dynamic_code == 'property_property_description':
            # property_description = "3.4. "+contract.property_description.strip()
            # _logger.info(f"Property description: {property_description}")
            contract = property_sale.contract_id
            # Insert "3.4. " directly at the start of the HTML paragraph in the property description
            property_description = contract.property_description
    
            # Use regex to insert "3.4. " right after the opening <p> tag, accounting for possible attributes and whitespace
            # property_description = re.sub(r'(<p\s*[^>]*>)', r'\1 3.4. ', property_description, 1)
            # _logger.info(f"Property description: {property_description}")

            # clean_property_description = re.sub(r'<[^>]+>', '', property_description)
            
    
            # property_description = re.sub(r'(<p\s*[^>]*>)', r'\13.4. ', property_description, 1)
    
            # _logger.info(f"Property clean_property_description: {clean_property_description}")


            return property_description


        elif self.dynamic_code =='property_area':
            property = property_sale.property_id
            gross_area = property.gross_area
            net_area = property.net_area
            base_template = f"""
            3.5. የአፓርታማ ቤቱ ስፋት ከዚህ ውል ጋር በተያያዘው ንድፍ መሠረት የጋራ መገልገያ ድርሻን ሳይጨምር {net_area}
            ካሬ ሜትር ነው፡፡ የቤቱ ጠቅላላ ስፋት {gross_area} ካ.ሜ. ነው፡፡
            """
            values = {
                'net_area': net_area,
                'gross_area': gross_area,
            }
            try:
                from string import Template
                template = Template(base_template)
                return template.safe_substitute(values)
            except Exception as e:
                return f"Error rendering template: {str(e)}"
        elif self.dynamic_code == 'site_images':
            try:
                # Retrieve the site ID and related certificates
                # site_id = property_sale.property_id.site
                # _logger.info(f"Site ID***********: {site_id}")
                
                # site = site_id and site_id.id and self.env['property.site'].search([('id', '=', site_id.id)], limit=1)
                
                # if not site:
                #     _logger.error("No site found for the given property.")
                #     return "Error: No site associated with the property."
                
                # leasehold_certificate = site.leasehold_certificate
                # commercial_certificate = site.commercial_certificate
                # taxpayer_certificate = site.taxpayer_certificate

                # # Log certificate presence
                # _logger.info(f"Leasehold certificate present: {'Yes' if leasehold_certificate else 'No'}")
                # _logger.info(f"Commercial certificate present: {'Yes' if commercial_certificate else 'No'}")
                # _logger.info(f"Taxpayer certificate present: {'Yes' if taxpayer_certificate else 'No'}")

                # # Convert binary data to base64 and construct data URIs
                # leasehold_certificate_img = (
                #     f"data:image/png;base64,{base64.b64encode(leasehold_certificate).decode()}"
                #     if leasehold_certificate else ""
                # )
                # commercial_certificate_img = (
                #     f"data:image/png;base64,{base64.b64encode(commercial_certificate).decode()}"
                #     if commercial_certificate else ""
                # )
                # taxpayer_certificate_img = (
                #     f"data:image/png;base64,{base64.b64encode(taxpayer_certificate).decode()}"
                #     if taxpayer_certificate else ""
                # )

                # # Debugging: Save images to files for verification
                # with open('/tmp/leasehold_certificate.png', 'wb') as f:
                #     f.write(leasehold_certificate or b'')
                # with open('/tmp/commercial_certificate.png', 'wb') as f:
                #     f.write(commercial_certificate or b'')
                # with open('/tmp/taxpayer_certificate.png', 'wb') as f:
                #     f.write(taxpayer_certificate or b'')

                # # Debugging: Log the start of the base64 data
                # _logger.info(f"Leasehold Certificate Data URI: {leasehold_certificate_img[:30]}...")
                # _logger.info(f"Commercial Certificate Data URI: {commercial_certificate_img[:30]}...")
                # _logger.info(f"Taxpayer Certificate Data URI: {taxpayer_certificate_img[:30]}...")


                # leasehold_certificate = site.leasehold_certificate
               

                # Construct the HTML template
                # template_string = """
                # <div>
                #     <h3>Property Certificates</h3>
                #     <div>
                #         <h4>Leasehold Certificate</h4>
                #         <img src="${leasehold_certificate}" alt="Leasehold Certificate" style="width:500px;height:auto;">
                #     </div>
                #     <div>
                #         <h4>Commercial Certificate</h4>
                #         <img src="${commercial_certificate}" alt="Commercial Certificate" style="width:500px;height:auto;">
                #     </div>
                #     <div>
                #         <h4>Taxpayer Certificate</h4>
                #         <img src="${taxpayer_certificate}" alt="Taxpayer Certificate" style="width:500px;height:auto;">
                #     </div>
                # </div>
                # """

               
                # from string import Template
                # # Substitute data URIs into the template
                # template = Template(template_string)
                # rendered_html = template.substitute(
                #     leasehold_certificate=leasehold_certificate_img,
                #     commercial_certificate=commercial_certificate_img,
                #     taxpayer_certificate=taxpayer_certificate_img
                # )

                # _logger.info("Template rendered successfully.")
                # return rendered_html


                site = property_sale.property_id.site
                if not site:
                    return "<div>Error: No site associated with the property.</div>"

                leasehold_certificate = site.leasehold_certificate

                # Validate and re-encode the image
                if leasehold_certificate:
                    try:
                        image = Image.open(BytesIO(leasehold_certificate))
                        image.verify()  # Check if it's a valid image

                        # Re-encode the image
                        buffer = BytesIO()
                        image.save(buffer, format="PNG")
                        leasehold_certificate = buffer.getvalue()
                    except Exception as e:
                        _logger.error(f"Leasehold Certificate is not a valid image: {str(e)}")
                        return "<div>Leasehold Certificate is invalid or corrupted.</div>"
                else:
                    _logger.warning("Leasehold Certificate is empty.")
                    return "<div>Leasehold Certificate is not available.</div>"

                # Save as an attachment
                attachment = self.env["ir.attachment"].create({
                    "name": "Leasehold Certificate",
                    "type": "binary",
                    "datas": base64.b64encode(leasehold_certificate),
                    "res_model": "property.site",
                    "res_id": site.id,
                    "mimetype": "image/png",
                })
                leasehold_certificate_url = f"/web/content/{attachment.id}"

                # Render the image in the HTML
                template = f"""
                <div>
                    <h4>Leasehold Certificate</h4>
                    <img src="{leasehold_certificate_url}" alt="Leasehold Certificate" style="width:500px;height:auto;">
                </div>
                """
                return template
            except Exception as e:
                _logger.error(f"Error processing images: {str(e)}", exc_info=True)
                return f"Error rendering template: {str(e)}"
            
        
        elif self.dynamic_code == 'payment_details':
            property = property_sale.property_id
            payment_term = property.payment_structure_id
            total_price = property_sale.new_sale_price if property_sale.new_sale_price else property_sale.sale_price
            price_per_sqm = property.price
            area = property.gross_area
            
            # Get first payment percentage and amount
            first_payment_line = property_sale.payment_installment_line_ids.sorted(lambda l: l.sequence)[0] # payment_term.payment_line.sorted(lambda l: l.sequence)[0]
            first_payment_percent = first_payment_line.expected if first_payment_line.remaining == 0 else first_payment_line.paid_amount * 100 / total_price
            first_payment_amount = first_payment_line.paid_amount

            template = """
                <div>
                    5.1. በገዥ የሚከፈለው በካሬ ${price_per_sqm_number} <b>/${price_per_sqm_amharic}</b> ሲሆን ገዢ የመረጡት ቤት ካሬው ${area} 
                    በመሆኑ ጠቅላላ የቤቱ ዋጋ ተ.እ.ታ.ን ጨምሮ በኢትዮጲያ ብር<u> ${total_price_number} <b>/${total_price_amharic}</b> </u> መሆኑን ተስማምተናል፡፡
                    በቀሪ ክፍያው ላይ ምንም አይነት የዋጋ እና የዶላር ግሽበት አይመለከተውም።<br/>
                    5.2. ገዢ ይህ ዉል ሲፈረም የመጀመሪያ ክፍያ ከመኖርያ ቤቱ ጠቅላላ የመሸጫ ዋጋ ላይ የሚሰላ ${first_payment_percent}% (${first_payment_percent_amharic} በመቶ) በኢትዮጵያ ብር ${first_payment_amount}<b>/${first_payment_amharic}</b> ቅድሚያ ክፍያ ከፍለዋል፡፡<br/>
                    5.3. በአንቀፅ 5.1 ላይ የተገለፅው የመኖርያ ቤቱ ዋጋ ቀሪ ክፍያዎች ከዚህ በታች በተመለከተው ሰንጠረዥ መሰረት ነው።<br/>
                </div>
            """

            values = {
                'price_per_sqm_amharic': self.number_to_amharic_words(int(price_per_sqm)),
                'price_per_sqm_number': f"{price_per_sqm:,.2f}",
                'area': f"{area:,.2f}",
                'total_price_amharic': self.number_to_amharic_words(int(total_price)),
                'total_price_number': f"{total_price:,.2f}",
                'first_payment_percent': f"{first_payment_percent:,.2f}",
                'first_payment_percent_amharic': self.number_to_amharic_words(int(first_payment_percent)),
                'first_payment_amount': f"{first_payment_amount:,.2f}",
                'first_payment_amharic': self.number_to_amharic_words(int(first_payment_amount))
            }

            try:
                from string import Template
                template = Template(template)
                return template.safe_substitute(values)
            except Exception as e:
                return f"Error rendering template: {str(e)}"
        elif self.dynamic_code == 'contract_number':
            template = """ <div style='float: right;'>
                    የውል ቁጥር ፡-  ${contract_number}
                    </div>
                    <br/>
                    <br/>
                """
            values={
                
                'contract_number': property_sale.contract_id.name or '--------------------',
               
            }
            
            try:
                from string import Template
                template = Template(template)
                return template.safe_substitute(values)
            except Exception as e:
                return f"Error rendering template: {str(e)}"
        return self.content