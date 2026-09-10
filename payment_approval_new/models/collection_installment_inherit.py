# -*- coding: utf-8 -*-

from odoo import models, fields, api


class CollectionInstallment(models.Model):
    _inherit = 'collection.installment'

    state = fields.Selection(selection_add=[
        ('pending', 'Pending')
    ])

    @api.depends('amount_residual', 'due_date', 'amount_paid', 'payment_ids.status')
    def _compute_state(self):
        """
        Compute the installment state.
        Priority: paid > pending > overdue > partial > unpaid
        Override to check for paid status first, then pending payments and draft payment approvals
        """
        today = fields.Date.today()
        for rec in self:
            # First check if it's fully paid (has invoice and payment completed)
            # If amount_residual <= 0, it's paid regardless of draft approvals
            if rec.amount_residual <= 0:
                rec.state = 'paid'
            else:
                # Check if there are any pending payments
                pending_payments = rec.payment_ids.filtered(lambda p: p.status == 'pending')
                if pending_payments:
                    rec.state = 'pending'
                else:
                    # Check for draft payment approval records (only if not paid)
                    # Use sudo to ensure we can access all draft approvals
                    draft_approvals = self.env['payment.approval.record'].sudo().search([
                        ('installment_id', '=', rec.id),
                        ('state', '=', 'draft')
                    ], limit=1)
                    if draft_approvals:
                        rec.state = 'pending'
                    elif rec.due_date and rec.due_date < today:
                        rec.state = 'overdue'
                    elif rec.amount_paid > 0:
                        rec.state = 'partial'
                    else:
                        rec.state = 'unpaid'
    
    @api.model
    def _fix_all_pending_installments(self):
        """Recompute state for all installments that have draft payment approvals"""
        # Find all installments with draft payment approvals
        try:
            import logging
            _logger = logging.getLogger(__name__)
            
            # Find all draft payment approvals
            draft_payments = self.env['payment.approval.record'].sudo().search([
                ('state', '=', 'draft')
            ])
            
            _logger.info(f"Found {len(draft_payments)} draft payment approvals")
            
            if not draft_payments:
                _logger.info("No draft payment approvals found")
                return 0
            
            # Get all unique installments
            installments = draft_payments.mapped('installment_id').filtered(lambda i: i)
            
            if not installments:
                _logger.info("No installments found with draft payment approvals")
                return 0
            
            # Remove duplicates
            installments = installments.sudo()
            unique_installments = installments.browse(list(set(installments.ids)))
            
            _logger.info(f"Processing {len(unique_installments)} unique installments for state recomputation")
            
            # Process in batches to avoid memory issues
            batch_size = 100
            updated_count = 0
            for i in range(0, len(unique_installments), batch_size):
                batch = unique_installments[i:i + batch_size]
                
                # Invalidate cache for this batch
                batch.invalidate_recordset(['state'])
                
                # Recompute state for this batch
                batch._compute_state()
                
                # Read computed state values and write them to database
                for inst in batch:
                    computed_state = inst.state
                    # Write directly to database to ensure it's stored
                    self.env.cr.execute(
                        "UPDATE collection_installment SET state = %s WHERE id = %s",
                        (computed_state, inst.id)
                    )
                    if computed_state == 'pending':
                        updated_count += 1
                
                # Invalidate cache after SQL update to ensure consistency
                batch.invalidate_recordset(['state'])
            
            _logger.info(f"Updated {updated_count} installments to pending state")
            _logger.info(f"Total installments processed: {len(unique_installments)}")
            
            return len(unique_installments)
        except Exception as e:
            import logging
            _logger = logging.getLogger(__name__)
            _logger.error(f"Error in _fix_all_pending_installments: {e}", exc_info=True)
            return 0
    
    def action_recompute_state(self):
        """Manual action to recompute state for selected installments"""
        self.invalidate_recordset(['state'])
        self._compute_state()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': f'State recomputed for {len(self)} installment(s)',
                'type': 'success',
                'sticky': False,
            }
        }

