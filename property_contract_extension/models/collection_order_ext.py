from odoo import models, fields, api

class CollectionOrder(models.Model):
    _inherit = 'collection.order'

    def _check_and_update_completed_status(self):
        super(CollectionOrder, self)._check_and_update_completed_status()

        # Check for sales that need to be marked as Done
        for rec in self:
            if rec.state == 'completed' and rec.sale_id and rec.sale_id.state == 'approve':
                rec.sale_id.write({'state': 'done'})
                rec.sale_id.message_post(body="<b>Contract Completed:</b> All payments have been collected via the Collection Order.")


class CollectionInstallment(models.Model):
    _inherit = 'collection.installment'
    _order = 'sequence, due_date asc, id asc'

    sequence = fields.Integer(string='Sequence', default=10)