# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import ValidationError
from datetime import timedelta
from dateutil.relativedelta import relativedelta


class PropertyReservationConvertRegular(models.Model):
    _inherit = 'property.reservation'

    def action_convert_to_regular(self):
        """Convert quick reservations to regular and update expire_date correctly."""
        for rec in self:
            regular_type = self.env['property.reservation.configuration'].search(
                [('reservation_type', '=', 'regular')], limit=1)
            if not regular_type:
                raise ValidationError("No regular reservation type configuration found.")

            rec.write({
                'reservation_type_id': regular_type.id,
                'status': 'draft',
                'converted_regular': True,
            })

            current_time = fields.Datetime.now()
            duration = regular_type.duration or 0
            expire_date = current_time
            if regular_type.duration_in == 'minutes':
                expire_date = current_time + timedelta(minutes=duration)
            elif regular_type.duration_in == 'hours':
                expire_date = current_time + timedelta(hours=duration)
            elif regular_type.duration_in == 'days':
                expire_date = current_time + timedelta(days=duration)
            elif regular_type.duration_in == 'weeks':
                expire_date = current_time + timedelta(weeks=duration)
            else:
                expire_date = current_time + relativedelta(months=duration)

            sunday_count = 0
            temp_time = current_time
            while temp_time <= expire_date:
                if temp_time.weekday() == 6:
                    sunday_count += 1
                temp_time += timedelta(days=1)
            if sunday_count:
                expire_date += timedelta(days=sunday_count)

            rec.expire_date = expire_date
            if rec.property_id:
                rec.property_id.reservation_end_date = expire_date
