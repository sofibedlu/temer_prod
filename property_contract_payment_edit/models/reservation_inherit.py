from odoo import models, fields

class PropertyReservation(models.Model):
    _inherit = 'property.reservation'

    # flag
    payment_edit_mode = fields.Boolean(default=False)


class PropertyReservationPayment(models.Model):
    _inherit = 'property.reservation.payment'

    # Directly related field so the XML tree view evaluates it instantly without 'parent' bugs
    sales_wizard_mode = fields.Boolean(
        related='reservation_id.is_from_sales', 
        string="In Sales Wizard Mode"
    )