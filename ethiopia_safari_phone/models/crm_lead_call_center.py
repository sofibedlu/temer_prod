# -*- coding: utf-8 -*-

import phonenumbers
from odoo import api, models, _
from odoo.exceptions import ValidationError


def _is_valid_ethiopia_mobile(phone_str):
    """Ethiopia: 9 digits starting with 7 (Safari) or 9 (Ethio Telecom). Accepts +251..., 251..., 07..., 09..."""
    if not phone_str:
        return False
    s = phone_str.strip().replace(' ', '')
    if s.startswith('+251'):
        s = s[4:]
    elif s.startswith('251'):
        s = s[3:]
    if s.startswith('0'):
        s = s[1:]
    return len(s) == 9 and s.isdigit() and s[0] in ('7', '9')


class CrmLeadCallCenterSafari(models.Model):
    _inherit = 'crm.callcenter'

    @api.onchange('new_phone')
    def _onchange_validate_phone(self):
        for record in self:
            if record.new_phone and record.country_id and record.country_id.code:
                if record.country_id.code.upper() == 'ET' and _is_valid_ethiopia_mobile(record.new_phone):
                    return  # Safari (+2517) or Ethio Telecom (+2519) accepted
                try:
                    parsed = phonenumbers.parse(record.new_phone.strip(), record.country_id.code)
                    if not phonenumbers.is_valid_number(parsed):
                        raise ValidationError(_('Invalid phone number for selected country'))
                except Exception as e:
                    raise ValidationError(_('Invalid phone number format: %s') % str(e))
