# -*- coding: utf-8 -*-
##############################################################################
#    Ahadubit Technologies
#    Copyright (C) 2024-TODAY Ahadubit Technologies(<https://ahadubit.com>).
#    Author: Ahadubit Technologies (<https://ahadubit.com>)
##############################################################################

from odoo import _, api, exceptions, fields, models


class MailActivityTypeInherited(models.Model):
    _inherit = 'mail.activity.type'

    show_on_crm =fields.Boolean(string="Show on CRM")

class MailThreadInherited(models.AbstractModel):
    _inherit =  'mail.thread'
    def _message_compute_author(self, author_id=None, email_from=None, raise_on_email=True):
        """ Tool method computing author information for messages. Purpose is
        to ensure maximum coherence between author / current user / email_from
        when sending emails.

        :param raise_on_email: if email_from is not found, raise an UserError

        :return tuple: res.partner ID (may be False or None), email_from
        """
        if author_id is None:
            if email_from:
                author = self._mail_find_partner_from_emails([email_from])[0]
            else:
                author = self.env.user.partner_id
                email_from = author.email_formatted
            author_id = author.id

        if email_from is None:
            if author_id:
                author = self.env['res.partner'].browse(author_id)
                email_from = author.email_formatted

        # superuser mode without author email -> probably public user; anyway we don't want to crash
        if not email_from and raise_on_email and not self.env.su:
            return author_id, "defualt@gmail.com"
            raise exceptions.UserError(_("Unable to send message, please configure the sender's email address."))

        return author_id, email_from


class MailActivityInherited(models.TransientModel):
    _inherit = 'mail.activity.schedule'
    activity_type_id =fields.Many2one('mail.activity.type',  domain="[('show_on_crm', '=', True)]")

class CustomMailActivity(models.Model):
    _inherit = 'mail.activity'

    @api.model
    def create(self, vals):
        model_id = vals.get('res_model_id')
        res_id = vals.get('res_id')
        model = self.env['ir.model'].search([('id', '=', model_id)], limit=1)
        if model and model.model == 'crm.lead':
            stage = self.env['crm.stage'].search([], order="sequence asc", limit=1)
            lead = self.env['crm.lead'].search([('id', '=', res_id)], limit=1)
            if lead:
                current_datetime = fields.Datetime.now()
                lead.write({
                    'write_date':current_datetime
                })
            if lead.stage_id.id==stage.id:
                follow_up_stage = self.env['crm.stage'].search([('name', 'ilike','Follow Up')],limit=1)
                if follow_up_stage:
                    lead.write({
                        'stage_id':follow_up_stage.id
                    })
        record = super(CustomMailActivity, self).create(vals)
        return record


class CrmLeadLostInherited(models.TransientModel):
    _inherit = 'crm.lead.lost'

    def action_lost_reason_apply(self):
        for rec in self.lead_ids:
            reservation_stages = self.env['crm.stage'].search([('is_lost_stage', '=', True)], limit=1)
            if reservation_stages:
                rec.stage_id = reservation_stages.id
            super(CrmLeadLostInherited, self).action_lost_reason_apply()
            rec.active=True




