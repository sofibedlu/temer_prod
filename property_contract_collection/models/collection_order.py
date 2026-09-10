from odoo import models, fields, api, _
from datetime import timedelta
from markupsafe import Markup

class CollectionOrder(models.Model):
    _inherit = 'collection.order'

    has_pending_void_request = fields.Boolean(
        string='Has Pending Void Request', 
        compute='_compute_has_pending_void_request'
    )
    has_pending_amendment_request = fields.Boolean(
        string='Has Pending Amendment Request',
        compute='_compute_has_pending_amendment_request'
    )

    def _compute_has_pending_void_request(self):
        for rec in self:
            domain = [
                ('state', 'in', ['draft', 'approved']),
                '|',
                ('collection_id', '=', rec.id),
                ('sale_id', '=', rec.sale_id.id)
            ]
            existing_request = self.env['property.contract.void.request'].search(domain, limit=1)
            rec.has_pending_void_request = bool(existing_request)

    def _compute_has_pending_amendment_request(self):
        Request = self.env['property.schedule.amendment.request']
        for rec in self:
            sale_id = rec.sale_id.id if rec.sale_id else False
            domain = ['&',
                        ('state', '=', 'draft'),
                        '|',
                            ('collection_id', '=', rec.id),
                            ('sale_id', '=', sale_id),
                     ]
            rec.has_pending_amendment_request = bool(Request.search(domain, limit=1))

    def action_reactivate(self):
        self.ensure_one()
        return {
            'name': _('Reactivate Collection Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'collection.reactivate.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_collection_id': self.id,
            }
        }

    def action_open_void_wizard(self):
        self.ensure_one()
        return {
            'name': 'Void Contract Request',
            'type': 'ir.actions.act_window',
            'res_model': 'void.contract.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_collection_id': self.id,
                'default_sale_id': self.sale_id.id
            }
        }
    
    def action_open_amendment_request_wizard(self):
        self.ensure_one()
        return {
            'name': 'Request Schedule Amendment',
            'type': 'ir.actions.act_window',
            'res_model': 'amendment.request.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_collection_id': self.id}
        }

    @api.model
    def _cron_check_termination(self):
        config = self.env['property.collection.config'].search([], limit=1)
        if not config:
            return
        
        threshold_days = config.termination_threshold_days
        today = fields.Date.today()
        cutoff_date = today - timedelta(days=threshold_days)

        overdue_installments = self.env['collection.installment'].search([
            ('state', '=', 'overdue'),
            ('due_date', '<', cutoff_date),
            ('collection_id.state', '=', 'active')
        ])
        
        collections_to_terminate = overdue_installments.mapped('collection_id')
        for collection in collections_to_terminate:
            collection.write({'state': 'terminated'})
            collection.message_post(
                body=Markup(f"<b>System Termination:</b> Order terminated automatically. An installment is overdue by more than {threshold_days} days.")
            )

class CollectionInstallment(models.Model):
    _inherit = 'collection.installment'

    @api.depends('amount_residual', 'due_date', 'amount_paid', 'payment_ids.status')
    def _compute_state(self):
        super(CollectionInstallment, self)._compute_state()
        collections_to_check = self.mapped('collection_id').filtered(lambda c: c.state == 'active')
        for collection in collections_to_check:
            if not any(inst.state != 'paid' for inst in collection.installment_ids):
                collection.sudo()._check_and_update_completed_status()