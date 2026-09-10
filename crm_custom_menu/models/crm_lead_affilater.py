from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, AccessError
import phonenumbers
import logging
import requests
import re

_logger = logging.getLogger(__name__)

class CrmAffilaterPhone(models.Model):
    _name = 'crm.affilater.phone'
    _description = 'Referral Phone'
    name = fields.Char(string="Phone Number", required=True)

class CrmLeadAffilater(models.Model):
    _name = 'crm.affilater'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Referral CRM Lead'
    _rec_name = 'name'

    name = fields.Char(string='Name', compute="compute_lead_name", store=True)
    customer_name = fields.Char(string='Customer', tracking=True, required=True)
    site_ids = fields.Many2many('property.site', string="Site", tracking=True, default=lambda self: self.env['property.site'].search([], limit=1).ids)
    country_id = fields.Many2one('res.country', string="Country", 
                                 default=lambda self: self.env.ref('base.et').id)
    phone_no = fields.Char(string="Phone No", tracking=True)
    nominated_supervisor_id = fields.Many2one('property.sales.supervisor', string="Nominated Supervisor", readonly=True, copy=False)
    nominated_wing_id = fields.Many2one('property.wing.config', string="Nominated Wing", readonly=True, copy=False)
    assigned_supervisor_id = fields.Many2one('property.sales.supervisor', string="Assigned Supervisor", readonly=True, copy=False)
    assigned_wing_id = fields.Many2one('property.wing.config', string="Assigned Wing", readonly=True, copy=False)
    nominated_salesperson_id = fields.Many2one('res.users', string="Nominated Person", readonly=True, copy=False)
    assigned_salesperson_id = fields.Many2one('res.users', string="Assigned Person", readonly=True, copy=False)
    state_crm = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
    ], string='Status', default='draft', tracking=True)
    phone_number = fields.Char(string="Phone Number")
    full_phone = fields.Many2many('crm.affilater.phone', string="All Phone no", help="List of all phone numbers.")
    secondary_phone = fields.Char(string="Secondary Phone", invisible=True)
    phone_prefix = fields.Char(string="Phone Prefix", compute="_compute_phone_prefix")
    user_id = fields.Many2one('res.users', string="Salesperson", default=lambda self: self.env.user, readonly=True)
    full_phone_ids = fields.Many2many('crm.affilater.phone', store=False, string="Excluded Phone Numbers")
    source_id = fields.Many2one('utm.source', string="Lead Source", default=lambda self: self._default_source_id(), help="Indicates the source of the lead (e.g., Website, Campaign, Referral).")
    is_affilater_user = fields.Boolean(string="Is Referral User", compute="_compute_is_affilater_user", store=False)
    sales_person = fields.Many2one('res.users', string="Responsible Person", default=lambda self: self.env.user, readonly=True)
    phone_number_message = fields.Char(string="Phone Number Message", readonly=True, help="Message displayed if the phone number is already registered.")
    crm_stage_id = fields.Many2one('crm.stage', string="CRM Stage", help="The stage to assign to the lead when it is created.")
    affilater_name = fields.Char(string="Referral Name", store=True)
    email_address = fields.Char(string="Email Address", store=True)

    # New fields for duplicate handling and SMS features
    resolved_supervisor_id = fields.Many2one('property.sales.supervisor', string="Resolved Supervisor", compute="_compute_resolved_supervisor", store=True)
    existing_salesperson_id = fields.Many2one('res.users', string="Existing Salesperson", readonly=True)
    existing_supervisor_id = fields.Many2one('property.sales.supervisor', string="Existing Supervisor", readonly=True)
    existing_temer_lead_id = fields.Many2one(
        'temer.lead', 
        string="Existing Temer Lead", 
        readonly=True,
        help="Reference to the existing temer.lead with this phone number"
    )
    
    existing_lead_state = fields.Selection(
        related='existing_temer_lead_id.state',
        string="Existing Lead Status",
        readonly=True
    )
    
    existing_lead_create_date = fields.Datetime(
        related='existing_temer_lead_id.create_date',
        string="Existing Lead Created On",
        readonly=True
    )
    
    existing_customer_and_phone = fields.Boolean(string="Is Exist ?")
    
    # Add duplicate phone boolean field
    is_duplicate_phone = fields.Boolean(
        string="Duplicate Phone", 
        default=False,
        help="Indicates if the phone number already exists in the system"
    )

    # DYNAMIC PHONE HANDLING METHODS
    def _normalize_phone_number(self, phone_number, country_code='ET'):
        """
        Normalize phone number to E164 format based on country code
        Returns: normalized phone in E164 format or original if parsing fails
        """
        if not phone_number:
            return phone_number
            
        try:
            # Parse with country code
            parsed = phonenumbers.parse(phone_number, country_code)
            
            # Validate the number
            if phonenumbers.is_valid_number(parsed):
                # Format to E164 international format (e.g., +251911234567, +15551234567)
                normalized = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
                return normalized
            else:
                _logger.warning(f"Invalid phone number {phone_number} for country {country_code}")
                return phone_number
                
        except phonenumbers.NumberParseException as e:
            _logger.warning(f"Failed to parse phone number {phone_number} for country {country_code}: {e}")
            return phone_number
        except Exception as e:
            _logger.error(f"Unexpected error normalizing phone {phone_number}: {e}")
            return phone_number

    def _generate_phone_variants(self, phone_number, country_code='ET'):
        """
        Generate common phone number variants for duplicate checking
        Handles any country code dynamically
        """
        variants = set()
        
        if not phone_number:
            return list(variants)
        
        # Always include the original
        variants.add(phone_number)
        
        try:
            # Get country phone code for the selected country
            country = self.env['res.country'].search([('code', '=', country_code)], limit=1)
            if country and country.phone_code:
                country_phone_code = str(country.phone_code)
                
                # Parse the phone number to extract national number
                parsed = phonenumbers.parse(phone_number, country_code)
                national_number = str(parsed.national_number)
                
                # Generate variants based on country
                if country_code.upper() == 'ET':
                    # Ethiopia-specific variants
                    variants.add(national_number)  # 911234567
                    variants.add('0' + national_number)  # 0911234567
                    variants.add('251' + national_number)  # 251911234567
                    variants.add('+251' + national_number)  # +251911234567
                    variants.add('009251' + national_number)  # 009251911234567
                else:
                    # Generic international variants for other countries
                    variants.add(national_number)  # National format
                    variants.add('0' + national_number)  # With leading zero
                    variants.add(country_phone_code + national_number)  # Without +
                    variants.add('+' + country_phone_code + national_number)  # With +
                    variants.add('00' + country_phone_code + national_number)  # With 00
                    
            else:
                # Fallback: just use digit extraction
                digits = ''.join(filter(str.isdigit, phone_number))
                if digits:
                    variants.add(digits)
                    
        except Exception as e:
            _logger.warning(f"Could not generate phone variants for {phone_number}: {e}")
            # Fallback: extract digits only
            digits = ''.join(filter(str.isdigit, phone_number))
            if digits:
                variants.add(digits)
        
        # Remove any empty variants and return as list
        return [v for v in variants if v]

    def _get_clean_phone_for_api(self, phone_number, country_code='ET'):
        """
        Clean phone number for API calls - removes formatting, keeps digits with country code
        """
        if not phone_number:
            return phone_number
            
        try:
            # Normalize first
            normalized = self._normalize_phone_number(phone_number, country_code)
            
            # For API, we might want just digits or a specific format
            # Remove all non-digit characters except +
            if normalized.startswith('+'):
                # Keep + for international format
                clean = '+' + ''.join(filter(str.isdigit, normalized[1:]))
            else:
                # Just digits
                clean = ''.join(filter(str.isdigit, normalized))
                
            return clean
            
        except Exception as e:
            _logger.warning(f"Error cleaning phone {phone_number}: {e}")
            # Fallback: just remove non-digits
            return ''.join(filter(str.isdigit, phone_number))

    @api.depends('customer_name', 'site_ids')
    def compute_lead_name(self):
        for rec in self:
            site_names = '-'.join(site.name for site in rec.site_ids)
            rec.name = f'{rec.customer_name}-{site_names}' if rec.customer_name else "New"

    @api.depends('country_id')
    def _compute_phone_prefix(self):
        for rec in self:
            rec.phone_prefix = f"+{rec.country_id.phone_code}" if rec.country_id and rec.country_id.phone_code else ""

    @api.depends_context('uid')
    def _compute_is_affilater_user(self):
        affilater_group = self.env.ref('crm_custom_menu.group_affilater', raise_if_not_found=False)
        for rec in self:
            rec.is_affilater_user = affilater_group and self.env.user in affilater_group.users

    @api.depends('assigned_supervisor_id', 'assigned_salesperson_id')
    def _compute_resolved_supervisor(self):
        """
        Compute the supervisor by checking assigned_supervisor_id first,
        if empty, find supervisor through salesperson mapping
        """
        for rec in self:
            if rec.assigned_supervisor_id:
                rec.resolved_supervisor_id = rec.assigned_supervisor_id
            elif rec.assigned_salesperson_id:
                # Find supervisor through salesperson mapping
                mapping = self.env['property.salesperson.mapping'].search([
                    ('user_id', '=', rec.assigned_salesperson_id.id)
                ], limit=1)
                rec.resolved_supervisor_id = mapping.supervisor_id if mapping else False
            else:
                rec.resolved_supervisor_id = False

    @api.model
    def _default_source_id(self):
        affilater_group = self.env.ref('crm_custom_menu.group_affilater', raise_if_not_found=False)
        if affilater_group and self.env.user in affilater_group.users:
            return self.env['utm.source'].search([('name', '=', 'Referral')], limit=1).id
        return False

    @api.constrains('source_id')
    def _check_source_id(self):
        affilater_group = self.env.ref('crm_custom_menu.group_affilater', raise_if_not_found=False)
        for rec in self:
            if affilater_group and self.env.user in affilater_group.users:
                source_affilater = self.env['utm.source'].search([('name', '=', 'Referral')], limit=1)
                if rec.source_id != source_affilater:
                    raise AccessError(_('You cannot change the Lead Source when it is set to Affiliate.'))

    @api.onchange('source_id')
    def _onchange_source_id(self):
        affilater_group = self.env.ref('crm_custom_menu.group_affilater', raise_if_not_found=False)
        if affilater_group and self.env.user in affilater_group.users:
            self.source_id = self.env['utm.source'].search([('name', '=', 'Referral')], limit=1).id

    @api.onchange('phone_no')
    def _onchange_validate_phone(self):
        for record in self:
            if record.phone_no and record.country_id and record.country_id.code:
                phone_call_center = record.phone_no.strip()
                country_code = record.country_id.code.upper()
                
                # Special case for Ethiopia (keep your existing logic)
                if country_code == 'ET':
                    if (phone_call_center.startswith('09') or phone_call_center.startswith('07')) and len(phone_call_center) == 10 and phone_call_center.isdigit():
                        return  # Accept as valid, skip further validation
                
                try:
                    # Use dynamic validation for all countries
                    parsed = phonenumbers.parse(phone_call_center, country_code)
                    if not phonenumbers.is_valid_number(parsed):
                        raise ValidationError(_('Invalid phone number for selected country'))
                    
                    # Auto-format the phone number to international format
                    formatted = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
                    record.phone_no = formatted
                        
                except Exception as e:
                    raise ValidationError(_('Invalid phone number format: %s') % str(e))

    @api.onchange('nominated_wing_id')
    def _onchange_nominated_wing_id(self):
        if self.nominated_wing_id:
            supervisors = self.env['property.sales.supervisor'].search([
                ('sales_team_id.wing_id', '=', self.nominated_wing_id.wing_id.id)
            ])
            return {'domain': {'nominated_supervisor_id': [('id', 'in', supervisors.ids)]}}
        else:
            return {'domain': {'nominated_supervisor_id': []}}

    def _get_next_available_supervisor_and_wing(self):
        Param = self.env['ir.config_parameter'].sudo()
        WingConfig = self.env['property.wing.config']
        # Only configs with source 'Affiliate'
        config = WingConfig.search([('source_id.name', '=', 'Referral')], limit=1)
        if not config:
            return False, False
        selected_supers = config.get_selected_supervisors()
        if not selected_supers:
            return False, config
        key = f'crm_custom_menu.last_rr_supervisor_{config.id}'
        last_index = int(Param.get_param(key, default=-1))
        next_index = (last_index + 1) % len(selected_supers)
        Param.set_param(key, next_index)
        return selected_supers[next_index], config

    def _get_next_available_rr_user_and_config(self):
        Param = self.env['ir.config_parameter'].sudo()
        WingConfig = self.env['property.wing.config']
        configs = WingConfig.search([('source_id.name', '=', 'Referral')])
        if not configs:
            return False, False

        # Step 1: Build a list of pools (each pool = list of users for a config)
        user_pools = []
        configs_list = []
        for config in configs:
            pool = list(config.get_selected_rr_pool())
            if pool:
                user_pools.append(pool)
                configs_list.append(config)
        if not user_pools:
            return False, False

        # Step 2: Interleave the pools (zig-zag order)
        user_config_pairs = []
        max_len = max(len(pool) for pool in user_pools)
        for i in range(max_len):
            for pool_idx, pool in enumerate(user_pools):
                if i < len(pool):
                    user = pool[i]
                    config = configs_list[pool_idx]
                    user_config_pairs.append((user, config))

        if not user_config_pairs:
            return False, False

        key = 'crm_custom_menu.last_rr_user_affilater'
        last_index = int(Param.get_param(key, default='-1'))

        # If index is out of bounds, reset
        if last_index < 0 or last_index >= len(user_config_pairs):
            next_index = 0
        else:
            last_user, last_config = user_config_pairs[last_index]
            last_lead = self.env['crm.affilater'].search(
                [('nominated_salesperson_id', '=', last_user.id)],
                order='id desc', limit=1
            )
            last_unsent = last_lead and last_lead.state_crm == 'draft'
            if last_unsent:
                next_index = last_index  # Keep assigning to this user
            else:
                next_index = (last_index + 1) % len(user_config_pairs)

        # Save new index
        Param.set_param(key, str(next_index))

        return user_config_pairs[next_index]

    @api.constrains('nominated_supervisor_id', 'nominated_wing_id')
    def _check_supervisor_in_wing(self):
        for rec in self:
            if rec.nominated_supervisor_id and rec.nominated_wing_id:
                if not rec.nominated_supervisor_id.sales_team_id:
                    raise ValidationError(_("Selected supervisor is not linked to any sales team!"))
                if rec.nominated_supervisor_id.sales_team_id.wing_id.id != rec.nominated_wing_id.wing_id.id:
                    raise ValidationError(_("Selected supervisor is not assigned to any team under the selected wing!"))

    # SMS FUNCTIONALITY

    def _send_sms(self, mobile_number, message):
        """
        Generic method to send SMS via AfroMessage API
        """
        try:
            # Clean the mobile number (remove spaces, dashes, etc.)
            mobile_number = mobile_number.replace(' ', '').replace('-', '').replace('+', '')

            # AfroMessage API configuration
            token = 'eyJhbGciOiJIUzI1NiJ9.eyJpZGVudGlmaWVyIjoiNlRaUTByWlZLejNoMVg4V3hVWUpUemRmUURTUGVNMFEiLCJleHAiOjE5MTYzMDcyODQsImlhdCI6MTc1ODU0MDg4NCwianRpIjoiNDAzMjQyYzItNjlkOS00MzBjLWI4ZGMtMzM0NDUzNjM5ZGExIn0.AXAEroQlKaAe7orHe2x6vkoZ-kTSfso_-XT_dIqlVbo'
            callback = 'YOUR_CALLBACK_URL'  # Optional: your webhook for delivery reports
            sender = 'Temer RE'  # Your registered sender name
            from_identifier = 'e80ad9d8-adf3-463f-80f4-7c4b39f7f164'  # Your identifier ID from AfroMessage

            # Session object
            session = requests.Session()
            base_url = 'https://api.afromessage.com/api/send'
            headers = {'Authorization': 'Bearer ' + token}

            # Final URL
            url = f"{base_url}?from={from_identifier}&sender={sender}&to={mobile_number}&message={message}&callback={callback}"

            # Make request
            result = session.get(url, headers=headers)

            # Check result
            if result.status_code == 200:
                json_response = result.json()
                if json_response.get('acknowledge') == 'success':
                    return True, "SMS sent successfully"
                else:
                    return False, f"AfroMessage API error: {json_response}"
            else:
                return False, f"HTTP error: {result.status_code}, Message: {result.content}"

        except Exception as e:
            return False, f"Error sending SMS: {str(e)}"

    def _send_sms_to_sales_person(self, lead, sales_person, customer_phone, is_existing=False):
        """
        Send SMS to the assigned sales person
        """
        try:
            if not sales_person or not sales_person.partner_id or not sales_person.partner_id.mobile:
                _logger.warning("No sales person assigned or sales person has no mobile number")
                return

            # Get sales person's details
            sales_person_mobile = sales_person.partner_id.mobile
            sales_name = sales_person.name or 'Sales Person'

            # Get lead source
            source = 'Referral'

            # Prepare the message based on whether it's for existing or new assignment
            if is_existing:
                message = f"Hi {sales_name}, lead {customer_phone} came via {source}. Please contact and work to close."
            else:
                message = f"Hi {sales_name}, new lead from {source}: {customer_phone}. Added to your pipeline—please check.\n\nTemer Properties, CRM"

            # Send SMS
            success, result_message = self._send_sms(sales_person_mobile, message)

            if success:
                _logger.info(f"SMS sent successfully to sales person: {sales_name}")
                # Log in the lead's chatter
                lead.message_post(
                    body=f"SMS notification sent to sales person: {sales_name}",
                    message_type='comment',
                    subtype_xmlid='mail.mt_comment'
                )
            else:
                _logger.error(f"Failed to send SMS to sales person: {result_message}")

        except Exception as e:
            _logger.error(f"Error sending SMS to sales person: {str(e)}")

    def _send_sms_to_supervisor(self, lead, supervisor, sales_person, is_existing=False):
        """
        Send SMS to the supervisor
        """
        try:
            if not supervisor or not supervisor.name or not supervisor.name.partner_id or not supervisor.name.partner_id.mobile:
                _logger.warning("No supervisor found or supervisor has no mobile number")
                return

            # Get supervisor's details
            supervisor_mobile = supervisor.name.partner_id.mobile
            supervisor_name = supervisor.name.name or 'Supervisor'
            sales_name = sales_person.name or 'Sales Person'

            # Get lead source
            source = 'Referral'

            # Prepare the message based on whether it's for existing or new assignment
            if is_existing:
                message = f"Hi {supervisor_name}, your rep {sales_name}’s customer contacted us via {source}. FYI."
            else:
                message = f"Hi {supervisor_name}, your rep {sales_name} got a new lead from {source}. Added to their pipeline—FYI."

            # Send SMS to supervisor
            success, result_message = self._send_sms(supervisor_mobile, message)

            if success:
                _logger.info(f"SMS sent successfully to supervisor: {supervisor_name}")
                # Log in the lead's chatter
                lead.message_post(
                    body=f"SMS notification sent to supervisor: {supervisor_name}",
                    message_type='comment',
                    subtype_xmlid='mail.mt_comment'
                )
            else:
                _logger.error(f"Failed to send SMS to supervisor: {result_message}")

        except Exception as e:
            _logger.error(f"Error sending SMS to supervisor: {str(e)}")

    def _get_supervisor_for_salesperson(self, salesperson):
        """
        Find the supervisor for a given salesperson through the mapping table
        """
        if not salesperson:
            return False
            
        mapping = self.env['property.salesperson.mapping'].search([
            ('user_id', '=', salesperson.id)
        ], limit=1)
        
        return mapping.supervisor_id if mapping else False

    # DUPLICATE PHONE HANDLING

    def _get_existing_salesperson_info(self, full_phone_number):
        """
        Get existing salesperson and supervisor information for duplicate phone number
        Check in temer.lead model first using sudo() to bypass security rules
        """
        # Generate variants for broader search
        phone_variants = self._generate_phone_variants(full_phone_number, self.country_id.code)
        
        for phone_variant in phone_variants:
            # Check in temer.lead first (most recent) using sudo for read access
            temer_lead = self.env['temer.lead'].sudo().search([
                ('phone_ids.phone', '=', phone_variant),
                ('state', 'not in', ['lost', 'expired'])  # Exclude closed leads
            ], order='create_date desc', limit=1)
            
            if temer_lead and temer_lead.user_id:
                salesperson = temer_lead.user_id
                supervisor = self._get_supervisor_for_salesperson(salesperson)
                return salesperson, supervisor, temer_lead
            
            # Check in crm.reception as fallback
            crm_reception = self.env['crm.reception'].search([
                ('full_phone.name', '=', phone_variant)
            ], order='create_date desc', limit=1)
            
            if crm_reception and crm_reception.sales_person:
                salesperson = crm_reception.sales_person
                supervisor = self._get_supervisor_for_salesperson(salesperson)
                return salesperson, supervisor, False
            
            # Check in crm.website as fallback
            crm_website = self.env['crm.website'].search([
                ('full_phone.name', '=', phone_variant)
            ], order='create_date desc', limit=1)
            
            if crm_website and crm_website.sales_person:
                salesperson = crm_website.sales_person
                supervisor = self._get_supervisor_for_salesperson(salesperson)
                return salesperson, supervisor, False
            
            # Check in crm.affilater as fallback
            crm_affilater = self.env['crm.affilater'].search([
                ('full_phone.name', '=', phone_variant)
            ], order='create_date desc', limit=1)
            
            if crm_affilater and crm_affilater.sales_person:
                salesperson = crm_affilater.sales_person
                supervisor = self._get_supervisor_for_salesperson(salesperson)
                return salesperson, supervisor, False
        
        return None, None, False

    def _get_duplicate_phone_message(self, full_phone_number, exclude_ids=None):
        """Check for duplicate phone in temer.lead and other models, return message with salesperson names."""
        exclude_ids = exclude_ids or []

        # Normalize the phone number for comparison
        normalized_phone = self._normalize_phone_number(full_phone_number, self.country_id.code)
        
        # Also generate variants for broader search
        phone_variants = self._generate_phone_variants(full_phone_number, self.country_id.code)
        
        messages = []

        # Check each model with all phone variants
        for phone_variant in phone_variants:
            # Check in temer.lead first using sudo() for read access
            temer_lead = self.env['temer.lead'].sudo().search([
                ('phone_ids.phone', '=', phone_variant),
                ('id', 'not in', exclude_ids),
                ('state', 'not in', ['lost', 'expired'])
            ], order='create_date desc', limit=1)
            
            if temer_lead and not any('Temer Leads' in msg for msg in messages):
                messages.append(f"In Temer Leads registered by: {temer_lead.user_id.name or 'Unknown Salesperson'}.")

            # Check in crm.reception
            crm_reception = self.env['crm.reception'].search([
                ('full_phone.name', '=', phone_variant),
                ('id', 'not in', exclude_ids)
            ], order='create_date desc', limit=1)
            
            if crm_reception and not any('Reception CRM' in msg for msg in messages):
                messages.append(f"In Reception CRM registered by: {crm_reception.sales_person.name or 'Unknown Salesperson'}.")

            # Check in crm.website
            crm_website = self.env['crm.website'].search([
                ('full_phone.name', '=', phone_variant),
                ('id', 'not in', exclude_ids)
            ], order='create_date desc', limit=1)
            
            if crm_website and not any('Website CRM' in msg for msg in messages):
                messages.append(f"In Website CRM registered by: {crm_website.sales_person.name or 'Unknown Salesperson'}.")

            # Check in crm.affilater (exclude current record)
            current_id = [self.id] if self.id else []
            crm_affilater = self.env['crm.affilater'].search([
                ('full_phone.name', '=', phone_variant),
                ('id', 'not in', exclude_ids + current_id)
            ], order='create_date desc', limit=1)
            
            if crm_affilater and not any('Referral CRM' in msg for msg in messages):
                messages.append(f"In Referral CRM registered by: {crm_affilater.sales_person.name or 'Unknown Salesperson'}.")

            # If we found duplicates, no need to check more variants
            if messages:
                break

        return "\n".join(messages) if messages else False

    def _send_duplicate_to_endpoint(self, phone_number):
        """Send duplicate phone information directly to the external endpoint using URL parameters"""
        api_url = "http://165.232.70.106:2000/crm/status/phone"
        
        # Generate proper phone variants based on country
        phone_variants = self._generate_phone_variants(phone_number, self.country_id.code)
        
        _logger.info("Sending duplicate info to endpoint for phone variants: %s", phone_variants)
        
        for candidate_phone in phone_variants:
            # Clean the phone for API (remove formatting)
            clean_phone = self._get_clean_phone_for_api(candidate_phone, self.country_id.code)
            
            params = {
                'phone': clean_phone,
                'status': 'True',
            }
            
            _logger.info("Calling duplicate endpoint with params: %s", params)
            try:
                # Use params instead of json in the request
                resp = requests.patch(api_url, params=params, timeout=10)
                
                _logger.info("Duplicate API response status: %s, body: %s", resp.status_code, resp.text)
                
                if 200 <= resp.status_code < 300:
                    _logger.info(
                        "Duplicate info sent successfully. Phone: %s, Affilater ID: %s", 
                        clean_phone, self.id
                    )
                    break  # Stop if successful
                    
                elif resp.status_code == 404:
                    _logger.info("API returned 404 for phone %s — trying next variant", clean_phone)
                    continue
                else:
                    _logger.error("API returned unexpected status %s for duplicate phone %s: %s", 
                                resp.status_code, clean_phone, resp.text)
                    break
                    
            except requests.exceptions.RequestException as e:
                _logger.error(
                    "API call failed for duplicate phone %s. Error: %s",
                    clean_phone, str(e)
                )
                break
            except Exception as e:
                _logger.exception("Unexpected error calling API for duplicate phone %s", clean_phone)
                break
        
        _logger.info("Duplicate phone processing completed for affilater ID: %s", self.id)

    # CREATE AND WRITE METHODS

    @api.model
    def create(self, vals):
        rr_user, config = self._get_next_available_rr_user_and_config()
        vals['nominated_salesperson_id'] = rr_user.id if rr_user else False
        vals['nominated_wing_id'] = config.id if config else False

        # If the chosen user is a supervisor, set nominated_supervisor_id as well
        supervisor = self.env['property.sales.supervisor'].search([('name', '=', rr_user.id)], limit=1) if rr_user else False
        vals['nominated_supervisor_id'] = supervisor.id if supervisor else False

        # Check for duplicate phone and store existing salesperson info
        is_duplicate = False
        existing_salesperson = False
        existing_supervisor = False
        existing_temer_lead = False
        
        if vals.get('phone_no'):
            # Get country code (default to ET if not set)
            country_id = vals.get('country_id', self.env.ref('base.et').id)
            country = self.env['res.country'].browse(country_id)
            country_code = country.code if country else 'ET'
            
            # Normalize the phone number
            normalized_phone = self._normalize_phone_number(vals['phone_no'], country_code)
            
            # Use normalized phone for duplicate checking
            message = self._get_duplicate_phone_message(normalized_phone)
            if message:
                vals['phone_number_message'] = message
                # Set duplicate boolean to True
                vals['is_duplicate_phone'] = True
                # Get existing salesperson and supervisor info
                existing_salesperson, existing_supervisor, existing_temer_lead = self._get_existing_salesperson_info(normalized_phone)
                if existing_salesperson:
                    vals['existing_salesperson_id'] = existing_salesperson.id
                if existing_supervisor:
                    vals['existing_supervisor_id'] = existing_supervisor.id
                if existing_temer_lead:
                    vals['existing_temer_lead_id'] = existing_temer_lead.id
                
                is_duplicate = True
            else:
                # No duplicate found, set boolean to False
                vals['is_duplicate_phone'] = False
            
            # Store the normalized phone number
            phone_entry = self.env['crm.affilater.phone'].search([('name', '=', normalized_phone)], limit=1)
            if not phone_entry:
                phone_entry = self.env['crm.affilater.phone'].create({'name': normalized_phone})
            vals['full_phone'] = [(4, phone_entry.id)]
        
        # Create the record
        record = super().create(vals)
        
        # AUTOMATICALLY CREATE TEMER.LEAD AFTER SAVE
        if not is_duplicate:
            # Only create temer.lead for NEW phone numbers
            record._create_temer_lead_automatically()
        else:
            # For duplicate numbers, send SMS immediately
            record._send_sms_for_duplicate()
        
        return record

    def write(self, vals):
        # Send duplicate info to endpoint for any phone update
        if vals.get('phone_no'):
            clean_phone = vals['phone_no'].strip()
            country_code = self.country_id.code if self.country_id else 'ET'
            normalized_phone = self._normalize_phone_number(clean_phone, country_code)
            self._send_duplicate_to_endpoint(normalized_phone)
            
        if not self.customer_name or not self.customer_name.strip():
            raise ValidationError(_("Customer name is required"))
        if not self.phone_no:
            raise ValidationError(_("Primary phone number is required"))
            
        for rec in self:
            if rec.state_crm == 'draft' and any(key in vals for key in ('customer_name', 'site_ids', 'phone_no')):
                rr_user, config = rec._get_next_available_rr_user_and_config()
                vals['nominated_salesperson_id'] = rr_user.id if rr_user else False
                vals['nominated_wing_id'] = config.id if config else False
                supervisor = rec.env['property.sales.supervisor'].search([('name', '=', rr_user.id)], limit=1) if rr_user else False
                vals['nominated_supervisor_id'] = supervisor.id if supervisor else False

        for rec in self:
            if vals.get('phone_no'):
                clean_phone = vals['phone_no'].strip()
                country_code = rec.country_id.code if rec.country_id else 'ET'
                normalized_phone = rec._normalize_phone_number(clean_phone, country_code)
                
                message = rec._get_duplicate_phone_message(normalized_phone)
                if message:
                    vals['phone_number_message'] = message
                    # Set duplicate boolean to True
                    vals['is_duplicate_phone'] = True
                    # Get existing salesperson and supervisor info
                    existing_salesperson, existing_supervisor, existing_temer_lead = rec._get_existing_salesperson_info(normalized_phone)
                    if existing_salesperson:
                        vals['existing_salesperson_id'] = existing_salesperson.id
                    if existing_supervisor:
                        vals['existing_supervisor_id'] = existing_supervisor.id
                    if existing_temer_lead:
                        vals['existing_temer_lead_id'] = existing_temer_lead.id
                else:
                    # No duplicate found, set boolean to False
                    vals['is_duplicate_phone'] = False
                
                phone_entry = self.env['crm.affilater.phone'].search([('name', '=', normalized_phone)], limit=1)
                if not phone_entry:
                    phone_entry = self.env['crm.affilater.phone'].create({'name': normalized_phone})
                vals['full_phone'] = [(4, phone_entry.id)]
        
        return super().write(vals)

    def _create_temer_lead_automatically(self):
        """Automatically create temer.lead for new phone numbers"""
        self.ensure_one()
        
        if self.state_crm != 'draft' or not self.phone_no:
            return
            
        # Clean and validate phone number
        clean_phone = self.phone_no.strip()
        country_code = self.country_id.code if self.country_id else 'ET'
        normalized_phone = self._normalize_phone_number(clean_phone, country_code)
            
        if not self.customer_name or not self.customer_name.strip():
            return
        if not clean_phone:
            return

        source_id = self.source_id.id or self.env['utm.source'].search([('name', '=', 'Referral')], limit=1).id
        
        # Create temer.lead for NEW phone numbers
        _logger.info("=== AUTOMATIC TEMER.LEAD CREATION FOR REFERRAL ===")
        
        lead_values = {
            'name': self.name or f"Lead from {self.customer_name.strip()}",
            'customer_name': self.customer_name.strip(),
            'phone_no': clean_phone,
            'site_ids': [(6, 0, self.site_ids.ids)],
            'country_id': self.country_id.id,
            'source_ids': source_id,
            'user_id': self.nominated_salesperson_id.id,
            'state': 'prospect',
            'from_affilater': True,
            'is_duplicate_phone': False,  # Explicitly set to False for new leads
        }
        
        _logger.info("Automatic Temer Lead Values: %s", lead_values)
        
        try:
            # Create temer.lead with context to disable mail notifications
            lead = self.env['temer.lead'].with_user(self.nominated_salesperson_id).with_context(
                mail_create_nosubscribe=True,
                mail_create_nolog=True,
                tracking_disable=True
            ).create(lead_values)
            
            # Send SMS to newly assigned salesperson and supervisor for NEW leads
            _logger.info("=== NEW ASSIGNMENT SCENARIO ===")
            
            # Send SMS to sales person
            _logger.info(f"Sending SMS to assigned salesperson: {self.nominated_salesperson_id.name}")
            self._send_sms_to_sales_person(lead, self.nominated_salesperson_id, normalized_phone, is_existing=False)
            
            # Send SMS to supervisor (if exists)
            supervisor_to_notify = self.nominated_supervisor_id
            if not supervisor_to_notify and self.nominated_salesperson_id:
                supervisor_to_notify = self._get_supervisor_for_salesperson(self.nominated_salesperson_id)
                _logger.info(f"Found supervisor through mapping: {supervisor_to_notify.name if supervisor_to_notify else 'None'}")
            
            if supervisor_to_notify:
                _logger.info(f"Sending SMS to supervisor: {supervisor_to_notify.name}")
                self._send_sms_to_supervisor(lead, supervisor_to_notify, self.nominated_salesperson_id, is_existing=False)
            else:
                _logger.info("No supervisor found to notify")
            
            # Set assigned fields
            self.write({
                'assigned_salesperson_id': self.nominated_salesperson_id.id,
                'assigned_wing_id': self.nominated_wing_id.id,
                'assigned_supervisor_id': supervisor_to_notify.id if supervisor_to_notify else False,
                'state_crm': 'sent'
            })
            
            _logger.info("=== AUTOMATIC LEAD CREATION COMPLETED ===")
            
        except Exception as e:
            _logger.error(f"Error creating automatic temer.lead: {str(e)}")
            # Don't raise error to allow affilater record to be saved

    def _send_sms_for_duplicate(self):
        """Send SMS for duplicate phone numbers automatically"""
        self.ensure_one()
        
        if not self.phone_number_message or not self.existing_salesperson_id:
            return
            
        clean_phone = self.phone_no.strip() if self.phone_no else ''
        country_code = self.country_id.code if self.country_id else 'ET'
        normalized_phone = self._normalize_phone_number(clean_phone, country_code)
        
        _logger.info("=== AUTOMATIC SMS FOR DUPLICATE PHONE (REFERRAL) ===")
        _logger.info(f"Sending SMS to existing salesperson: {self.existing_salesperson_id.name}")
        
        # Create a temporary lead for SMS logging
        temp_lead = self.env['temer.lead'].create({
            'name': f"Temp lead for SMS - {self.customer_name}",
            'customer_name': self.customer_name.strip(),
            'state': 'prospect',
        })
        
        self._send_sms_to_sales_person(temp_lead, self.existing_salesperson_id, normalized_phone, is_existing=True)
        
        if self.existing_supervisor_id:
            _logger.info(f"Sending SMS to existing supervisor: {self.existing_supervisor_id.name}")
            self._send_sms_to_supervisor(temp_lead, self.existing_supervisor_id, self.existing_salesperson_id, is_existing=True)
        else:
            # Try to find supervisor through mapping
            existing_supervisor = self._get_supervisor_for_salesperson(self.existing_salesperson_id)
            if existing_supervisor:
                _logger.info(f"Sending SMS to mapped supervisor: {existing_supervisor.name}")
                self._send_sms_to_supervisor(temp_lead, existing_supervisor, self.existing_salesperson_id, is_existing=True)
        
        # Delete the temporary lead
        temp_lead.unlink()
        
        # SEND DUPLICATE INFORMATION DIRECTLY TO ENDPOINT
        _logger.info("=== SENDING DUPLICATE INFO TO ENDPOINT ===")
        self._send_duplicate_to_endpoint(normalized_phone)
        
        # Update state to sent for duplicate records too
        self.write({'state_crm': 'sent'})
        
        _logger.info("=== AUTOMATIC SMS SENT FOR DUPLICATE ===")

    # ACTION METHODS

    def action_send_sms_to_existing_customer(self):
        """Send SMS to existing salesperson and supervisor for duplicate phone numbers"""
        self.ensure_one()
        
        if not self.phone_number_message or not self.existing_salesperson_id:
            raise ValidationError(_("No existing salesperson found for this phone number."))
        
        clean_phone = self.phone_no.strip() if self.phone_no else ''
        country_code = self.country_id.code if self.country_id else 'ET'
        normalized_phone = self._normalize_phone_number(clean_phone, country_code)
        
        # Create temporary lead for SMS logging
        temp_lead = self.env['temer.lead'].create({
            'name': f"Temp SMS lead - {self.customer_name}",
            'customer_name': self.customer_name.strip(),
            'state': 'prospect',
        })
        
        # Send SMS to existing salesperson
        self._send_sms_to_sales_person(temp_lead, self.existing_salesperson_id, normalized_phone, is_existing=True)
        
        # Send SMS to existing supervisor
        if self.existing_supervisor_id:
            self._send_sms_to_supervisor(temp_lead, self.existing_supervisor_id, self.existing_salesperson_id, is_existing=True)
        else:
            existing_supervisor = self._get_supervisor_for_salesperson(self.existing_salesperson_id)
            if existing_supervisor:
                self._send_sms_to_supervisor(temp_lead, existing_supervisor, self.existing_salesperson_id, is_existing=True)
        
        # Delete temporary lead
        temp_lead.unlink()
        
        # Show success message
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('SMS Sent'),
                'message': _('SMS notification sent to existing salesperson and supervisor.'),
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_open_existing_temer_lead(self):
        """Open the existing temer.lead record"""
        self.ensure_one()
        if not self.existing_temer_lead_id:
            raise ValidationError(_("No existing temer.lead found."))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Existing Temer Lead'),
            'res_model': 'temer.lead',
            'res_id': self.existing_temer_lead_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # Remove the manual action_create_temer_lead method since it's now automatic