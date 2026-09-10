from odoo import models, fields

class SupportContact(models.Model):
    _name = 'support.contact'
    _description = 'Person of Contact'
    _order = 'name'

    name = fields.Char(string='Contact Name', required=True)
    phone = fields.Char(string='Phone No.')

    def _compute_display_name(self):
        for rec in self:
            if rec.phone:
                rec.display_name = f"{rec.name} | {rec.phone}"
            else:
                rec.display_name = rec.name
