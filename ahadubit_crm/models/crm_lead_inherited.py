# -*- coding: utf-8 -*-
##############################################################################
#    Ahadubit Technologies
#    Copyright (C) 2024-TODAY Ahadubit Technologies(<https://ahadubit.com>).
#    Author: Ahadubit Technologies (<https://ahadubit.com>)
##############################################################################
from email.policy import default
from pprint import pprint

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta

import base64
import imghdr
import logging
import re

_logger = logging.getLogger(__name__)

class CrmPhone(models.Model):
    _name = 'crm.phone'
    _rec_name = 'phone'


    country_id = fields.Many2one(
        'res.country',
        string='Country',
        required=True,
        help="Select the country for the phone number.",
        default=lambda self: self.env['res.country'].search([('phone_code', '=', 251)], limit=1)
    )
    phone = fields.Char(string='Phone', tracking=True,)
    partner_id = fields.Many2one('res.partner',string='Partner')
    name = fields.Char(string='Name', compute="compute_name")

    @api.depends('phone')
    def compute_name(self):
        for rec in self:
            rec.name = rec.partner_id


    @api.onchange('country_id')
    def compute_phone_perfix(self):
        for rec in self:
            if rec.country_id:
                rec.phone=False
                rec.phone=f"+{rec.country_id.phone_code}"


    @api.constrains('phone')
    def _check_phone_number(self):
        phone_regex = r'^\+?\d{1,15}$'
        for record in self:
            if record.phone:
                con_code=f"+{record.country_id.phone_code}"
                if not re.match(phone_regex, record.phone):
                    raise ValidationError("Invalid phone number format! Please enter a valid phone number.")
                if record.country_id.phone_code == 251:
                    if record.phone[0] =="0":
                        raise ValidationError("Invalid phone number format! Phone number must not start with 0.")
                    if  len(record.phone) != 13:
                        raise ValidationError("Invalid phone number format! Please enter a valid phone number.")
                elif (len(record.phone) - len(con_code))  < 5 or (len(record.phone) - len(con_code))> 14:
                    raise ValidationError("Invalid phone number format! Please enter a valid phone number.")
                
    def create(self, vals):
        partner_id = vals['partner_id']
        phone = vals['phone']
        clause = [('is_won', '!=', True), ('is_lost', '!=', True), ('is_expired', '!=', True),('phone_ids.phone', '=', phone)]
        leads = self.env['crm.lead'].sudo().search(clause)
        phone_ids = leads.mapped('phone_ids')
        for phone_id in phone_ids:
            added_phone_no = phone_id.phone 
            if phone == added_phone_no:
                raise ValidationError("This number is Already Registered, Phone number must be unique!")
        res = super(CrmPhone, self).create(vals)
        return res


class CrmStageInherited(models.Model):
    _inherit = 'crm.stage'
    is_reservation_stage = fields.Boolean(string='is Reservation Stage')
    is_lost_stage = fields.Boolean(string='is Lost Stage')
    is_expire_stage = fields.Boolean(string="is Expire stage")


class CrmResPartnerInherited(models.Model):
    _inherit = 'res.partner'
    phone_no = fields.Char(string='Phone')
    phone_ids = fields.Many2many('crm.phone',
                                 domain="[('create_uid', '=', uid)]",
                                 string="Phone" )
    is_expired = fields.Boolean(string="is Expired")


    # @api.constrains('phone_ids', 'phone_no')
    # def validate_customer_phone(self):
    #     for rec in self:
    #         if rec.phone_no:
    #             _logger.info(f"rec.phone_no===: {rec.phone_no}")
    #             _logger.info(f"rec.phone_ids===: {rec.phone_ids}")
            #     phone_no = f"+{rec.country_id.phone_code}{self.phone_no}"
            #     _logger.info(f"country: {rec.country_id.name}")
            #     _logger.info(f"country code: {rec.country_id.code}")
            #     _logger.info(f"country id: {rec.country_id.id}")
            #     _logger.info(f"country phone code: {rec.country_id.phone_code}")
            #     _logger.info(f"phone_no: {phone_no}")
            #     clause = [('id', '!=', rec.id),('is_won', '!=', True), ('is_lost', '!=', True), ('is_expired', '!=', True),('phone_ids.phone', '=', phone_no)]
            #     _logger.info(f"clause: {clause}")
            #     leads = self.env['crm.lead'].search(clause)
            #     _logger.info(f"leads: {leads}")


            #     clause2 = [('id', '!=', rec.id),('is_won', '!=', True), ('is_lost', '!=', True), ('is_expired', '!=', True)]
            #     _logger.info(f"clause 2: {clause2}")
            #     leads2 = self.env['crm.lead'].search(clause2)
            #     _logger.info(f"leads 2: {leads2}")

            #     if leads:
            #         raise ValidationError("Phone number must be unique")




                # phone_no_crms  = self.env['crm.phone'].search([( ('partner_id','=',rec.id)])
                # for phone_no_crm in phone_no_crms:
                #     _logger.info(f"phone_no_crm: {phone_no_crm}")
                #     added_phone_no = phone_no_crm.phone
                #     partners = self.env['res.partner'].search(
                #         [('phone_no', '=', added_phone_no), ('id', '!=', rec.id),('is_expired','!=',True)])
                #     _logger.info(f"partners: {partners}")
                #     if partners:
                #         leads = self.env['crm.lead'].search(
                #             [('is_won', '!=',True), ('is_lost', '!=',True), ('is_expired', '!=', True), ('partner_id', 'in', partners.ids),])
                #         if leads:
                #             raise  ValidationError("Phone number must be unique2")
                #     partner_phones = self.env['crm.phone'].search(
                #         [('phone', '=', added_phone_no), ('partner_id.is_expired', '!=', True)])
                #     _logger.info(f"partner_phones: {partner_phones}")
                #     if partner_phones:
                #         partner_ids = partner_phones.mapped('partner_id')
                #         _logger.info(f"partner_ids: {partner_ids}")
                #         leads = self.env['crm.lead'].search(
                #             [('is_won', '!=', True), ('is_lost', '!=', True), ('is_expired', '!=', True), ('partner_id', 'in', partner_ids.ids), ])
                #         if leads:
                #             raise ValidationError("Phone number must be unique3")



class CrmLeadInherited(models.Model):
    _inherit = 'crm.lead'
    partner_id = fields.Many2one('res.partner',
                                 domain="[('create_uid', '=', uid),('is_expired', '!=', True)]")
    phone = fields.Char(string='Phone', store = False,selectable = False)
    phone_no = fields.Char(string='Phone')

    phone_code = fields.Char(string='Code', compute="compute_phone_perfix")
    phone_ids = fields.Many2many('crm.phone',
                                 domain="[('create_uid', '=', 'abcd')]",
                                 string="Phone",tracking=True,groupable=False)

    name = fields.Char(string='Name', compute="compute_lead_name", required=False)
    site_ids = fields.Many2many('property.site', required=True, string="site", tracking=True)
    is_creator = fields.Boolean(string="Creator", compute="compute_is_creator")
    has_phone = fields.Boolean(string="Has Phone", compute="compute_is_has_phone")
    is_reserved = fields.Boolean(compute="compute_is_reserved")
    is_lost = fields.Boolean(compute="compute_is_reserved", store=True)
    is_won = fields.Boolean(compute="compute_is_reserved", store=True)
    is_expire_stage = fields.Boolean(compute="compute_is_reserved", store=True)
    reservation_count = fields.Integer( compute="compute_reservation_count")
    country_id = fields.Many2one(
        'res.country',
        string='Country',
        help="Select the country for the phone number.",
        default=lambda self: self.env['res.country'].search([('phone_code', '=', 251)], limit=1)
    )
    is_expired = fields.Boolean(string="is Expired")
    stage_name = fields.Char(related='stage_id.name', store=True)
    customer_name = fields.Char(string='Customer',tracking=True, required=True)

    
    def save_record(self):
        vals = {
            'customer_name': self.customer_name,
            'phone_no': self.phone_no,
            'country_id': self.country_id.id,
            'site_ids': self.site_ids,
        }
        if self.id:
            self.write(vals)
        else:
            self.create(vals)
        
    def fields_get(self, allfields=None, attributes=None):
        res = super().fields_get(allfields, attributes)

        hide_list = ['phone_ids', 'phone_no']
        for field in hide_list:
            if res.get(field):
                res[field]['searchable'] = False  # Prevent filtering
                res[field]['sortable'] = False  # Prevent sorting
                res[field]['groupable'] = False  # Ensure it is NOT available in "Group By"

        return res
    def print_change_history(self):
        for record in self:
            tracking_values = self.env['mail.tracking.value'].search([
                ('mail_message_id', 'in', record.message_ids.ids)
            ])
            messages = self.env['mail.message'].search([
                ('model', '=', 'crm.lead'),  # Current model name
                ('res_id', '=', record.id),  # Current record ID
                ('body', '!=', '')  # Current record ID
            ])

            data_list=[]
            for rec in tracking_values:
                data_list.append({
                    'user': rec.create_uid.name,
                    'fields': rec.field_id.name,
                    'old_value': rec.old_value_char,
                    'new_value': rec.new_value_char,
                    'date': rec.create_date,
                })
            for mas in messages:
                clean_body = re.sub(r'<[^>]*>', '', mas.body)
                data_list.append({
                    'user': mas.create_uid.name,
                    'fields': '',
                    'old_value': '',
                    'new_value': clean_body,
                    'date': mas.date,
                })
            data_list.append({
                'user': self.create_uid.name,
                'fields': '',
                'old_value': '',
                'new_value': "Lead/Opportunity created",
                'date': self.create_date,
            })
            data_list = sorted(data_list, key=lambda x: x['date'], reverse=True) 

            for item in data_list:
                item['date'] = item['date'] + timedelta(hours=3)
            data = {
                'datas': data_list,
                'lead': self.name,
                'customer': self.customer_name,
                'sale_person': self.user_id.name,
            }
            return self.env.ref(
                'ahadubit_crm.crm_lead_report_action_report').report_action(
                self, data=data)

    @api.depends('customer_name','site_ids')
    def compute_lead_name(self):
        for rec in self:
            site_names = '-'.join([site.name for site in rec.site_ids])
            if rec.customer_name:
                rec.name= f'{rec.customer_name}-{site_names}'
            else:
                rec.name ="New"


    # def expire_lead_acton(self):
    #     _logger.info(f"====expire_lead_acton: {self.id}")
    #     duration_in = self.env['ir.config_parameter'].sudo().get_param('ahadubit_property_base.custom_expiration_duration_in')
    #     duration = int(self.env['ir.config_parameter'].sudo().get_param('ahadubit_property_base.custom_expiration_duration', default=0))
    #     if duration_in and duration:
    #         if duration_in == 'hours':
    #             target_date = datetime.now() - timedelta(hours=duration)
    #         elif duration_in == 'days':
    #             target_date = datetime.now() - timedelta(days=duration)
    #         elif duration_in == 'months':
    #             target_date = datetime.now() - timedelta(days=duration * 30)
    #         elif duration_in == 'years':
    #             target_date = datetime.now() - timedelta(days=duration * 365)
    #         else:
    #             target_date = datetime.now()
    #         won_stage_id =self.env['crm.stage'].search([('is_won', '=', True)])
    #         lost_stage_id =self.env['crm.stage'].search([('is_lost_stage', '=', True)])
    #         leads = self.env['crm.lead'].search([('write_date', '<', target_date),('is_expired', '!=', True),('stage_id','not in',[won_stage_id.id,lost_stage_id.id])])
    #         for lead in leads:
    #             lead.write({
    #                 'is_expired':True
    #             })
    #             other_leads = self.env['crm.lead'].search([('id','!=',lead.id),('partner_id', '=', lead.partner_id.id), ('is_expired', '!=', True)])
    #             if not other_leads:
    #                 lead.partner_id.write({
    #                     'is_expired': True
    #                 })
    #             lead.custom_action_set_expired()


    def expire_lead_acton(self):
        """Optimized lead expiration method"""
        _logger.info(f"====expire_lead_acton: {self.id}")
        
        duration_in = self.env['ir.config_parameter'].sudo().get_param(
            'ahadubit_property_base.custom_expiration_duration_in')
        duration = int(self.env['ir.config_parameter'].sudo().get_param(
            'ahadubit_property_base.custom_expiration_duration', default=0))
        
        if not duration_in or not duration:
            return
        
        # Calculate target date
        now = datetime.now()
        if duration_in == 'hours':
            target_date = now - timedelta(hours=duration)
        elif duration_in == 'days':
            target_date = now - timedelta(days=duration)
        elif duration_in == 'months':
            target_date = now - timedelta(days=duration * 30)
        elif duration_in == 'years':
            target_date = now - timedelta(days=duration * 365)
        else:
            target_date = now
        
        # Get stage IDs
        won_stage_id = self.env['crm.stage'].search([('is_won', '=', True)])
        lost_stage_id = self.env['crm.stage'].search([('is_lost_stage', '=', True)])
        
        # Find expired leads
        domain = [
            ('write_date', '<', target_date),
            ('is_expired', '!=', True),
            ('stage_id', 'not in', [won_stage_id.id, lost_stage_id.id])
        ]
        
        expired_leads = self.env['crm.lead'].search(domain)
        
        # Process in batches for better performance
        batch_size = 100
        for i in range(0, len(expired_leads), batch_size):
            batch = expired_leads[i:i + batch_size]
            
            # Mark leads as expired
            batch.write({'is_expired': True})
            
            # Mark partners as expired if no other active leads
            for lead in batch:
                other_leads = self.env['crm.lead'].search([
                    ('id', '!=', lead.id),
                    ('partner_id', '=', lead.partner_id.id),
                    ('is_expired', '!=', True)
                ], limit=1)
                
                if not other_leads:
                    lead.partner_id.is_expired = True
                
                lead.custom_action_set_expired()


    @api.onchange('partner_id')
    def get_default_customer_phone(self):
        for rec in self:
            rec.phone_ids=rec.partner_id.phone_ids
            rec.phone_no=rec.partner_id.phone_no

    @api.onchange('stage_id')
    def compute_is_reserved(self):
        for rec in self:
            rec.is_reserved=rec.stage_id.is_reservation_stage
            rec.is_lost=rec.stage_id.is_lost_stage
            rec.is_expire_stage=rec.stage_id.is_expire_stage
            rec.is_won=rec.stage_id.is_won

    def compute_reservation_count(self):
        for rec in self:
            rec.reservation_count=self.env['property.reservation'].search_count([('crm_lead_id', '=', rec.id)])

    @api.constrains('phone_no','phone_ids')
    def _check_phone_number(self):
        phone_regex = r'^\+?\d{1,15}$'
        for record in self:
            if record.phone_no:
                if not re.match(phone_regex, record.phone_no):
                    raise ValidationError("Invalid phone number format! Please enter a valid phone number.")
                if record.country_id.phone_code == 251:
                    if len(record.phone_no) != 9:
                        raise ValidationError("Invalid phone number format! Please enter a valid phone number.")
                elif len(record.phone_no)<5 or len(record.phone_no) > 14:
                    raise ValidationError("Invalid phone number format! Please enter a valid phone number.")



    @api.depends('phone_ids')
    def compute_is_has_phone(self):
        for rec in self:
            if len(rec.phone_ids)>0:
                rec.has_phone=True
            else:
                rec.has_phone = False


    @api.onchange('country_id')
    def compute_phone_perfix(self):
        for rec in self:
            if rec.country_id:
                rec.phone = False
                rec.phone_code = f"(+{rec.country_id.phone_code})"
            else:
                rec.phone_code=False


    def add_more_phone_list(self):
        if not self.phone_no:
            raise ValidationError("phone is required")
        if not self.country_id:
            raise  ValidationError("country code is required")
        phone_no=f"+{self.country_id.phone_code}{self.phone_no}"
        partner_phones=self.env['crm.phone'].search([('phone','=',phone_no),('partner_id.is_expired','!=',True)])
        if partner_phones:
            partner_ids = partner_phones.mapped('partner_id')
            leads = self.env['crm.lead'].search(
                [('is_won', '!=', True), ('is_lost', '!=', True), ('is_expired', '!=', True), ('partner_id', 'in', partner_ids.ids), ])
            if leads:
                raise ValidationError("This number is Already Registered, Phone number must be unique!")

        result= self.env['crm.phone'].create({
            'phone':phone_no,
            'partner_id':self.partner_id.id,
            'country_id': self.country_id.id,
          })
        
        self.phone_ids = [(4, result.id)]
        self.phone_no = False
        self.country_id = self.env['res.country'].search([('phone_code', '=', 251)], limit=1)

        self.partner_id.phone_ids=[(4, result.id)]
        self.partner_id.phone_no = False
        self.partner_id.country_id = False


    def compute_is_creator(self):
        for rec in self:
            user_id= self.env.user.id
            if rec.create_uid.id!=user_id:
                rec.is_creator=True
            else:
                rec.is_creator=False
            



        
    
    @api.constrains('site_ids')
    def _check_site_no(self):
        site_numbers = int(self.env['ir.config_parameter'].sudo().get_param('ahadubit_property_base.allows_site_no', default=0))
        for record in self:
            if site_numbers < len(record.site_ids):
                raise ValidationError(f"You can select a maximum of {site_numbers} site(s) on one lead.")


    # @api.model
    # def create(self, vals):
    #     name=vals.get('customer_name', [])
    #     partner=self.create_partner(name)
    #     vals['partner_id']=partner.id
    #     phone = vals.get('phone_no', [])
    #     country_id=vals.get('country_id', [])
    #     country=self.env['res.country'].search([('id', '=', country_id)], limit=1)
    #     code=country.phone_code
    #     if phone and phone[0] == "0" and code == 251:
    #         raise ValidationError("Invalid phone number format! Phone number must not start with 0.")
    #     phone_list =vals.get('phone_ids', [])
    #     if not (phone_list or phone):
    #         raise ValidationError("phone is required")
    #     record = super(CrmLeadInherited, self).create(vals)
    #     record.partner_id.phone_no = record.phone_no
    #     record.partner_id.country_id = record.country_id
    #     if record.phone_no:
    #         phone_no = f"+{record.country_id.phone_code}{record.phone_no}"
    #         self.validate_phone(phone_no)
    #         result=self.env['crm.phone'].create({
    #             'phone': phone_no,
    #             'partner_id': record.partner_id.id,
    #             'country_id': record.country_id.id,
    #         })
    #         record.phone_ids = [(4, result.id)]
    #         record.write({
    #             'phone_no':False
    #         })
    #     record.post_message_to_chatter(phone_no)
    #     return record

    @api.model
    def create(self, vals):
        # Validate phone first to avoid creating records if validation fails
        phone = vals.get('phone_no')
        country_id = vals.get('country_id')
        
        if phone and country_id:
            country = self.env['res.country'].browse(country_id)
            code = country.phone_code
            
            # Format validation
            if phone and phone[0] == "0" and code == 251:
                raise ValidationError("Invalid phone number format! Phone number must not start with 0.")
            
            # Uniqueness validation
            formatted_phone = f"+{code}{phone}"
            self._validate_phone_uniqueness(formatted_phone)
        
        # Check if phone is required
        phone_list = vals.get('phone_ids', [])
        if not (phone_list or phone):
            raise ValidationError("Phone is required")
        
        # Create partner
        name = vals.get('customer_name', 'New Customer')
        partner = self._create_partner(name)
        vals['partner_id'] = partner.id
        
        # Create the lead
        record = super(CrmLeadInherited, self).create(vals)
        
        # Create phone record after lead is created
        if phone and country_id:
            formatted_phone = f"+{code}{phone}"
            result = self.env['crm.phone'].create({
                'phone': formatted_phone,
                'partner_id': partner.id,
                'country_id': country_id,
            })
            record.phone_ids = [(4, result.id)]
            record.phone_no = False
        
        # record._post_message_to_chatter(formatted_phone if phone else 'No phone')
        record.post_message_to_chatter(formatted_phone if phone else 'No phone')
        return record

    # def create_partner(self, name):
    #     partner=self.env['res.partner'].create({
    #         'name': name,
    #     })
    #     return  partner

    # def _validate_phone_uniqueness(self, phone):
    #     """Optimized phone uniqueness validation"""
    #     domain = [
    #         ('is_won', '!=', True), 
    #         ('is_lost', '!=', True),
    #         ('is_expired', '!=', True),
    #         ('phone_ids.phone', '=', phone)
    # ]
    
    # # Use search_count for better performance
    #     duplicate_count = self.env['crm.lead'].search_count(domain)
    #     if duplicate_count > 0:
    #         raise ValidationError("This number is already registered in an active lead. Phone number must be unique!")
    
    def _validate_phone_uniqueness(self, phone):
    # Flush pending database operations first
        self.env['crm.lead'].flush_model()
        
        domain = [
            ('is_won', '!=', True), 
            ('is_lost', '!=', True),
            ('is_expired', '!=', True),
            ('phone_ids.phone', '=', phone)
        ]
        
        # Use search instead of search_count for more reliable results
        duplicates = self.env['crm.lead'].search(domain, limit=1)
        if duplicates:
            raise ValidationError("This number is already registered in an active lead. Phone number must be unique!")

    def _create_partner(self, name):
        """Optimized partner creation"""
        return self.env['res.partner'].create({
            'name': name,
        })

   
    def is_phone_required(self):
        _logger.info(f"+++++++++@@@@@@@@@@++********++is_phone_required: {self.phone_ids}")
        for rec in self:
            if len(rec.phone_ids)==1 and rec.phone_ids[0].phone =='duplicated':
                raise ValidationError("phone is required")

    # def read(self, fields=None, load='_classic_read'):
    #     leads = self.env['crm.lead'].search([('customer_name', '=', False)])
    #     for lead in leads:
    #         if lead.partner_id:
    #             lead.customer_name=lead.partner_id.name
    #         else:
    #             lead.customer_name="False"
    #         _logger.info(f"lead.phone_ids: {lead.phone_ids}")
    #         _logger.info(f"lead.phone_ids LEN===: {len(lead.phone_ids)}")

            # _logger.info(f"lead.phone_ids.phone: {lead.phone_ids.phone}")


        return super(CrmLeadInherited, self).read(fields=fields, load=load)

    def validate_phone(self, phone):
        leads = self.env['crm.lead'].search([('id', '!=', self.id),('is_won', '!=', True), ('is_lost', '!=', True),('phone_ids.phone', '=', phone),('is_expired', '!=', True)])
        if leads:
            raise ValidationError("This number is Already Registered, Phone number must be unique!")
    

    def post_message_to_chatter(self,phone_no):
        for record in self:
            record.message_post(
                body=f"Lead/Opportunity created with phone {phone_no}",
                subject="Lead/Opportunity",
                message_type='comment',  # Options: 'comment', 'notification'
                subtype_xmlid='mail.mt_note',  # Default subtype for notes
            )

    # def write(self, vals):
    #     if 'phone_no' in vals and vals['phone_no']:
    #         phone=vals['phone_no']
    #         if 'country_id' in vals:
    #             country_id=vals['country_id']
    #         else:
    #             country_id=self.country_id.id
    #         _logger.info(f"country_id: {country_id}")
    #         country=self.env['res.country'].search([('id', '=', country_id)], limit=1)
    #         code=country.phone_code
    #         _logger.info(f"code===: {code}")

    #         if phone and phone[0] == "0" and code == 251:
    #             raise ValidationError("Invalid phone number format! Phone number must not start with 0.")
    #         self.partner_id.phone_no =phone
    #         country_code=self.country_id.phone_code
    #         if 'country_id' in vals and vals['country_id']:
    #             country_id=vals['country_id']
    #             country=self.env['res.country'].search([('id', '=', country_id)], limit=1)
    #             country_code=country.phone_code
    #         phone_no = f"+{country_code}{self.partner_id.phone_no}"
    #         self.validate_phone(phone_no)
    #         result = self.env['crm.phone'].create({
    #             'phone': phone_no,
    #             'partner_id': self.partner_id.id,
    #             'country_id': self.country_id.id,
    #         })
    #         self.phone_ids = [(4, result.id)]
    #         vals['phone_no']=False
    #     if 'country_id' in vals:
    #         self.partner_id.country_id =vals['country_id']
    #     record = super(CrmLeadInherited, self).write(vals)
    #     if self.partner_id and self.customer_name!=self.partner_id.name:
    #         self.partner_id.write({
    #             'name':self.customer_name
    #         })

    #     for rec in self:
    #         if not rec.phone_no and not rec.has_phone:
    #             raise ValidationError("phone is required")
    #     return record

    def write(self, vals):
        # Validate phone before any writes
        if 'phone_no' in vals and vals['phone_no']:
            phone = vals['phone_no']
            country_id = vals.get('country_id', self.country_id.id)
            country = self.env['res.country'].browse(country_id)
            
            # Format validation
            if phone and phone[0] == "0" and country.phone_code == 251:
                raise ValidationError("Invalid phone number format! Phone number must not start with 0.")
            
            # Uniqueness validation
            formatted_phone = f"+{country.phone_code}{phone}"
            self._validate_phone_uniqueness(formatted_phone)
            
            # Create phone record
            result = self.env['crm.phone'].create({
                'phone': formatted_phone,
                'partner_id': self.partner_id.id,
                'country_id': country_id,
            })
            self.phone_ids = [(4, result.id)]
            vals['phone_no'] = False
        
        # Update partner name if changed
        if 'customer_name' in vals and self.partner_id:
            self.partner_id.name = vals['customer_name']
        
        # Perform the write operation
        result = super(CrmLeadInherited, self).write(vals)
        
        # Check phone requirement
        for rec in self:
            if not rec.phone_no and not rec.has_phone:
                raise ValidationError("Phone is required")
        
        return result

    @api.depends('partner_id')
    def _compute_name(self):
        for lead in self:
            if not lead.name and lead.partner_id and lead.partner_id.name:
                lead.name = lead.partner_id.name


    def action_reserve(self):
        for rec in self:
            rec.is_phone_required()
            # self.action_set_reserved()
            return {
                'type': 'ir.actions.act_window',
                'name': 'Reservation',
                'res_model': 'property.reservation',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_partner_id': rec.partner_id.id,
                    'default_crm_lead_id': rec.id,
                    'default_property_id_domain':f"[('state', 'in', ['available']),('site', 'in', {rec.site_ids.ids})]"
                }
            }

    def action_set_reserved(self):
        for rec in self:
            reservation_stages = self.env['crm.stage'].search([('is_reservation_stage', '=', True)], limit=1)
            if reservation_stages:
                rec.stage_id=reservation_stages.id


    def custom_action_set_expired(self):
        for rec in self:
            lost_stages = self.env['crm.stage'].search([('is_expire_stage', '=', True)], limit=1)
            if lost_stages:
                rec.stage_id=lost_stages.id



    def action_reserve_list(self):
        for rec in self:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Reservation',
                'res_model': 'property.reservation',
                'domain': [('crm_lead_id', '=', rec.id)],
                'view_mode': 'kanban,tree,form',
                'target': 'current'
            }



class PropertyReservationHistoryInherited(models.Model):
    _inherit = 'property.reservation'
    crm_lead_id= fields.Many2one("crm.lead")
    property_id_domain=fields.Char(compute='onchange_crm_lead_id', default="[('state', 'in', ['available'])]")




    @api.depends('crm_lead_id')
    def onchange_crm_lead_id(self):
        for rec in self:
            if self.crm_lead_id:
                self.property_id_domain= f"[('state', 'in', ['available']),('site', 'in', {self.crm_lead_id.site_ids.ids})]"
            else:
                self.property_id_domain = "[('state', 'in', ['available'])]"

    @api.model
    def create(self, vals):
        res = super(PropertyReservationHistoryInherited, self).create(vals)
        return res
    
    @api.model
    def write(self, vals):
        res = super(PropertyReservationHistoryInherited, self).write(vals)
        if self.status == 'requested':
            self.crm_lead_id.action_set_reserved()
        elif self.status == 'draft' and self.crm_lead_id.is_reserved:
            stage=self.env['crm.stage'].search([('name', 'ilike', "Follow Up")], limit=1)
            if stage:
                self.crm_lead_id.write({'stage_id': stage.id})
        return res


class PropertyReservationInherited(models.TransientModel):
    _inherit = 'cancellation.reason.wizard'

    def action_cancel_reservation(self):
        if self.reservation_id.crm_lead_id:
            stage=self.env['crm.stage'].search([('name', 'ilike', "Follow Up")], limit=1)
            if stage:
                self.reservation_id.crm_lead_id.write({
                    'stage_id': stage.id,
                })
        super(PropertyReservationInherited, self).action_cancel_reservation()


    def check_expired_reservation(self):
        if self.reservation_id.crm_lead_id:
            stage=self.env['crm.stage'].search([('name', 'ilike', "Follow Up")], limit=1)
            if stage:
                self.reservation_id.crm_lead_id.write({
                    'stage_id': stage.id,
                })
        super(PropertyReservationInherited, self).check_expired_reservation()


class PropertySale(models.Model):
    _inherit = 'property.sale'
    _description = 'Property Sale'

    def action_confirm(self):
        """Confirm the sale order and Change necessary fields"""
        self.ensure_one()
        if self.partner_id.blacklisted:
            raise ValidationError(
                _('The Customer %r is Blacklisted.', self.partner_id.name))
        self.state = 'confirm'
        self.property_id.state = 'sold'
        self.reservation_id.status = 'sold'
        self.property_id.sale_id = self.id
        
        # Update CRM lead to won stage
        if self.reservation_id.crm_lead_id:
            won_stages = self.env['crm.stage'].search([('is_won', '=', True)], limit=1)
            if won_stages:
                self.reservation_id.crm_lead_id.write({
                    'stage_id': won_stages.id
                })
        
        # Update temer.lead to won status
        if self.reservation_id.temer_lead_ids:
            self.reservation_id.temer_lead_ids.write({
                'state': 'won'
            })

    def action_cancel_sale(self):
        self.ensure_one()
        # Update CRM lead to follow up stage
        if self.reservation_id.crm_lead_id:
            follow_up_stages = self.env['crm.stage'].search([('name', 'ilike', "Follow Up")], limit=1)
            if follow_up_stages:
                self.reservation_id.crm_lead_id.write({
                    'stage_id': follow_up_stages.id
                })
        
        # Update temer.lead to follow_up status (revert to follow up)
        if self.reservation_id.temer_lead_ids:
            self.reservation_id.temer_lead_ids.write({
                'state': 'follow_up'
            })

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