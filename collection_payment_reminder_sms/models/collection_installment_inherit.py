from odoo import models, fields, api
import requests
import logging
from odoo.tools import html2plaintext

_logger = logging.getLogger(__name__)

try:
    from ethioqen.calendar_conversion import convert_gregorian_to_ethiopian
except ImportError:
    _logger.warning("The 'ethioqen' library is missing.")

class CollectionInstallment(models.Model):
    _inherit = 'collection.installment'

    reminder_stage = fields.Selection([
        ('0', 'No Reminders Sent'),
        ('1', 'First Reminder Sent'),
        ('2', 'Second Reminder Sent'),
        ('3', 'Third Reminder Sent')
    ], string="Reminder Stage", default='0', readonly=True, copy=False)

    # 🌟 Safety Guard: Permanently tracks if the thank-you SMS was already fired
    thank_you_sms_sent = fields.Boolean(
        string="Thank You SMS Sent", 
        default=False, 
        copy=False, 
        readonly=True
    )

    def write(self, vals):
        if self.env.context.get('skip_thank_you_sms'):
            return super(CollectionInstallment, self).write(vals)

        # 1. 🌟 CAPTURE PRE-WRITE STATE:
        # Only consider installments that are currently NOT paid
        unpaid_installments = self.filtered(lambda r: r.state != 'paid' and not r.thank_you_sms_sent)

        # 2. Execute standard write
        res = super(CollectionInstallment, self).write(vals)

        # 3. 🌟 CAPTURE POST-WRITE TRANSITION:
        # Which of those previously UNPAID installments have NOW transitioned to 'paid'?
        newly_paid_installments = unpaid_installments.filtered(lambda r: r.state == 'paid')

        if newly_paid_installments:
            template = self.env['collection.sms.template'].search([('template_type', '=', 'thank_you')], limit=1)
            
            if template:
                for rec in newly_paid_installments:
                    # Double-check database log just in case
                    already_sent = self.env['collection.sms.log'].sudo().search_count([
                        ('installment_id', '=', rec.id),
                        ('message_stage', '=', 'thank_you'),
                        ('status', 'in', ['sent', 'delivered'])
                    ])

                    if not already_sent:
                        # Send SMS using context to prevent recursion
                        success = rec.with_context(skip_thank_you_sms=True)._send_sms_from_template(rec, template)
                        if success:
                            # Lock the installment so it can never trigger again
                            rec.with_context(skip_thank_you_sms=True).write({'thank_you_sms_sent': True})

        return res


    def _send_sms_api(self, mobile, message):
        """ Send SMS via AfroMessage API """
        if not mobile:
            return False, "No mobile number provided"
        try:
            mobile = mobile.replace(' ', '').replace('-', '').replace('+', '')     
            token = 'eyJhbGciOiJIUzI1NiJ9.eyJpZGVudGlmaWVyIjoiQ2JsdHB6dHRFNkNaR1BjZ2VHWjRidThDUzMyOXczNWMiLCJleHAiOjE5Mjk4NzE1NjYsImlhdCI6MTc3MjEwNTE2NiwianRpIjoiNDZiZjhiYWMtNjhiOS00NmMzLWFjZTctMGZkNDMyNTM5YjMxIn0.3XK4_j0brTi7DkzE37YNVponFjzXyJo5w0a7TAr-7_Y'
            sender = 'Temer RE'
            from_identifier = 'e80ad9d8-adf3-463f-80f4-7c4b39f7f164'
            
            session = requests.Session()
            base_url = 'https://api.afromessage.com/api/send'
            headers = {'Authorization': 'Bearer ' + token}
            
            url = f"{base_url}?from={from_identifier}&sender={sender}&to={mobile}&message={message}"
            result = session.get(url, headers=headers)
            
            if result.status_code == 200:
                json_response = result.json()
                if json_response.get('acknowledge') == 'success':
                    return True, "Success"
                else:
                    return False, f"API Error: {json_response}"
            else:
                return False, f"HTTP Error: {result.status_code}"
                
        except Exception as e:
            return False, str(e)

    def _send_sms_from_template(self, installment, template):
        """ Helper method to format text and trigger API """

        site = installment.collection_id.property_id.site
        mapping = self.env['site.company.mapping.line'].sudo().search([('site_id', '=', site.id)], limit=1)
        company = mapping.company_id if mapping else False

        company_name = company.name if company and company.name else self.env.company.name

        company_name_amharic = company.name_amharic if company and company.name_amharic else company_name

        amount_str = "{:,.2f}".format(installment.amount_residual or installment.amount_total)
        due_date_str = str(installment.due_date) if installment.due_date else "N/A"

        due_date_ec_str = "N/A"
        if installment.due_date:
            try:
                y, m, d = convert_gregorian_to_ethiopian(installment.due_date.year, installment.due_date.month, installment.due_date.day)
                due_date_ec_str = f"{d:02d}/{m:02d}/{y}"
            except Exception:
                pass

        # 🌟 NEW: Dynamic Customer Name Logic
        b_text = installment.collection_id.buyers_name_text
        if b_text and b_text.strip() != 'No buyers found':
            customer_name = b_text
        else:
            customer_name = installment.partner_id.name or "Customer"


        # Inject the variables into the HTML template
        raw_html_message = template.body.format(
            customer_name=customer_name,  # 🌟 Updated Variable
            company_name=company_name,
            company_name_amharic=company_name_amharic,
            amount=amount_str,
            due_date=due_date_str,
            due_date_ec=due_date_ec_str
        )

        # This strips out <p>, <b>, <br> and translates them into clean SMS line breaks.
        clean_message_text = html2plaintext(raw_html_message)

        phone = installment.partner_id.mobile or installment.partner_id.phone
        success, response_msg = self._send_sms_api(phone, clean_message_text)
        status = 'sent' if success else 'failed'

        # Log History
        self.env['collection.sms.log'].create({
            'installment_id': installment.id,
            'message_body': clean_message_text,
            'status': status,
            'error_message': response_msg if not success else False,
            'sender_id': self.env.user.id,
            'message_stage': template.template_type
        })
        return success

    @api.model
    def _cron_send_automated_reminders(self):
        """ 
        Runs daily. Automatically sends 2nd and 3rd reminders if 1st was sent.
        """
        today = fields.Date.context_today(self)

        # SECOND REMINDER (Due Today)
        second_template = self.env['collection.sms.template'].search([('template_type', '=', 'second')], limit=1)
        if second_template:
            installments_for_second = self.search([
                ('reminder_stage', '=', '1'),
                ('state', 'not in', ['paid', 'pending']),
                ('due_date', '=', today),
                ('collection_id.state', '=', 'active')
            ])
            for inst in installments_for_second:
                if inst._send_sms_from_template(inst, second_template):
                    inst.write({'reminder_stage': '2'})

        # THIRD REMINDER (Overdue)
        third_template = self.env['collection.sms.template'].search([('template_type', '=', 'third')], limit=1)
        if third_template:
            installments_for_third = self.search([
                ('reminder_stage', '=', '2'),
                ('state', 'not in', ['paid', 'pending']),
                ('due_date', '<', today),
                ('collection_id.state', '=', 'active')
            ])
            for inst in installments_for_third:
                if inst._send_sms_from_template(inst, third_template):
                    inst.write({'reminder_stage': '3'})