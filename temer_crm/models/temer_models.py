# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import logging
from odoo.exceptions import UserError
_logger = logging.getLogger(__name__)


class Propertymanagement(models.Model):
    _inherit = 'property.reservation'

    temer_lead_ids = fields.Many2one('temer.lead')
    salesperson_ids = fields.Many2one(
        'res.users',
        string="Salesperson",
        readonly=True,
    )

    @api.model
    def create(self, vals):
        reservation = super(Propertymanagement, self).create(vals)
        # Update the lead status when reservation is successfully created
        if reservation.temer_lead_ids:
            reservation.temer_lead_ids.action_set_reserved()
        return reservation


class TemerLeadAdditionalNumbers(models.Model):
    _name = 'temer.lead.additional.numbers'
    _description = 'Temer Lead Additional Numbers'

    lead_id = fields.Many2one(
        'temer.lead',
        string='Lead',
        required=True,
        ondelete='cascade'
    )

    number = fields.Char(
        string='Number',
        required=True,
        help="Store any number without validation"
    )

    description = fields.Char(
        string='Description',
        help="Optional description for this number"
    )

    created_date = fields.Datetime(
        string='Created Date',
        default=fields.Datetime.now
    )


class TemerLeadStageHistory(models.Model):
    _name = 'temer.lead.stage.history'
    _description = 'Temer Lead Stage History'
    _order = 'transition_date desc'

    lead_id = fields.Many2one('temer.lead', string='Lead', required=True, ondelete='cascade')
    from_stage = fields.Selection([
        ('prospect', 'Prospect'),
        ('follow_up', 'Follow Up'),
        ('reservation', 'Reserved'),
        ('won', 'Won'),
        ('lost', 'Lost'),
        ('expired', 'Expired')
    ], string='From Stage')
    to_stage = fields.Selection([
        ('prospect', 'Prospect'),
        ('follow_up', 'Follow Up'),
        ('reservation', 'Reserved'),
        ('won', 'Won'),
        ('lost', 'Lost'),
        ('expired', 'Expired')
    ], string='To Stage', required=True)
    transition_date = fields.Datetime(string='Transition Date', default=fields.Datetime.now)
    user_id = fields.Many2one('res.users', string='Changed By', default=lambda self: self.env.user)
    year = fields.Integer(string='Year', compute='_compute_date_parts', store=True)
    month = fields.Integer(string='Month', compute='_compute_date_parts', store=True)
    quarter = fields.Integer(string='Quarter', compute='_compute_date_parts', store=True)
    
    # SIMPLIFIED FIELDS - Only salesperson and source
    salesperson_id = fields.Many2one(
        'res.users', 
        string='Salesperson', 
        compute='_compute_salesperson_source', 
        store=True
    )
    source_id = fields.Many2one(
        'utm.source', 
        string='Source', 
        compute='_compute_salesperson_source', 
        store=True
    )
    count_field = fields.Integer(string='Count', default=1)

    @api.depends('transition_date')
    def _compute_date_parts(self):
        for record in self:
            if record.transition_date:
                record.year = record.transition_date.year
                record.month = record.transition_date.month
                record.quarter = (record.transition_date.month - 1) // 3 + 1
            else:
                current_date = fields.Datetime.now()
                record.year = current_date.year
                record.month = current_date.month
                record.quarter = (current_date.month - 1) // 3 + 1

    @api.depends('lead_id.user_id', 'lead_id.source_ids')
    def _compute_salesperson_source(self):
        """Compute salesperson and source from the lead"""
        for record in self:
            if record.lead_id:
                record.salesperson_id = record.lead_id.user_id
                record.source_id = record.lead_id.source_ids
            else:
                record.salesperson_id = False
                record.source_id = False


class TemerLead(models.Model):
    _name = 'temer.lead'
    _description = 'Temer Lead'
    _order = 'create_date desc'

    name = fields.Char(
        string='Name',
        required=True,
        compute="compute_lead_name",
        tracking=True
    )

    country_id = fields.Many2one(
        'res.country',
        string='Country',
        required=True,
        tracking=True,
        default=lambda self: self.env['res.country'].search([('phone_code', '=', 251)], limit=1)
    )

    phone_no = fields.Char(
        string='New Phone Number',
        help="Enter phone number without country code",
        tracking=True
    )

    phone_code = fields.Char(
        string='Country Code',
        compute='_compute_phone_code'
    )

    phone_ids = fields.One2many(
        'temer.phone',
        'lead_id',
        string='Phone Numbers',
        readonly=False
    )

    from_callcenter = fields.Boolean(
        string="From Call Center",
        default=False,
        help="Indicates if this lead was created from the call center"
    )
    # New One2many field for storing numbers without validation
    additional_numbers_ids = fields.One2many(
        'temer.lead.additional.numbers',
        'lead_id',
        string='Additional Numbers',
        help="Store additional numbers without validation"
    )
    from_website = fields.Boolean("From Website", default=False)
    from_affilater = fields.Boolean("From Affilater", default=False)
    state = fields.Selection([
        ('prospect', 'Prospect'),
        ('follow_up', 'Follow Up'),
        ('reservation', 'Reserved'),
        ('won', 'Sold'),
        ('lost', 'Lost'),
        ('expired', 'Expired')
    ], string='Status', default='prospect', tracking=True)
    partner_id = fields.Many2one('res.partner',
                                 domain="[('create_uid', '=', uid)]")
    # Add this field to track when the lead entered prospect state
    prospect_date = fields.Datetime(
        string='Prospect Since',
        help="Date when the lead was set to prospect state",
        default=fields.Datetime.now
    )
    supervisor_id = fields.Many2one('property.sales.supervisor', string="Sales Supervisor", readonly=True)
    sales_team_id = fields.Many2one('property.sales.team', string="Sales Team", readonly=True)
    wing_id = fields.Many2one('property.sales.wing', string="Sales Wing", readonly=True)
    
    from_reception = fields.Boolean("From Reception", default=False)
    customer_name = fields.Char(string='Customer', tracking=True, required=True)
    site_ids = fields.Many2many('property.site', string="site", tracking=True, required=True)
    source_ids = fields.Many2one('utm.source', string="Source", required=True)
    notes = fields.Text(string='Notes')
    user_id = fields.Many2one(
        'res.users',
        string='Salesperson',
        default=lambda self: self.env.user
    )
    counted_reservation = fields.Integer(
        string='Reservation',
        compute='compute_reservation_count'
    )

    # Stage History Fields
    stage_history_ids = fields.One2many('temer.lead.stage.history', 'lead_id', string='Stage History')
 
    # Historical count fields (all-time)
    total_prospect_count = fields.Integer(string='Total Prospect Count', compute='_compute_historical_counts')
    total_follow_up_count = fields.Integer(string='Total Follow Up Count', compute='_compute_historical_counts')
    total_reservation_count = fields.Integer(string='Total Reservation Count', compute='_compute_historical_counts')
    total_won_count = fields.Integer(string='Total Won Count', compute='_compute_historical_counts')
    total_lost_count = fields.Integer(string='Total Lost Count', compute='_compute_historical_counts')
    total_expired_count = fields.Integer(string='Total Expired Count', compute='_compute_historical_counts')
    

    state_sequence = fields.Integer(
        string='State Sequence',
        compute='_compute_state_sequence',
        store=True
        )

    @api.depends('state')
    def _compute_state_sequence(self):
        """Compute sequence for state ordering"""
        sequence_map = {
            'prospect': 1,
            'follow_up': 2,
            'reservation': 3,
            'won': 4,
            'lost': 5,
            'expired': 6
        }
        for record in self:
            record.state_sequence = sequence_map.get(record.state, 0)
            

    def compute_reservation_count(self):
        for rec in self:
            rec.counted_reservation = self.env['property.reservation'].search_count([('temer_lead_ids', '=', rec.id)])

    @api.depends('country_id')
    def _compute_phone_code(self):
        for record in self:
            if record.country_id:
                record.phone_code = f"+{record.country_id.phone_code}"
            else:
                record.phone_code = False

    @api.depends('customer_name', 'site_ids')
    def compute_lead_name(self):
        for rec in self:
            site_names = '-'.join([site.name for site in rec.site_ids])
            if rec.customer_name:
                rec.name = f'{rec.customer_name}-{site_names}'
            else:
                rec.name = "New"

    @api.constrains('phone_no')
    def _validate_phone_input(self):
        """Validate the phone number input before adding to list"""
        for record in self:
            if record.phone_no:
                if not record.phone_no.isdigit():
                    raise ValidationError(_("Phone number should contain only digits."))

                if record.country_id.phone_code == 251:  # Ethiopia
                    if record.phone_no.startswith('0'):
                        raise ValidationError(_("Ethiopian phone numbers must not start with 0."))
                    if len(record.phone_no) != 9:
                        raise ValidationError(_("Ethiopian phone numbers must be 9 digits."))

    def _check_duplicate_phone_in_crm_lead(self, phone):
        """Check if phone number exists in crm.lead"""
        if not phone:
            return False

        domain = [
            ('is_won', '!=', True),
            ('is_lost', '!=', True),
            ('is_expired', '!=', True),
            '|',  # This makes it OR for the phone conditions
            ('phone_ids.phone', '=', phone),
            ('phone_no', '=', phone)
        ]

        duplicates = self.env['crm.lead'].search(domain, limit=1)
        return bool(duplicates)

    @api.model
    def create(self, vals):
        """Override create to create partner and set prospect_date, with phone validation"""
        # Check for phone number duplication before creating anything
        # if not vals.get('phone_no'):
        #     raise ValidationError("Phone Number is required when creating a new lead!")  
        if 'phone_no' in vals and vals.get('phone_no'):
            country_id = vals.get('country_id')
            if country_id:
                country = self.env['res.country'].browse(country_id)
                formatted_phone = f"+{country.phone_code}{vals['phone_no']}"

                # Check if phone already exists
                existing_phone = self.env['temer.phone'].search([
                    ('phone', '=', formatted_phone)
                ], limit=1)

                if existing_phone:
                    raise ValidationError(_(
                        "This phone number is already registered in the system. "
                        "Phone number must be unique! Please use a different phone number."
                    ))
                if self._check_duplicate_phone_in_crm_lead(formatted_phone):
                    raise ValidationError(_(
                        "This phone number is already registered in CRM Leads. "
                        "Please use a different phone number or check the existing lead in CRM."
                    ))

        # Create partner first if customer_name is provided
        partner_id = False
        if 'customer_name' in vals and vals.get('customer_name'):
            partner = self.env['res.partner'].create({
                'name': vals['customer_name'],
                'company_type': 'person',
            })
            partner_id = partner.id
            vals['partner_id'] = partner_id

        # Set prospect_date if state is not provided
        if 'state' not in vals:
            vals['prospect_date'] = fields.Datetime.now()

        # Create the lead
        lead = super(TemerLead, self).create(vals)

        # Record initial stage history
        if lead.state == 'prospect':
            self.env['temer.lead.stage.history'].create({
                'lead_id': lead.id,
                'from_stage': False,
                'to_stage': 'prospect',
                'transition_date': fields.Datetime.now(),
            })

        # If phone number was provided during creation, add it immediately
        if 'phone_no' in vals and vals.get('phone_no') and lead.country_id:
            try:
                formatted_phone = f"+{lead.country_id.phone_code}{vals['phone_no']}"

                # Create in phone_ids (with validation)
                self.env['temer.phone'].create({
                    'phone': formatted_phone,
                    'country_id': lead.country_id.id,
                    'lead_id': lead.id,
                })

                # ALSO add to additional_numbers_ids (without validation)
                self.env['temer.lead.additional.numbers'].create({
                    'number': vals['phone_no'],
                    'description': 'Primary phone number',
                    'lead_id': lead.id,
                })

                lead.write({'phone_no': False})

            except Exception as e:
                # If phone creation fails, delete the lead we just created
                lead.unlink()
                if "phone_unique" in str(e):
                    raise ValidationError(_(
                        "This phone number is already registered in the system. "
                        "Phone number must be unique! Please use a different phone number."
                    ))
                else:
                    raise

        return lead

    def write(self, vals):
        """Override write to update prospect_date when state changes to prospect and handle phone updates"""

        # REMOVED THE SOURCE RESTRICTION CODE

        if 'site_ids' in vals and any(rec.id for rec in self):
            # Only check for existing records
            existing_records = self.filtered(lambda r: r.id)
            for record in existing_records:
                current_sites = set(record.site_ids.ids)
                new_sites_commands = vals['site_ids']
                
                for command in new_sites_commands:
                    if command[0] == 3:  # REMOVE
                        raise UserError("Cannot remove sites. You can only add new ones.")
                    elif command[0] == 5:  # CLEAR ALL
                        raise UserError("Cannot clear all sites. You can only add new ones.")
                    elif command[0] == 6:  # REPLACE
                        new_sites = set(command[2])
                        if current_sites - new_sites:
                            raise UserError("Cannot remove existing sites. You can only add new ones.")
        
        if 'state' in vals:
            if vals['state'] == 'prospect':
                vals['prospect_date'] = fields.Datetime.now()
            elif vals['state'] != 'prospect':
                # Reset prospect_date when leaving prospect state
                vals['prospect_date'] = False

            # Track stage changes
            for record in self:
                old_state = record.state
                new_state = vals['state']

                if old_state != new_state:
                    self.env['temer.lead.stage.history'].create({
                        'lead_id': record.id,
                        'from_stage': old_state,
                        'to_stage': new_state,
                        'transition_date': fields.Datetime.now(),
                    })

        # Handle phone number updates during manual save
        if 'phone_no' in vals and vals.get('phone_no'):
            for record in self:
                # Get the country (either from vals or existing record)
                country_id = vals.get('country_id', record.country_id.id)
                country = self.env['res.country'].browse(country_id)

                if not country:
                    continue

                formatted_phone = f"+{country.phone_code}{vals['phone_no']}"

                # Check for duplicate phone numbers
                existing_phone = self.env['temer.phone'].search([
                    ('phone', '=', formatted_phone),
                    ('id', 'not in', record.phone_ids.ids)
                ], limit=1)

                if existing_phone:
                    raise ValidationError(_(
                        "This phone number is already registered in the system. "
                        "Phone number must be unique! Please use a different phone number."
                    ))

                if record._check_duplicate_phone_in_crm_lead(formatted_phone):
                    raise ValidationError(_(
                        "This phone number is already registered in CRM Leads. "
                        "Please use a different phone number or check the existing lead in CRM."
                    ))
                # Create new phone record
                try:
                    self.env['temer.phone'].create({
                        'phone': formatted_phone,
                        'country_id': country.id,
                        'lead_id': record.id,
                    })

                    # ALSO add to additional_numbers_ids (without validation)
                    self.env['temer.lead.additional.numbers'].create({
                        'number': vals['phone_no'],
                        'description': 'Additional phone number',
                        'lead_id': record.id,
                    })

                    # Clear the phone_no field after successful creation
                    vals['phone_no'] = False

                except Exception as e:
                    if "phone_unique" in str(e):
                        raise ValidationError(_(
                            "This phone number is already registered in the system. "
                            "Phone number must be unique! Please use a different phone number."
                        ))
                    else:
                        raise

        return super(TemerLead, self).write(vals)

    def add_phone_number(self):
        """Add a new phone number to the lead"""
        self.ensure_one()

        if not self.country_id:
            raise ValidationError(_("Please select a country."))

        formatted_phone = f"+{self.country_id.phone_code}{self.phone_no}"

        # Check for duplicate in crm.lead
        if self._check_duplicate_phone_in_crm_lead(formatted_phone):
            raise ValidationError(_(
                "This phone number is already registered in CRM Leads. "
                "Please use a different phone number or check the existing lead in CRM."
            ))

        try:
            # Create in phone_ids (with validation)
            self.env['temer.phone'].create({
                'phone': formatted_phone,
                'country_id': self.country_id.id,
                'lead_id': self.id,
            })

            # ALSO add to additional_numbers_ids (without validation)
            self.env['temer.lead.additional.numbers'].create({
                'number': self.phone_no,
                'description': 'Phone number added via button',
                'lead_id': self.id,
            })

            self.phone_no = False

        except Exception as e:
            if "phone_unique" in str(e):
                raise ValidationError(_(
                    "This phone number is already registered in the system. "
                    "Phone number must be unique!"
                ))
            else:
                raise

    # Historical counts computation
    @api.depends('stage_history_ids.to_stage')
    def _compute_historical_counts(self):
        """Compute historical counts for each stage"""
        for record in self:
            record.total_prospect_count = len(record.stage_history_ids.filtered(lambda x: x.to_stage == 'prospect'))
            record.total_follow_up_count = len(record.stage_history_ids.filtered(lambda x: x.to_stage == 'follow_up'))
            record.total_reservation_count = len(
                record.stage_history_ids.filtered(lambda x: x.to_stage == 'reservation'))
            record.total_won_count = len(record.stage_history_ids.filtered(lambda x: x.to_stage == 'won'))
            record.total_lost_count = len(record.stage_history_ids.filtered(lambda x: x.to_stage == 'lost'))
            record.total_expired_count = len(record.stage_history_ids.filtered(lambda x: x.to_stage == 'expired'))

    def action_view_stage_history(self):
        """Action to view stage history in pivot view"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Stage History',
            'res_model': 'temer.lead.stage.history',
            'view_mode': 'pivot,tree,graph',
            'domain': [('lead_id', '=', self.id)],
            'target': 'current',
            'context': {
                'search_default_group_by_to_stage': 1,
                'search_default_group_by_year': 1,
                'search_default_group_by_month': 1,
            }
        }

    def action_view_all_stage_history(self):
        """Action to view all stage history in pivot view"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'All Stage History',
            'res_model': 'temer.lead.stage.history',
            'view_mode': 'pivot,tree,graph',
            'target': 'current',
            'context': {
                'search_default_group_by_to_stage': 1,
                'search_default_group_by_year': 1,
                'search_default_group_by_month': 1,
            }
        }

    def action_save_crm_records(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'current',
        }

    def action_mark_lost(self):
        self.write({'state': 'lost'})

    def action_mark_expired(self):
        """Manually mark as expired and delete phone numbers"""
        self._expire_leads()

    def _expire_leads(self):
        """Expire leads and delete their phone numbers"""
        for lead in self:
            # Delete associated phone numbers
            if lead.phone_ids:
                lead.phone_ids.unlink()
                _logger.info(f"Deleted phone numbers for expired lead {lead.name}")

            # Update state to expired
            lead.write({'state': 'expired', 'prospect_date': False})

    def action_reserve(self):
        for rec in self:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Reservation',
                'res_model': 'property.reservation',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_partner_id': rec.partner_id.id,
                    'default_temer_lead_ids': rec.id,
                    'default_salesperson_ids': rec.user_id.id,
                    'default_is_sufficient': False,
                    'default_property_id_domain': f"[('state', 'in', ['available']),('site', 'in', {rec.site_ids.ids})]"
                }
            }

    def action_set_reserved(self):
        self.write({'state': 'reservation'})

    def action_reserve_list(self):
        for rec in self:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Reservation',
                'res_model': 'property.reservation',
                'domain': [('temer_lead_ids', '=', rec.id)],
                'view_mode': 'kanban,tree,form',
                'target': 'current'
            }

    def name_get(self):
        result = []
        for record in self:
            name = f"{record.name} - {record.state.upper()}"
            result.append((record.id, name))
        return result

    @api.model
    def _cron_expire_prospect_leads(self):
        """Scheduled action to automatically expire leads after 1 month"""
        _logger.info("Starting automatic expiration of prospect leads...")

        # Calculate date 1 month ago
        one_month_ago = datetime.now() - timedelta(days=30)

        # Find leads that have been in prospect state for more than 1 month
        expired_leads = self.search([
            ('state', '=', 'prospect'),
            ('prospect_date', '<=', one_month_ago)
        ])

        if expired_leads:
            _logger.info(f"Found {len(expired_leads)} leads to expire")
            expired_leads._expire_leads()
            _logger.info(f"Successfully expired {len(expired_leads)} leads")
        else:
            _logger.info("No leads to expire at this time")

    # Add these new fields for activities
    activity_type = fields.Selection([
        ('call', 'Call'),
        ('sms', 'SMS'),
        ('email', 'Email'),
        ('office_visit', 'Office Visit'),
        ('site_visit', 'Site Visit')
    ], string='Activity Type')

    activity_description = fields.Text(string='Activity Description')

    # Field to track follow-up activities
    followup_line_ids = fields.One2many(
        'temer.lead.followup',
        'lead_id',
        string='Follow-up Activities'
    )

    def action_log_activity(self):
        """Open the activity logging wizard"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Log Activity',
            'res_model': 'temer.lead.activity.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_lead_id': self.id,
            }
        }

    def _update_state_to_followup(self):
        """Update state to follow_up if currently in prospect"""
        if self.state == 'prospect':
            self.write({'state': 'follow_up'})

    # Add these computed fields for activity counts
    call_count = fields.Integer(
        string='Call Count',
        compute='_compute_activity_counts',
        store=True
    )
    sms_count = fields.Integer(
        string='SMS Count',
        compute='_compute_activity_counts',
        store=True
    )
    email_count = fields.Integer(
        string='Email Count',
        compute='_compute_activity_counts',
        store=True
    )
    office_visit_count = fields.Integer(
        string='Office Visit Count',
        compute='_compute_activity_counts',
        store=True
    )
    site_visit_count = fields.Integer(
        string='Site Visit Count',
        compute='_compute_activity_counts',
        store=True
    )
    total_activities = fields.Integer(
        string='Total Activities',
        compute='_compute_activity_counts',
        store=True
    )

    @api.depends('followup_line_ids.activity_type')
    def _compute_activity_counts(self):
        """Compute counts for each activity type"""
        for record in self:
            record.call_count = len(record.followup_line_ids.filtered(lambda x: x.activity_type == 'call'))
            record.sms_count = len(record.followup_line_ids.filtered(lambda x: x.activity_type == 'sms'))
            record.email_count = len(record.followup_line_ids.filtered(lambda x: x.activity_type == 'email'))
            record.office_visit_count = len(
                record.followup_line_ids.filtered(lambda x: x.activity_type == 'office_visit'))
            record.site_visit_count = len(record.followup_line_ids.filtered(lambda x: x.activity_type == 'site_visit'))
            record.total_activities = len(record.followup_line_ids)

    def action_print_activity_report(self):
        """Print the activity report"""
        self.ensure_one()
        return self.env.ref('temer_crm.action_report_temer_lead_activities').report_action(self)
    

class TemerLeadFollowup(models.Model):
    _name = 'temer.lead.followup'
    _description = 'Temer Lead Follow-up Activities'
    _order = 'activity_date desc'

    lead_id = fields.Many2one('temer.lead', string='Lead', required=True)
    activity_type = fields.Selection([
        ('call', 'Call'),
        ('sms', 'SMS'),
        ('email', 'Email'),
        ('office_visit', 'Office Visit'),
        ('site_visit', 'Site Visit')
    ], string='Activity Type', required=True)
    description = fields.Text(string='Description')
    activity_date = fields.Datetime(string='Date', default=fields.Datetime.now)
    user_id = fields.Many2one(
        'res.users',
        string='Performed By',
        default=lambda self: self.env.user
    )

class TemerLeadActivityAnalysis(models.Model):
    _name = 'temer.lead.activity.analysis'
    _description = 'Temer Lead Activity Analysis'
    _auto = False
    _rec_name = 'display_name'

    display_name = fields.Char(string='Display Name')
    activity_type = fields.Selection([
        ('call', 'Call'),
        ('sms', 'SMS'),
        ('email', 'Email'),
        ('office_visit', 'Office Visit'),
        ('site_visit', 'Site Visit')
    ], string='Activity Type')
    lead_id = fields.Many2one('temer.lead', string='Lead')
    salesperson_id = fields.Many2one('res.users', string='Salesperson')
    activity_date = fields.Datetime(string='Activity Date')
    year = fields.Integer(string='Year')
    month = fields.Integer(string='Month')
    quarter = fields.Integer(string='Quarter')
    activity_count = fields.Integer(string='Activity Count')
    lead_count = fields.Integer(string='Lead Count')

    def init(self):
        from odoo import tools
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW temer_lead_activity_analysis AS (
                SELECT 
                    ROW_NUMBER() OVER() as id,
                    CONCAT(fu.activity_type, '_', fu.lead_id, '_', EXTRACT(YEAR FROM fu.activity_date)) as display_name,
                    fu.activity_type,
                    fu.lead_id,
                    fl.user_id as salesperson_id,
                    fu.activity_date,
                    EXTRACT(YEAR FROM fu.activity_date) as year,
                    EXTRACT(MONTH FROM fu.activity_date) as month,
                    EXTRACT(QUARTER FROM fu.activity_date) as quarter,
                    COUNT(*) as activity_count,
                    COUNT(DISTINCT fu.lead_id) as lead_count
                FROM temer_lead_followup fu
                JOIN temer_lead fl ON fu.lead_id = fl.id
                WHERE fu.activity_type IS NOT NULL
                GROUP BY 
                    fu.activity_type,
                    fu.lead_id,
                    fl.user_id,
                    fu.activity_date,
                    EXTRACT(YEAR FROM fu.activity_date),
                    EXTRACT(MONTH FROM fu.activity_date),
                    EXTRACT(QUARTER FROM fu.activity_date)
            )
        """)   