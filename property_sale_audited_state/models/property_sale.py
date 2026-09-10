from odoo import models, fields, api

class PropertySale(models.Model):
    _inherit = 'property.sale'

    state = fields.Selection(
        selection_add=[('audited', 'Audited'),
                       ('done', 'Done'),],
        ondelete={'audited': 'set default'}
    )

    def action_mark_as_audited(self):

        for rec in self:
            if rec.state == 'approve':
                rec.write({'state': 'audited'})