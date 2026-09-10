from odoo import models, fields, api
from markupsafe import Markup

class CollectionOrder(models.Model):
    _inherit = 'collection.order'

    has_been_terminated_before = fields.Boolean(
        string="Previously Terminated",
        default=False,
        readonly=True,
        tracking=True,
        help="If checked, this order has been terminated in the past. It will no longer receive the Termination Threshold grace period."
    )

    def write(self, vals):

        if vals.get('state') == 'terminated':
            vals['has_been_terminated_before'] = True
            
        return super(CollectionOrder, self).write(vals)

    @api.model
    def _cron_check_termination(self):
        res = super(CollectionOrder, self)._cron_check_termination()

        today = fields.Date.today()

        # ignore the 'cutoff_date' threshold here.
        zero_tolerance_installments = self.env['collection.installment'].search([
            ('state', '=', 'overdue'),
            ('due_date', '<', today),
            ('collection_id.state', '=', 'active'),
            ('collection_id.has_been_terminated_before', '=', True)
        ])

        collections_to_terminate = zero_tolerance_installments.mapped('collection_id')
        
        for collection in collections_to_terminate:
            collection.write({'state': 'terminated'})
            collection.message_post(
                body=Markup("<b>System Termination (Zero Tolerance):</b> Order terminated automatically. This order was previously reactivated and has gone overdue again (No Grace Period Applied).")
            )

        return res