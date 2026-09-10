from odoo import models, api
from odoo.exceptions import ValidationError
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
class PropertyReservationHistory(models.Model):
    _inherit = 'property.reservation'

    show_convert_to_regular = fields.Boolean(
        compute='can_convert_to_regular',
        string="Show Convert to Regular Button"
    )

    # def action_convert_to_regular(self):
    #         """
    #         Convert quick reservation to regular, keep the existing expire_date unchanged,
    #         and set the reservation_end_date on the property to the quick's end date.
    #         """
    #         for rec in self:
    #             regular_type = self.env['property.reservation.configuration'].search(
    #                 [('reservation_type', '=', 'regular')], limit=1)
    #             if not regular_type:
    #                 raise ValidationError("No regular reservation type configuration found.")
    #             # Only change the reservation_type_id and status, do NOT touch expire_date at all
    #             rec.write({
    #                 'reservation_type_id': regular_type.id,
    #                 'status': 'draft',
    #             })
    #             # Set the reservation_end_date on the property to the current expire_date (from quick)
    #             if rec.property_id and rec.expire_date:
    #                 rec.property_id.reservation_end_date = rec.expire_date

    # def action_convert_to_regular(self):
    #     """
    #     Convert quick reservation to regular, keep the existing expire_date unchanged,
    #     and set the reservation_end_date on the property to the quick's end date.
    #     """
    #     for rec in self:
    #         regular_type = self.env['property.reservation.configuration'].search(
    #             [('reservation_type', '=', 'regular')], limit=1)
    #         if not regular_type:
    #             raise ValidationError("No regular reservation type configuration found.")
    #         # Only change the reservation_type_id and status, do NOT touch expire_date at all
    #         rec.write({
    #             'reservation_type_id': regular_type.id,
    #             'status': 'draft',
    #         })
    #         # Set the reservation_end_date on the property to the current expire_date (from quick)
    #         if rec.property_id and rec.expire_date:
    #             rec.property_id.reservation_end_date = rec.expire_date

    def action_convert_to_regular(self):
        """
        Convert quick reservation to regular, reset expire_date based on regular config (replace quick time),
        and set the reservation_end_date on the property to the new regular's end date.
        """
        for rec in self:
            regular_type = self.env['property.reservation.configuration'].search(
                [('reservation_type', '=', 'regular')], limit=1)
            if not regular_type:
                raise ValidationError("No regular reservation type configuration found.")
            # Change the reservation_type_id and status
            rec.write({
                'reservation_type_id': regular_type.id,
                'status': 'draft',
            })
            # Set expire_date based on regular config, starting from now
            current_time = fields.Datetime.now()
            duration = regular_type.duration or 0
            expire_date = current_time
            if regular_type.duration_in == "minutes":
                expire_date = current_time + timedelta(minutes=duration)
            elif regular_type.duration_in == "hours":
                expire_date = current_time + timedelta(hours=duration)
            elif regular_type.duration_in == "days":
                expire_date = current_time + timedelta(days=duration)
            elif regular_type.duration_in == "weeks":
                expire_date = current_time + timedelta(weeks=duration)
            else:  # months
                expire_date = current_time + relativedelta(months=duration)
            # Count Sundays in the period
            sunday_count = 0
            temp_time = current_time
            while temp_time <= expire_date:
                if temp_time.weekday() == 6:
                    sunday_count += 1
                temp_time += timedelta(days=1)
            if sunday_count:
                expire_date += timedelta(days=sunday_count)
            # rec.expire_date = expire_date
            # Set the reservation_end_date on the property to the new expire_date
            if rec.property_id:
                rec.property_id.reservation_end_date = expire_date
    

    def can_convert_to_regular(self):
        for rec in self:
            # Only show the button if type is 'quick' AND status is NOT 'cancel' or 'expired'
            rec.show_convert_to_regular = (
                rec.reservation_type_id.reservation_type == 'quick'
                and rec.status not in ['canceled', 'expired']
            )


    # def approve_reservation(self):
    #     """
    #     Approve a reservation request.
    #     - If regular: set expire_date from configuration, starting from now, but if the current expire_date (from quick) is already in the past, expire this reservation.
    #     - If quick: set expire_date from configuration, and only approve if quick time not expired.
    #     - If quick time expired and status is draft/requested: set status to draft and release property.
    #     - If regular, use duration_in/duration from property.reservation.configuration for new end date.
    #     """
    #     self.ensure_one()
    #     config = self.reservation_type_id

    #     # Handle regular reservation
    #     if config.reservation_type == 'regular':
    #         # If the current expire_date (from quick) is in the past, expire this reservation
    #         if self.expire_date and self.expire_date < fields.Datetime.now():
    #             self.status = 'expired'
    #             return
    #         current_time = fields.Datetime.now()
    #         duration = config.duration or 0
    #         expire_date = current_time
    #         if config.duration_in == "minutes":
    #             expire_date = current_time + timedelta(minutes=duration)
    #         elif config.duration_in == "hours":
    #             expire_date = current_time + timedelta(hours=duration)
    #         elif config.duration_in == "days":
    #             expire_date = current_time + timedelta(days=duration)
    #         elif config.duration_in == "weeks":
    #             expire_date = current_time + timedelta(weeks=duration)
    #         else:  # months
    #             expire_date = current_time + relativedelta(months=duration)
    #         # Count Sundays in the period
    #         sunday_count = 0
    #         temp_time = current_time
    #         while temp_time <= expire_date:
    #             if temp_time.weekday() == 6:
    #                 sunday_count += 1
    #             temp_time += timedelta(days=1)
    #         if sunday_count:
    #             expire_date += timedelta(days=sunday_count)
    #         self.expire_date = expire_date
    #         self.status = 'reserved'
    #         if self.property_id:
    #             self.property_id.sudo().write({'state': 'reserved'})
    #         channel = self.env['discuss.channel'].search([('name','=','general')], limit=1)
    #         if channel:
    #             expire_date_notify = self.expire_date + timedelta(hours=3)
    #             channel.message_post(
    #                 body=(f"Property {self.property_id.name} is reserved, reservation will expire on {expire_date_notify}"),
    #                 message_type='comment',
    #                 subtype_xmlid='mail.mt_comment',
    #             )
    #         return

    #     # Handle quick reservation
    #     if config.reservation_type == 'quick':
    #         current_time = fields.Datetime.now()
    #         duration = config.duration or 0
    #         expire_date = current_time
    #         if config.duration_in == "minutes":
    #             expire_date = current_time + timedelta(minutes=duration)
    #         elif config.duration_in == "hours":
    #             expire_date = current_time + timedelta(hours=duration)
    #         elif config.duration_in == "days":
    #             expire_date = current_time + timedelta(days=duration)
    #         elif config.duration_in == "weeks":
    #             expire_date = current_time + timedelta(weeks=duration)
    #         else:  # months
    #             expire_date = current_time + relativedelta(months=duration)
    #         # Count Sundays in the period
    #         sunday_count = 0
    #         temp_time = current_time
    #         while temp_time <= expire_date:
    #             if temp_time.weekday() == 6:
    #                 sunday_count += 1
    #             temp_time += timedelta(days=1)
    #         if sunday_count:
    #             expire_date += timedelta(days=sunday_count)

    #         # If quick time is up and status is draft/requested, set to draft and release property
    #         if self.expire_date and fields.Datetime.now() > self.expire_date and self.status in ['draft', 'requested']:
    #             self.status = 'draft'
    #             if self.property_id:
    #                 self.property_id.sudo().write({'state': 'available'})
    #             return

    #         # Otherwise, approve and set new expire_date
    #         self.expire_date = expire_date
    #         self.status = 'reserved'
    #         if self.property_id:
    #             self.property_id.sudo().write({'state': 'reserved'})
    #         channel = self.env['discuss.channel'].search([('name','=','general')], limit=1)
    #         if channel:
    #             expire_date_notify = self.expire_date + timedelta(hours=3)
    #             channel.message_post(
    #                 body=(f"Property {self.property_id.name} is reserved, reservation will expire on {expire_date_notify}"),
    #                 message_type='comment',
    #                 subtype_xmlid='mail.mt_comment',
    #             )
    #         return

    #     # Fallback for other types
    #     if self.property_id.state != 'available':
    #         raise ValidationError(
    #             _(f"Cannot approve reservation request. Property {self.property_id.name} is in {self.property_id.state} state")
    #         )
    #     channel = self.env['discuss.channel'].search([('name','=','general')], limit=1)
    #     if channel:
    #         expire_date_notify = self.expire_date + timedelta(hours=3)
    #         channel.message_post(
    #             body=(f"Property {self.property_id.name} is reserved, reservation will expire on {expire_date_notify}"),
    #             message_type='comment',
    #             subtype_xmlid='mail.mt_comment',
    #         )
    #     self.property_id.sudo().write({'state': 'reserved'})
    #     self.status = 'reserved'


    # def cancel_reservation(self):
    #     # First call the original cancel logic
    #     res = super(PropertyReservationHistory, self).cancel_reservation()
    #     # Then mark the property as available
    #     for rec in self:
    #         rec.property_id.sudo().write({'state': 'available'})
    #     return res


    def cancel_reservation(self):
        res = super(PropertyReservationHistory, self).cancel_reservation()
        for rec in self:
            if rec.property_id.state == 'reserved':
                rec.property_id.sudo().write({'state': 'available'})
        return res


    # def check_expired_reservation(self):
    #     # Call original logic first
    #     super(PropertyReservationHistory, self).check_expired_reservation()
    #     current_time = fields.Datetime.now()
    #     # Find all regular reservations that are still reserved and have expired
    #     expired_regular_reservations = self.search([
    #         ('reservation_type_id.reservation_type', '=', 'regular'),
    #         ('status', '=', 'reserved'),
    #         ('expire_date', '<', current_time)
    #     ])
    #     # Set their status to expired
    #     expired_regular_reservations.write({'status': 'expired'})
    #     # Only set property to available if it was reserved (never if draft or sold)
    #     expired_reservations = self.search([
    #         ('status', '=', 'expired'),
    #         ('property_id.state', '=', 'reserved')
    #     ])
    #     for reservation in expired_reservations:
    #         if reservation.property_id and reservation.property_id.state == 'reserved':
    #             # Do NOT set to available if property is in draft or sold
    #             reservation.property_id.sudo().write({'state': 'available'})



    def write(self, vals):
        # If status is being set to 'reserved', ensure property is also reserved
        res = super(PropertyReservationHistory, self).write(vals)
        if 'status' in vals and vals['status'] == 'reserved':
            for rec in self:
                if rec.property_id and rec.property_id.state != 'reserved':
                    rec.property_id.sudo().write({'state': 'reserved'})
        return res



    # def check_expired_regular_reservation(self):
    #     """Check and update expired regular reservations."""
    #     now = fields.Datetime.now()
    #     # Find all expired regular reservations in relevant states
    #     regular_reservations = self.search([
    #         ('reservation_type_id.reservation_type', '=', 'regular'),
    #         ('status', 'in', ['draft', 'requested', 'reserved']),
    #         ('expire_date', '<=', now),
    #     ])
    #     for reservation in regular_reservations:
    #         prev_status = reservation.status
    #         if reservation.status in ['draft', 'requested']:
    #             # Cancel expired drafts/requested
    #             reservation.sudo().write({
    #                 'status': 'canceled',
    #                 'canceled_time': datetime.now()
    #             })
    #             # Set property available if previously reserved
    #             if reservation.property_id and reservation.property_id.state == 'reserved':
    #                 reservation.property_id.sudo().write({'state': 'available'})
    #         elif reservation.status == 'reserved':
    #             # Expire reserved if expired
    #             reservation.sudo().write({
    #                 'status': 'expired',
    #                 'canceled_time': datetime.now()
    #             })
    #             if reservation.property_id and reservation.property_id.state == 'reserved':
    #                 reservation.property_id.sudo().write({'state': 'available'})
    #         # Optional: Move lead to Follow Up
    #         stage = self.env['crm.stage'].search([('name', 'ilike', "Follow Up")], limit=1)
    #         if stage and reservation.crm_lead_id:
    #             reservation.crm_lead_id.write({'stage_id': stage.id})