from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, AccessError
import phonenumbers
import logging
import requests
import re

_logger = logging.getLogger(__name__)

class CrmReceptionPhone(models.Model):
    _name = 'crm.reception.phone'
    _description = 'Reception Phone Numbers'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Phone Number", required=True, tracking=True)
    crm_lead_id = fields.Many2one('crm.lead', string="CRM Lead")
    reception_record_id = fields.Many2one('crm.reception', string="Reception Record")
    is_walk_in = fields.Boolean(string="Walk-in Customer", default=True)

class CrmReception(models.Model):
    _name = 'crm.reception'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Reception CRM Lead'
    _rec_name = 'name'

    # Main Fields
    name = fields.Char(string='Lead Reference', compute="_compute_lead_name", store=True)
    customer_name = fields.Char(string='Customer Name', required=True, tracking=True)
    site_ids = fields.Many2many('property.site', string="Preferred Sites", tracking=True)
    country_id = fields.Many2one('res.country', string="Country", default=lambda self: self.env.ref('base.et').id)
    new_phone = fields.Char(string="Phone no", tracking=True)
    secondary_phone = fields.Char(string="Secondary Phone")
    phone_prefix = fields.Char(string="Phone Prefix", compute="_compute_phone_prefix")
    phone_number = fields.Char(string="Phone Number")
    full_phone = fields.Many2many('crm.reception.phone', string="All Phone Numbers")
    phone_number_message = fields.Char(string="Phone Alert", readonly=True)
    crm_reception_phone_id = fields.Many2one('crm.reception.phone', string="Phone")
    
    # Supervisor and Salesperson fields
    nominated_supervisor_id = fields.Many2one('property.sales.supervisor', string="Nominated Supervisor", readonly=True, copy=False)
    nominated_wing_id = fields.Many2one('property.wing.config', string="Nominated Wing", readonly=True, copy=False)
    assigned_supervisor_id = fields.Many2one('property.sales.supervisor', string="Assigned Supervisor", readonly=True, copy=False)
    assigned_wing_id = fields.Many2one('property.wing.config', string="Assigned Wing", readonly=True, copy=False)
    nominated_salesperson_id = fields.Many2one('res.users', string="Nominated Person", readonly=True, copy=False)
    assigned_salesperson_id = fields.Many2one('res.users', string="Assigned Person", readonly=True, copy=False)
    
    # Status fields
    state_crm = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
    ], string='Status', default='draft', tracking=True)

    # Source and user info
    source_id = fields.Many2one('utm.source', string="Lead Source",
        default=lambda self: self._default_source_id(), tracking=True)
    is_reception_user = fields.Boolean(string="Is Reception User", compute="_compute_is_reception_user")
    sales_person = fields.Many2one('res.users', string="Receptionist", default=lambda self: self.env.user, readonly=True)
    crm_stage_id = fields.Many2one('crm.stage', string="CRM Stage")

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

    # COMPUTE/ONCHANGE METHODS

    @api.depends('customer_name', 'site_ids')
    def _compute_lead_name(self):
        for rec in self:
            if rec.customer_name:
                site_names = '-'.join([site.name for site in rec.site_ids]) if rec.site_ids else ''
                rec.name = f'{rec.customer_name}-{site_names}' if site_names else rec.customer_name
            else:
                rec.name = "New Reception Lead"

    @api.depends('country_id')
    def _compute_phone_prefix(self):
        for rec in self:
            rec.phone_prefix = f"+{rec.country_id.phone_code}" if rec.country_id and rec.country_id.phone_code else ""

    @api.depends_context('uid')
    def _compute_is_reception_user(self):
        reception_group = self.env.ref('crm_custom_menu.group_reception', raise_if_not_found=False)
        for record in self:
            record.is_reception_user = reception_group and self.env.user in reception_group.users

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

    # DEFAULTS/CONSTRAINTS

    @api.model
    def _default_source_id(self):
        reception_group = self.env.ref('crm_custom_menu.group_reception', raise_if_not_found=False)
        if reception_group and self.env.user in reception_group.users:
            return self.env['utm.source'].search([('name', '=', 'Walk In')], limit=1).id
        return False

    @api.constrains('source_id')
    def _check_source_id(self):
        reception_group = self.env.ref('crm_custom_menu.group_reception', raise_if_not_found=False)
        for record in self:
            if reception_group and self.env.user in reception_group.users:
                walk_in_source = self.env['utm.source'].search([('name', '=', 'Walk In')], limit=1)
                if record.source_id != walk_in_source:
                    raise AccessError(_('Reception users must keep the source as "Walk In"'))

    @api.onchange('new_phone')
    def _onchange_validate_phone(self):
        for record in self:
            if record.new_phone and record.country_id and record.country_id.code:
                phone = record.new_phone.strip()
                # Special case for Ethiopia (ET): allow 09... or 07... with 10 digits
                if record.country_id.code.upper() == 'ET':
                    if (
                    (phone.startswith('09') or phone.startswith('07'))
                    and len(phone) == 10
                    and phone.isdigit()
                ):
                        continue  # Accept as valid
                try:
                    parsed = phonenumbers.parse(phone, record.country_id.code)
                    if not phonenumbers.is_valid_number(parsed):
                        raise ValidationError(_('Invalid phone number for selected country'))
                except Exception as e:
                    raise ValidationError(_('Invalid phone number format: %s') % str(e))

    @api.constrains('nominated_supervisor_id', 'nominated_wing_id')
    def _check_supervisor_in_wing(self):
        for rec in self:
            if rec.nominated_supervisor_id and rec.nominated_wing_id:
                if not rec.nominated_supervisor_id.sales_team_id:
                    raise ValidationError(_("Selected supervisor is not linked to any sales team!"))
                if rec.nominated_supervisor_id.sales_team_id.wing_id.id != rec.nominated_wing_id.wing_id.id:
                    raise ValidationError(_("Selected supervisor is not assigned to any team under the selected wing!"))

    # ROUND ROBIN ASSIGNMENT METHODS

    def _get_next_available_supervisor_and_wing(self):
        Param = self.env['ir.config_parameter'].sudo()
        WingConfig = self.env['property.wing.config']
        configs = WingConfig.search([('source_id.name', '=', 'Walk In')])
        if not configs:
            return False, False

        # Combine all selected supervisors from all configs with source 'Walk In'
        sup_pool = []
        config_map = []
        for config in configs:
            pool = config.get_selected_supervisors()
            for sup in pool:
                sup_pool.append(sup)
                config_map.append(config)

        if not sup_pool:
            return False, False

        key = 'crm_custom_menu.last_rr_supervisor_walkin'
        last_index = int(Param.get_param(key, default=-1))
        next_index = (last_index + 1) % len(sup_pool)
        Param.set_param(key, next_index)
        # Return the supervisor and their corresponding config
        return sup_pool[next_index], config_map[next_index]

    def _get_next_available_rr_user_and_config(self):
        Param = self.env['ir.config_parameter'].sudo()
        WingConfig = self.env['property.wing.config']
        configs = WingConfig.search([('source_id.name', '=', 'Walk In')])
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

        key = 'crm_custom_menu.last_rr_user_walkin'
        last_index = int(Param.get_param(key, default='-1'))

        # If index is out of bounds, reset
        if last_index < 0 or last_index >= len(user_config_pairs):
            next_index = 0
        else:
            last_user, last_config = user_config_pairs[last_index]
            last_lead = self.env['crm.reception'].search(
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
            source = 'Walk In'

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
            source = 'Walk In'

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
        # Check in temer.lead first (most recent) using sudo for read access
        temer_lead = self.env['temer.lead'].sudo().search([
            ('phone_ids.phone', '=', full_phone_number),
            ('state', 'not in', ['lost', 'expired'])  # Exclude closed leads
        ], order='create_date desc', limit=1)
        
        if temer_lead and temer_lead.user_id:
            salesperson = temer_lead.user_id
            supervisor = self._get_supervisor_for_salesperson(salesperson)
            return salesperson, supervisor, temer_lead
        
        # Check in crm.reception as fallback
        crm_reception = self.env['crm.reception'].search([
            ('full_phone.name', '=', full_phone_number)
        ], order='create_date desc', limit=1)
        
        if crm_reception and crm_reception.sales_person:
            salesperson = crm_reception.sales_person
            supervisor = self._get_supervisor_for_salesperson(salesperson)
            return salesperson, supervisor, False
        
        # Check in crm.website as fallback
        crm_website = self.env['crm.website'].search([
            ('full_phone.name', '=', full_phone_number)
        ], order='create_date desc', limit=1)
        
        if crm_website and crm_website.sales_person:
            salesperson = crm_website.sales_person
            supervisor = self._get_supervisor_for_salesperson(salesperson)
            return salesperson, supervisor, False
        
        return None, None, False

    def _get_duplicate_phone_message(self, full_phone_number, exclude_ids=None):
        """Check for duplicate phone in temer.lead and other models, return message with salesperson names."""
        exclude_ids = exclude_ids or []

        # Check in temer.lead first using sudo() for read access
        temer_lead = self.env['temer.lead'].sudo().search([
            ('phone_ids.phone', '=', full_phone_number),
            ('id', 'not in', exclude_ids),
            ('state', 'not in', ['lost', 'expired'])
        ], order='create_date desc', limit=1)
        temer_lead_msg = ""
        if temer_lead:
            temer_lead_msg = f"In Temer Leads registered by: {temer_lead.user_id.name or 'Unknown Salesperson'}."

        # Check in crm.reception
        crm_reception = self.env['crm.reception'].search([
            ('full_phone.name', '=', full_phone_number),
            ('id', 'not in', exclude_ids)
        ], order='create_date desc', limit=1)
        crm_reception_msg = ""
        if crm_reception:
            crm_reception_msg = f"In Reception CRM registered by: {crm_reception.sales_person.name or 'Unknown Salesperson'}."

        # Check in crm.website
        crm_website = self.env['crm.website'].search([
            ('full_phone.name', '=', full_phone_number),
            ('id', 'not in', exclude_ids)
        ], order='create_date desc', limit=1)
        crm_website_msg = ""
        if crm_website:
            crm_website_msg = f"In Website CRM registered by: {crm_website.sales_person.name or 'Unknown Salesperson'}."

        # Combine messages - temer.lead first
        messages = [msg for msg in [temer_lead_msg, crm_reception_msg, crm_website_msg] if msg]
        return "\n".join(messages) if messages else False

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
        
        if vals.get('new_phone'):
            clean_phone = vals['new_phone'].strip()
            if clean_phone.startswith('+251'):
                clean_phone = clean_phone[4:]
            elif clean_phone.startswith('251'):
                clean_phone = clean_phone[3:]
            if clean_phone.startswith('0'):
                clean_phone = clean_phone[1:]
            full_phone_number = f"+251{clean_phone}"
            
            message = self._get_duplicate_phone_message(full_phone_number)
            if message:
                vals['phone_number_message'] = message
                # Get existing salesperson and supervisor info
                existing_salesperson, existing_supervisor, existing_temer_lead = self._get_existing_salesperson_info(full_phone_number)
                if existing_salesperson:
                    vals['existing_salesperson_id'] = existing_salesperson.id
                if existing_supervisor:
                    vals['existing_supervisor_id'] = existing_supervisor.id
                if existing_temer_lead:
                    vals['existing_temer_lead_id'] = existing_temer_lead.id
                
                is_duplicate = True
            
            phone_entry = self.env['crm.reception.phone'].search([('name', '=', full_phone_number)], limit=1)
            if not phone_entry:
                phone_entry = self.env['crm.reception.phone'].create({'name': full_phone_number})
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
        for rec in self:
            if rec.state_crm == 'draft' and any(key in vals for key in ('customer_name', 'site_ids', 'new_phone')):
                rr_user, config = rec._get_next_available_rr_user_and_config()
                vals['nominated_salesperson_id'] = rr_user.id if rr_user else False
                vals['nominated_wing_id'] = config.id if config else False
                supervisor = rec.env['property.sales.supervisor'].search([('name', '=', rr_user.id)], limit=1) if rr_user else False
                vals['nominated_supervisor_id'] = supervisor.id if supervisor else False

        for rec in self:
            if vals.get('new_phone'):
                clean_phone = vals['new_phone'].strip()
                if clean_phone.startswith('+251'):
                    clean_phone = clean_phone[4:]
                elif clean_phone.startswith('251'):
                    clean_phone = clean_phone[3:]
                if clean_phone.startswith('0'):
                    clean_phone = clean_phone[1:]
                full_phone_number = f"+251{clean_phone}"
                
                message = self._get_duplicate_phone_message(full_phone_number)
                if message:
                    vals['phone_number_message'] = message
                    # Get existing salesperson and supervisor info
                    existing_salesperson, existing_supervisor, existing_temer_lead = rec._get_existing_salesperson_info(full_phone_number)
                    if existing_salesperson:
                        vals['existing_salesperson_id'] = existing_salesperson.id
                    if existing_supervisor:
                        vals['existing_supervisor_id'] = existing_supervisor.id
                    if existing_temer_lead:
                        vals['existing_temer_lead_id'] = existing_temer_lead.id
                
                phone_entry = self.env['crm.reception.phone'].search([('name', '=', full_phone_number)], limit=1)
                if not phone_entry:
                    phone_entry = self.env['crm.reception.phone'].create({'name': full_phone_number})
                vals['full_phone'] = [(4, phone_entry.id)]
        
        return super().write(vals)

    def _create_temer_lead_automatically(self):
        """Automatically create temer.lead for new phone numbers"""
        self.ensure_one()
        
        if self.state_crm != 'draft' or not self.new_phone:
            return
            
        # Clean and validate phone number
        clean_phone = self.new_phone.strip()
        if clean_phone.startswith('+251'):
            clean_phone = clean_phone[4:]
        elif clean_phone.startswith('251'):
            clean_phone = clean_phone[3:]
        if clean_phone.startswith('0'):
            clean_phone = clean_phone[1:]
            
        if not self.customer_name or not self.customer_name.strip():
            return
        if not clean_phone:
            return

        source_id = self.source_id.id or self.env['utm.source'].search([('name', '=', 'Walk In')], limit=1).id
        
        # Create temer.lead for NEW phone numbers
        _logger.info("=== AUTOMATIC TEMER.LEAD CREATION FOR RECEPTION ===")
        
        lead_values = {
            'name': self.name or f"Lead from {self.customer_name.strip()}",
            'customer_name': self.customer_name.strip(),
            'phone_no': clean_phone,
            'site_ids': [(6, 0, self.site_ids.ids)],
            'country_id': self.country_id.id,
            'source_ids': source_id,
            'user_id': self.nominated_salesperson_id.id,
            'state': 'prospect',
            'from_reception': True,  # Mark as from reception
        }
        
        _logger.info("Automatic Temer Lead Values: %s", lead_values)
        
        try:
            # Create temer.lead with context to disable mail notifications
            lead = self.env['temer.lead'].with_user(self.nominated_salesperson_id).with_context(
                mail_create_nosubscribe=True,      # Don't subscribe followers
                mail_create_nolog=True,            # Don't log the creation
                tracking_disable=True              # Disable tracking
            ).create(lead_values)
            
            # Send SMS to newly assigned salesperson and supervisor for NEW leads
            _logger.info("=== NEW ASSIGNMENT SCENARIO ===")
            
            # Send SMS to sales person
            _logger.info(f"Sending SMS to assigned salesperson: {self.nominated_salesperson_id.name}")
            self._send_sms_to_sales_person(lead, self.nominated_salesperson_id, clean_phone, is_existing=False)
            
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
            # Don't raise error to allow reception record to be saved

    def _send_sms_for_duplicate(self):
        """Send SMS for duplicate phone numbers automatically"""
        self.ensure_one()
        
        if not self.phone_number_message or not self.existing_salesperson_id:
            return
            
        clean_phone = self.new_phone.strip() if self.new_phone else ''
        if clean_phone.startswith('+251'):
            clean_phone = clean_phone[4:]
        elif clean_phone.startswith('251'):
            clean_phone = clean_phone[3:]
        if clean_phone.startswith('0'):
            clean_phone = clean_phone[1:]
        
        _logger.info("=== AUTOMATIC SMS FOR DUPLICATE PHONE (RECEPTION) ===")
        _logger.info(f"Sending SMS to existing salesperson: {self.existing_salesperson_id.name}")
        
        # Create a temporary lead for SMS logging
        temp_lead = self.env['temer.lead'].create({
            'name': f"Temp lead for SMS - {self.customer_name}",
            'customer_name': self.customer_name.strip(),
            'state': 'prospect',
        })
        
        self._send_sms_to_sales_person(temp_lead, self.existing_salesperson_id, clean_phone, is_existing=True)
        
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
        
        # Update state to sent for duplicate records too
        self.write({'state_crm': 'sent'})
        
        _logger.info("=== AUTOMATIC SMS SENT FOR DUPLICATE ===")

    # ACTION METHODS

    def action_send_sms_to_existing_customer(self):
        """Send SMS to existing salesperson and supervisor for duplicate phone numbers"""
        self.ensure_one()
        
        if not self.phone_number_message or not self.existing_salesperson_id:
            raise ValidationError(_("No existing salesperson found for this phone number."))
        
        clean_phone = self.new_phone.strip() if self.new_phone else ''
        if clean_phone.startswith('+251'):
            clean_phone = clean_phone[4:]
        elif clean_phone.startswith('251'):
            clean_phone = clean_phone[3:]
        if clean_phone.startswith('0'):
            clean_phone = clean_phone[1:]
        
        # Create temporary lead for SMS logging
        temp_lead = self.env['temer.lead'].create({
            'name': f"Temp SMS lead - {self.customer_name}",
            'customer_name': self.customer_name.strip(),
            'state': 'prospect',
        })
        
        # Send SMS to existing salesperson
        self._send_sms_to_sales_person(temp_lead, self.existing_salesperson_id, clean_phone, is_existing=True)
        
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