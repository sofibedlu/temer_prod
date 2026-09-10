# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields
import re
import html
from urllib.parse import quote_plus

try:
    import html2text
except Exception:
    html2text = None


class Message(models.TransientModel):

    _inherit = 'mail.compose.message'

    is_wp = fields.Boolean('Is whatsapp ?')

    def action_send_wp(self):
        # Convert HTML body to plain text. Prefer html2text if available, otherwise fall back to a simple stripper.
        if html2text:
            text = html2text.html2text(self.body or '')
        else:
            # naive fallback: remove tags and unescape HTML entities
            text = re.sub(r'<[^>]+>', '', (self.body or ''))
            text = html.unescape(text)

        phone = False
        if self.partner_ids:
            phone = getattr(self.partner_ids[0], 'mobile', False)

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        if self.attachment_ids:
            text += '%0A%0A Other Attachments :'
            for attachment in self.attachment_ids:
                attachment.generate_access_token()
                text += '%0A%0A'
                text += base_url + '/web/content/ir.attachment/' \
                    + str(attachment.id) + '/datas?access_token=' \
                    + attachment.access_token
        context = dict(self._context or {})
        active_id = context.get('active_id')
        active_model = context.get('active_model')

        if text and active_id and active_model:
            # prepare message (strip markdown-like markers and keep plain text for messages)
            message_plain = str(text).replace('*', '').replace('_', '')
            # message will be included in a URL, so URL-encode it when needed
            message_encoded = quote_plus(message_plain)

            if active_model == 'sale.order' and self.env['sale.order'].browse(active_id).company_id.display_in_message:
                self.env['mail.message'].create({
                    'partner_ids': [(6, 0, self.partner_ids.ids)],
                    'model': 'sale.order',
                    'res_id': active_id,
                    'author_id': self.env.user.partner_id.id,
                    'body': message_plain or False,
                    'message_type': 'comment',
                })

            if active_model == 'purchase.order' and self.env['purchase.order'].browse(active_id).company_id.purchase_display_in_message:
                self.env['mail.message'].create({
                    'partner_ids': [(6, 0, self.partner_ids.ids)],
                    'model': 'purchase.order',
                    'res_id': active_id,
                    'author_id': self.env.user.partner_id.id,
                    'body': message_plain or False,
                    'message_type': 'comment',
                })

            if (active_model == 'account.move' and self.env['account.move'].browse(active_id).company_id.invoice_display_in_message) \
               or (active_model == 'account.payment' and self.env['account.payment'].browse(active_id).company_id.invoice_display_in_message):
                self.env['mail.message'].create({
                    'partner_ids': [(6, 0, self.partner_ids.ids)],
                    'model': active_model,
                    'res_id': active_id,
                    'author_id': self.env.user.partner_id.id,
                    'body': message_plain or False,
                    'message_type': 'comment',
                })

            if active_model == 'stock.picking' and self.env['stock.picking'].browse(active_id).company_id.inventory_display_in_message:
                self.env['mail.message'].create({
                    'partner_ids': [(6, 0, self.partner_ids.ids)],
                    'model': 'stock.picking',
                    'res_id': active_id,
                    'author_id': self.env.user.partner_id.id,
                    'body': message_plain or False,
                    'message_type': 'comment',
                })

            if active_model == 'hr.payslip':
                phone = self.env['hr.payslip'].browse(active_id).employee_id.mobile

        # final fallback: if phone not determined yet, try to get from partner_ids
        if not phone and self.partner_ids:
            phone = getattr(self.partner_ids[0], 'mobile', '')

        return {
            'type': 'ir.actions.act_url',
            'url': f'https://web.whatsapp.com/send?l=&phone={phone}&text={quote_plus(text)}',
            'target': 'new'
        }
