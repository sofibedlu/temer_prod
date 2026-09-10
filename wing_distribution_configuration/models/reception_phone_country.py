from odoo import models, fields


class CrmReceptionPhoneCountry(models.Model):
    _inherit = "crm.reception.phone"

    country_id = fields.Many2one("res.country", string="Country", ondelete="set null")

