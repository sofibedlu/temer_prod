# -*- coding: utf-8 -*-
from odoo import models, fields


class PropertyReservationExtendInherit(models.Model):
    _inherit = 'property.reservation.extend.history'

    # Override to remove the required constraint on Request Letter
    # so users can save an extension request without uploading a file.
    request_letter_file = fields.Binary(
        string="Request Letter",
        tracking=True,
        required=False,
    )
