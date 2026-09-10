# -*- coding: utf-8 -*-
##############################################################################
#    Property Lock / Unlock
#    Copyright (C) 2024-TODAY Ahadubit Technologies
##############################################################################

from odoo import models, fields


class PropertyReservationTransfer(models.Model):
    _inherit = 'property.reservation.transfer.history'

    # Exclude locked properties from transfer destination
    property_id = fields.Many2one(
        'property.property',
        string="Transfer to Property",
        domain=[('state', '=', 'available'), ('is_locked', '=', False)],
        required=True,
        tracking=True
    )
