# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, _
from odoo.exceptions import UserError
from urllib.parse import quote_plus


class ShSendWhatsappMessage(models.TransientModel):
    _name = "sh.base.send.whatsapp.message.wizard"
    _description = "Send whatsapp message wizard"

    partner_ids = fields.Many2many("res.partner", string="Recipients")
    message = fields.Text("Message", required=True)
    attachment_ids = fields.Many2many(comodel_name="ir.attachment",
                                      relation="rel_sh_send_whatsapp_msg_ir_attachments",
                                      string="Attachments")

    def action_send_whatsapp_message(self):
        if self:
            for rec in self:
                for partner in rec.partner_ids:
                    # Ensure message is URL-encoded to avoid injection and formatting issues
                    if not rec.message:
                        raise UserError(_("Please enter a message to send."))

                    if partner.mobile:
                        phone = partner.mobile
                        msg = quote_plus(rec.message)
                        return {
                            'type': 'ir.actions.act_url',
                            'url': f"https://web.whatsapp.com/send?l=&phone={phone}&text={msg}",
                            'target': 'new',
                            'res_id': rec.id,
                        }
                    else:
                        raise UserError(_("Partner Mobile Number does not exist."))
