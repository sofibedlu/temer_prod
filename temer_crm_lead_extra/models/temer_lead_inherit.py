# -*- coding: utf-8 -*-
import re
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class TemerLead(models.Model):
    _inherit = 'temer.lead'

    previously_contacted = fields.Boolean(
        string='Previously Contacted by Temer Team',
        default=False,
        tracking=True,
    )

    for_whom = fields.Char(
        string='For Whom to Buy',
        tracking=True,
    )

    client_response = fields.Text(
        string='Client Response',
        tracking=True,
    )

    @api.constrains('phone_no')
    def _validate_phone_input(self):
        """Override parent constraint to allow * as masked-digit placeholder."""
        for record in self:
            if not record.phone_no:
                continue

            if not re.match(r'^[\d*]+$', record.phone_no):
                raise ValidationError(_(
                    "Phone number should contain only digits or * characters (e.g. 910*****)."
                ))

            if record.country_id and record.country_id.phone_code == 251:
                clean = record.phone_no.replace('*', '')
                if clean and clean[0] == '0':
                    raise ValidationError(_("Ethiopian phone numbers must not start with 0."))
                if len(record.phone_no) != 9:
                    raise ValidationError(_("Ethiopian phone numbers must be exactly 9 characters."))
