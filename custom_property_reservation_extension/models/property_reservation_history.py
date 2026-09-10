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
    converted_regular = fields.Boolean(readonly=True, default=False, string="converted reservation", store=True)

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
                'converted_regular': True,
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
                and rec.status == 'reserved'
            )




    def check_expired_reservation(self):
        """Check and update expired reservations: now includes 'draft'."""
        reservations = self.search([
            ('status', 'in', ['draft', 'requested', 'reserved']),
            ('expire_date', '<=', fields.Datetime.now()),
        ])
        for reservation in reservations:
            
            status = reservation.status
            reservation.sudo().write({
                'status': 'expired',
                'canceled_time': datetime.now()
            })

       

            if status in ["reserved", "draft", "requested"]:
                property_obj = reservation.property_id.sudo()
                other_reserved = self.search([
                    ('id', '!=', reservation.id),
                    ('property_id', '=', property_obj.id),
                    ('status', '=', 'reserved'),
                ], limit=1)

                if not other_reserved and property_obj.state not in ['sold', 'pending_sale', 'rented', 'draft']:
                    property_obj.write({'state': 'available'})




            stage = self.env['crm.stage'].search([('name', 'ilike', "Follow Up")], limit=1)
            if stage and reservation.crm_lead_id:
                reservation.crm_lead_id.write({
                    'stage_id': stage.id,
                })



    def approve_reservation(self):
        self.ensure_one()
        config = self.reservation_type_id

        # Validation for both 'special' and 'regular'
        if config.reservation_type in ['special', 'regular'] and self.converted_regular != True:
            if self.property_id.state == 'reserved':
                raise ValidationError(_("Cannot approve a %s reservation because the property is already reserved: %s") % (config.reservation_type, self.property_id.name))

        # Handle regular reservation
        if config.reservation_type == 'regular':
            # current_time = self.expire_date or self.create_date or fields.Datetime.now()
            current_time = fields.Datetime.now()
            duration = config.duration or 0
            expire_date = current_time
            if config.duration_in == "minutes":
                expire_date = current_time + timedelta(minutes=duration)
            elif config.duration_in == "hours":
                expire_date = current_time + timedelta(hours=duration)
            elif config.duration_in == "days":
                expire_date = current_time + timedelta(days=duration)
            elif config.duration_in == "weeks":
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
                expire_date = expire_date + timedelta(days=sunday_count)
            self.expire_date = expire_date
            # if self.property_id.state != 'sold':
            # if self.property_id.state == 'available':
            if self.property_id.state not in ['sold', 'pending_sale', 'rented','draft']:

                self.property_id.sudo().write({'state': 'reserved'})
            else:
                raise ValidationError(_("Cannot reserve a because it is in a non-available state: %s") % self.property_id.name)
            self.status = 'reserved'
            channel = self.env['discuss.channel'].search([('name','=','general')], limit=1)
            if channel:
                expire_date_notify = self.expire_date + timedelta(hours=3)
                channel.message_post(
                    body=(f"Property {self.property_id.name} is reserved, reservation will expire on {expire_date_notify}"),
                    message_type='comment',
                    subtype_xmlid='mail.mt_comment',
                )
            return

        # Handle quick reservation
        if config.reservation_type == 'quick':
            current_time = fields.Datetime.now()
            duration = config.duration or 0
            expire_date = current_time
            if config.duration_in == "minutes":
                expire_date = current_time + timedelta(minutes=duration)
            elif config.duration_in == "hours":
                expire_date = current_time + timedelta(hours=duration)
            elif config.duration_in == "days":
                expire_date = current_time + timedelta(days=duration)
            elif config.duration_in == "weeks":
                expire_date = current_time + timedelta(weeks=duration)
            else:
                expire_date = current_time + relativedelta(months=duration)
            # Count Sundays in the period
            sunday_count = 0
            temp_time = current_time
            while temp_time <= expire_date:
                if temp_time.weekday() == 6:
                    sunday_count += 1
                temp_time += timedelta(days=1)
            if sunday_count:
                expire_date = expire_date + timedelta(days=sunday_count)

            # if self.expire_date and fields.Datetime.now() > self.expire_date and self.status in ['draft', 'requested']:
            #     self.status = 'draft'
            #     if self.property_id.state != 'sold':
            #         self.property_id.sudo().write({'state': 'available'})
            #     return

            if self.expire_date and fields.Datetime.now() > self.expire_date and self.status in ['draft', 'requested']:
                self.status = 'draft'
                # if self.property_id.state != 'sold':
                if self.property_id.state not in ['sold', 'pending_sale', 'rented','draft']:

                # if self.property_id.state == 'reserved':
                    self.property_id.sudo().write({'state': 'available'})
                return


            self.expire_date = expire_date
            # if self.property_id.state != 'sold':
            if self.property_id.state not in ['sold', 'pending_sale', 'rented','draft']:
            # if self.property_id.state == 'available':
                self.property_id.sudo().write({'state': 'reserved'})
            else:
                raise ValidationError(_("Cannot reserve a because it is in a non-available state: %s") % self.property_id.name)
            self.status = 'reserved'
            channel = self.env['discuss.channel'].search([('name','=','general')], limit=1)
            if channel:
                expire_date_notify = self.expire_date + timedelta(hours=3)
                channel.message_post(
                    body=(f"Property {self.property_id.name} is reserved, reservation will expire on {expire_date_notify}"),
                    message_type='comment',
                    subtype_xmlid='mail.mt_comment',
                )
            return

        # For other types, skip validation but never override "sold"
        if self.property_id.state == 'sold':
            raise ValidationError(_("Cannot reserve a because it is in a non-available state: %s") % self.property_id.name)
        channel = self.env['discuss.channel'].search([('name','=','general')], limit=1)
        if channel:
            expire_date = self.expire_date + timedelta(hours=3)
            channel.message_post(
                body=(f"Property {self.property_id.name} is reserved, reservation will expire on {expire_date}"),
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
            )
        self.property_id.sudo().write({'state': 'reserved'})
        self.status = 'reserved'


    from odoo import models, fields

    class CancellationReasonWizardInherit(models.TransientModel):
        _inherit = 'cancellation.reason.wizard'

        def action_cancel_reservation(self):
            if self.reservation_id:
                status = self.reservation_id.status
                self.reservation_id.write({
                    'status': 'canceled',
                    'canceled_time': fields.Datetime.now(),
                    'canceled_reason': self.reason if self.other else self.reason_id.name
                })
    
                            # ...existing code...
                if status in ["reserved", "draft", "requested"]:
                    reservation = self.sudo().reservation_id
                    property_obj = reservation.property_id
             
                    if property_obj.state == 'reserved' and property_obj.state not in ['sold', 'pending_sale', 'rented','draft']:
                            property_obj.write({'state': 'available'})
                # ...existing code...



                # Optional: set CRM stage
                stage = self.env['crm.stage'].search([('name', 'ilike', "Follow Up")], limit=1)
                if stage and self.reservation_id.crm_lead_id:
                    self.reservation_id.crm_lead_id.write({
                        'stage_id': stage.id,
                    })
