# -*- coding: utf-8 -*-
from odoo import models, api, _


class PropertyReservationPaymentAudit(models.Model):
    _inherit = 'property.reservation.payment'

    def _log_property_bank_change(self, prop, old_bank, new_bank):
        if not prop or old_bank == new_bank:
            return
        prop._log_property_chatter(
            body=_('Payment bank: %s → %s') % (old_bank or '-', new_bank or '-'),
        )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.bank_id and rec.property_id:
                rec._log_property_bank_change(
                    rec.property_id, '', rec.bank_id.display_name,
                )
        return records

    def write(self, vals):
        bank_changes = []
        if 'bank_id' in vals and not self.env.context.get('property_audit_log_skip'):
            for rec in self:
                if rec.property_id:
                    old_name = rec.bank_id.display_name if rec.bank_id else ''
                    new_bank = (
                        self.env['bank.configuration'].browse(vals['bank_id'])
                        if vals.get('bank_id') else False
                    )
                    new_name = new_bank.display_name if new_bank else ''
                    if old_name != new_name:
                        bank_changes.append((rec, rec.property_id, old_name, new_name))
        res = super().write(vals)
        for payment, prop, old_name, new_name in bank_changes:
            payment._log_property_bank_change(prop, old_name, new_name)
        return res
