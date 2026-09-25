from odoo import api, models


class CollectionInstallmentPayment(models.Model):
    _inherit = 'collection.installment.payment'

    def _trigger_thank_you_sms(self):
        """Send thank-you SMS when a payment completes and the installment is fully paid."""
        if self.env.context.get('skip_thank_you_sms'):
            return

        template = self.env['collection.sms.template'].search(
            [('template_type', '=', 'thank_you')],
            limit=1,
        )
        if not template:
            return

        log_model = self.env['collection.sms.log'].sudo()

        for payment in self:
            if payment.status != 'paid':
                continue

            installment = payment.installment_id
            if not installment:
                continue

            installment.invalidate_recordset(['amount_residual', 'state'])
            if installment.amount_residual > 0:
                continue

            already_sent = log_model.search_count([
                ('installment_id', '=', installment.id),
                ('message_stage', '=', 'thank_you'),
                ('status', '=', 'sent'),
            ])
            if already_sent:
                continue

            installment._send_sms_from_template(installment, template)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.filtered(lambda p: p.status == 'paid')._trigger_thank_you_sms()
        return records

    def write(self, vals):
        previously_unpaid = self.filtered(lambda p: p.status != 'paid')
        res = super().write(vals)
        newly_paid = previously_unpaid.filtered(lambda p: p.status == 'paid')
        if newly_paid:
            newly_paid._trigger_thank_you_sms()
        return res
