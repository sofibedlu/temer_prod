# -*- coding: utf-8 -*-
from odoo import models, fields


class PropertyReservationExtensionStatus(models.Model):
    """
    Extends property.reservation to add 'pending_final_approval' to extension_status
    so the reservation form correctly reflects the intermediate approval state.
    """
    _inherit = 'property.reservation'

    extension_status = fields.Selection(
        selection_add=[
            ('pending_final_approval', 'Pending Final Approval'),
        ],
    )
