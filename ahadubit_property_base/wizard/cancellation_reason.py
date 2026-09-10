from email.policy import default

from odoo import models, fields, api,_
from odoo.exceptions import ValidationError
import re

from odoo.tools.safe_eval import datetime


class PropertyReservation(models.TransientModel):
    _name = 'cancellation.sale.reason.wizard'

    reason = fields.Text(string="Reason")
    reason_id = fields.Many2one('property.sale.cancel.reason', string="Reason")
    other=fields.Boolean(default=False)
    sale_id = fields.Many2one('property.sale', string="Sale")


    def action_cancel_sales(self):
        if self.sale_id:
            self.sale_id.write({
                'state': 'cancel',
                'cancel_reason': self.reason if self.other else self.reason_id.name
            })
            self.sale_id.property_id.write({'state': 'available'})
            if self.sale_id.reservation_id:
                self.sale_id.reservation_id.write({'status': 'canceled'})


