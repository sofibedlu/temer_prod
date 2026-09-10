import base64
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import Markup

class CollectionSendEmailWizard(models.TransientModel):
    _name = 'collection.send.email.wizard'
    _description = 'Send Collection Email'

    collection_id = fields.Many2one('collection.order', string='Collection', required=True)
    installment_id = fields.Many2one(
        'collection.installment', 
        string='Installment', 
        required=True, 
        domain="[('collection_id', '=', collection_id)]",
        help="Select the installment related to this letter/email."
    )
    
    email_to = fields.Char(string='To (Email)', required=True)
    template_id = fields.Many2one('mail.template', string='Email Template', domain="[('model', '=', 'collection.installment')]")
    subject = fields.Char(string='Subject', required=True)
    body = fields.Html(string='Body', sanitize_style=True)
    
    letter_type = fields.Selection([
        ('payment_request', 'Payment Request Letter'),
        ('warning', 'Warning Letter'),
        ('termination', 'Termination Letter')
    ], string='Letter to Attach', required=False, help="Select a letter template to generate and attach to the email.")
    
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')

        # Case 1: Opened from Collection Order
        if active_model == 'collection.order' and active_id:
            collection = self.env['collection.order'].browse(active_id)
            res['collection_id'] = collection.id
            res['email_to'] = collection.partner_id.email or ''
            
        # Case 2: Opened from Installment (Legacy/Direct)
        elif active_model == 'collection.installment' and active_id:
            installment = self.env['collection.installment'].browse(active_id)
            res['collection_id'] = installment.collection_id.id
            res['installment_id'] = installment.id
            res['email_to'] = installment.partner_id.email or ''
            
        return res

    @api.onchange('template_id', 'installment_id')
    def _onchange_template_id(self):
        """ Render template based on the selected installment """
        if self.template_id and self.installment_id:
            self.subject = self.template_id._render_field('subject', self.installment_id.ids)[self.installment_id.id]
            self.body = self.template_id._render_field('body_html', self.installment_id.ids)[self.installment_id.id]

    def action_send_email(self):
        self.ensure_one()
        report_ref = False
        filename = "Letter.pdf"
        
        final_attachment_ids = list(self.attachment_ids.ids)
        if self.letter_type:
            if self.letter_type == 'payment_request':
                report_ref = self.env.ref('collection_management.action_report_collection_letter', raise_if_not_found=False)
                filename = f"Payment_Request_{self.installment_id.name}.pdf"
            elif self.letter_type == 'warning':
                report_ref = self.env.ref('collection_management.action_report_warning_letter', raise_if_not_found=False)
                filename = f"Warning_Letter_{self.installment_id.name}.pdf"
            elif self.letter_type == 'termination':
                report_ref = self.env.ref('collection_management.action_report_termination_letter', raise_if_not_found=False)
                filename = f"Termination_Letter_{self.installment_id.name}.pdf"

            if report_ref:
                pdf_content, _ = self.env['ir.actions.report']._render_qweb_pdf(report_ref, self.installment_id.ids)
                attachment = self.env['ir.attachment'].sudo().create({
                    'name': filename,
                    'type': 'binary',
                    'datas': base64.b64encode(pdf_content),
                    'res_model': 'collection.installment',
                    'res_id': self.installment_id.id,
                    'mimetype': 'application/pdf',
                })
                final_attachment_ids.append(attachment.id)

        # Send Email
        mail_values = {
            'subject': self.subject,
            'body_html': self.body,
            'email_to': self.email_to,
            'attachment_ids': [(6, 0, final_attachment_ids)],
            'model': 'collection.installment',
            'res_id': self.installment_id.id,
        }
        mail = self.env['mail.mail'].sudo().create(mail_values)
        mail.send()
        
        self.collection_id.sudo().message_post(
            body=Markup(f"<b>Email sent regarding {self.installment_id.name}</b><br/>To: {self.email_to}"),
            subject=self.subject,
            attachment_ids=final_attachment_ids,
        )

        return {'type': 'ir.actions.act_window_close'}