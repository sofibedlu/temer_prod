from odoo import models, fields, api, _

class PropertyReservationConfig(models.Model):
    _inherit = 'property.reservation.configuration'

    reservation_type = fields.Selection(
        selection_add=[('prespecial', 'Pre-Special')],
        string='Reservation Type',
        tracking=True,
    )