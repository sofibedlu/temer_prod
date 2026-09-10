# -*- coding: utf-8 -*-
import re
from odoo import models, _
from odoo.exceptions import ValidationError


class TemerPhone(models.Model):
    _inherit = 'temer.phone'

    def _validate_phone_format(self, phone, country):
        """Override to allow * as a masked-digit placeholder in phone numbers."""
        phone_regex = r'^\+[\d*]{1,15}$'

        if not re.match(phone_regex, phone):
            raise ValidationError(_(
                "Invalid phone number format! Use +[country code][number]. "
                "* is allowed as a placeholder for masked digits (e.g. +251910*****)."
            ))

        if country.phone_code == 251:
            if len(phone) != 13:
                raise ValidationError(_(
                    "Ethiopian phone numbers must be exactly 9 digits/characters after +251."
                ))
            local_number = phone[4:]
            clean = local_number.replace('*', '')
            if clean and clean[0] == '0':
                raise ValidationError(_(
                    "Ethiopian phone numbers must not start with 0 after the country code."
                ))
        else:
            local_length = len(phone) - len(f"+{country.phone_code}")
            if local_length < 5 or local_length > 14:
                raise ValidationError(_(
                    "Invalid phone number length for %s. Local part should be 5–14 characters."
                ) % country.name)
