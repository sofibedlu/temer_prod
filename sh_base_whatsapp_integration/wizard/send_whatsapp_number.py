# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from urllib.parse import quote_plus


class ShSendWhatsappNumber(models.TransientModel):
    _name = "sh.base.send.whatsapp.number.wizard"
    _description = "Send whatsapp message wizard"

    partner_ids = fields.Many2one("res.partner", string="Recipients")
    whatsapp_mobile = fields.Char(string="Whatsapp Number", required=True)
    message = fields.Text("Message", required=True)

    @api.onchange('partner_ids')
    def onchange_partner(self):
        if self.partner_ids:
            self.whatsapp_mobile = self.partner_ids.mobile

    def action_send_whatsapp_number(self):
        if self.whatsapp_mobile and self.message:
            for rec in self:
                # if rec.partner_ids:
                if not rec.message:
                    raise UserError(_("Please enter a message to send."))
                phone = rec.whatsapp_mobile
                msg = quote_plus(rec.message)
                return {
                    'type': 'ir.actions.act_url',
                    'url': f"https://web.whatsapp.com/send?l=&phone={phone}&text={msg}",
                    'target': 'new',
                    'res_id': self.id,
                }
        else:
            raise UserError(_("Please select recipients or add a Whatsapp number."))
