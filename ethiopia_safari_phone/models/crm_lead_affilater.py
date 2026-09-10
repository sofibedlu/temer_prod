# -*- coding: utf-8 -*-

import phonenumbers
from odoo import api, models, _
from odoo.exceptions import ValidationError

from .crm_lead_call_center import _is_valid_ethiopia_mobile


class CrmLeadAffilaterSafari(models.Model):
    _inherit = 'crm.affilater'

    @api.onchange('phone_no')
    def _onchange_validate_phone(self):
        for record in self:
            if record.phone_no and record.country_id and record.country_id.code:
                if record.country_id.code.upper() == 'ET' and _is_valid_ethiopia_mobile(record.phone_no):
                    return  # Safari (+2517) or Ethio Telecom (+2519) accepted
                try:
                    parsed = phonenumbers.parse(record.phone_no.strip(), record.country_id.code)
                    if not phonenumbers.is_valid_number(parsed):
                        raise ValidationError(_('Invalid phone number for selected country'))
                    formatted = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
                    record.phone_no = formatted
                except Exception as e:
                    raise ValidationError(_('Invalid phone number format: %s') % str(e))
