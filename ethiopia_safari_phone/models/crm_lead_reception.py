# -*- coding: utf-8 -*-

import phonenumbers
from odoo import api, models, _
from odoo.exceptions import ValidationError

from .crm_lead_call_center import _is_valid_ethiopia_mobile


class CrmLeadReceptionSafari(models.Model):
    _inherit = 'crm.reception'

    @api.onchange('new_phone')
    def _onchange_validate_phone(self):
        for record in self:
            if record.new_phone and record.country_id and record.country_id.code:
                if record.country_id.code.upper() == 'ET' and _is_valid_ethiopia_mobile(record.new_phone):
                    continue  # Safari (+2517) or Ethio Telecom (+2519) accepted
                try:
                    parsed = phonenumbers.parse(record.new_phone.strip(), record.country_id.code)
                    if not phonenumbers.is_valid_number(parsed):
                        raise ValidationError(_('Invalid phone number for selected country'))
                except Exception as e:
                    raise ValidationError(_('Invalid phone number format: %s') % str(e))
