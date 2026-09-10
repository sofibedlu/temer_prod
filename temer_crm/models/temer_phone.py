# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re
import logging

_logger = logging.getLogger(__name__)

class TemerPhone(models.Model):
    _name = 'temer.phone'
    _description = 'Temer Phone Numbers'
    _rec_name = 'phone'
    _sql_constraints = [
        ('phone_unique', 'UNIQUE(phone)', 'Phone number must be unique across the system!'),
    ]

    country_id = fields.Many2one(
        'res.country',
        string='Country',
        required=True,
        help="Select the country for the phone number.",
        default=lambda self: self.env['res.country'].search([('phone_code', '=', 251)], limit=1)
    )
    phone = fields.Char(
        string='Phone Number',
        required=True,
        index=True,
        help="Full phone number including country code"
    )
    lead_id = fields.Many2one(
        'temer.lead',
        string='Lead',
        required=True,
        ondelete='cascade'
    )
    phone_datetime = fields.Datetime(
        string="Datetime",
        default=fields.Datetime.now,
        required=True
    )

    @api.model
    def create(self, vals):
        # Validate phone format before creation
        phone = vals.get('phone', '')
        country_id = vals.get('country_id')

        if country_id:
            country = self.env['res.country'].browse(country_id)
            self._validate_phone_format(phone, country)

        # Database UNIQUE constraint will handle uniqueness
        return super(TemerPhone, self).create(vals)

    def _validate_phone_format(self, phone, country):
        """Validate phone number format"""
        phone_regex = r'^\+\d{1,15}$'

        if not re.match(phone_regex, phone):
            raise ValidationError(_(
                "Invalid phone number format! Please use format: +[country code][number]"
            ))

        # Country-specific validation
        if country.phone_code == 251:  # Ethiopia
            if len(phone) != 13:  # +251XXXXXXXXX
                raise ValidationError(_(
                    "Ethiopian phone numbers must be 12 digits after country code (+251)."
                ))
            # Remove country code and check if starts with 0
            local_number = phone[4:]
            if local_number.startswith('0'):
                raise ValidationError(_(
                    "Ethiopian phone numbers must not start with 0 after country code."
                ))
        else:
            # Generic validation for other countries
            local_number_length = len(phone) - len(f"+{country.phone_code}")
            if local_number_length < 5 or local_number_length > 14:
                raise ValidationError(_(
                    "Invalid phone number length for %s. Local number should be 5-14 digits."
                ) % country.name)