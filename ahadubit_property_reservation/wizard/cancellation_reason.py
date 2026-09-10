from email.policy import default

from odoo import models, fields, api,_
from odoo.exceptions import ValidationError
import re

from odoo.tools.safe_eval import datetime


class PropertyReservation(models.TransientModel):
    _name = 'cancellation.reason.wizard'

    reason = fields.Text(string="Reason")
    reason_id = fields.Many2one('property.reservation.cancel', string="Reason")
    other=fields.Boolean(default=False)
    reservation_id = fields.Many2one('property.reservation', string="Reservation")


    def action_cancel_reservation(self):
        if self.reservation_id:
            status=self.reservation_id.status
            self.reservation_id.write({
                'status': 'canceled',
                'canceled_time': fields.Datetime.now(),
                'canceled_reason': self.reason if self.other else self.reason_id.name
            })
            if status =="reserved":
                self.sudo().reservation_id.property_id.write({'state': 'available'})

            stage = self.env['crm.stage'].search([('name', 'ilike', "Follow Up")], limit=1)
            if stage and self.reservation_id.crm_lead_id:
                self.reservation_id.crm_lead_id.write({
                    'stage_id': stage.id,
                })



class PropertyReservationPayment(models.TransientModel):
    _name = 'payment.cancellation.reason.wizard'

    reason = fields.Text(string="Reason")
    reason_id = fields.Many2one('payment.cancellation.reason', string="Reason")
    other=fields.Boolean(default=False)
    payment_id = fields.Many2one('property.reservation.payment', string="Reservation Payment")


    def action_cancel_payment(self):
        if self.payment_id:
            self.payment_id.write({
                'payment_status': 'canceled',
                'canceled_time': fields.Datetime.now(),
                'cancel_reason': self.reason if self.other else self.reason_id.name
            })
            if self.payment_id.reservation_id and self.payment_id.reservation_id.status=="pending_sales":
                self.payment_id.reservation_id.write({'status': 'reserved'})
                sales=self.env['property.sale'].search([('reservation_id', '=', self.payment_id.reservation_id.id)])
                for sale in sales:
                    sale.write({'state': 'cancel'})
                    sale.property_id.write({'state': 'reserved'})








