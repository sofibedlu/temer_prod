from odoo import models, fields, _
from odoo.exceptions import UserError
from odoo.tools import Markup, float_compare
from markupsafe import Markup

class PropertySale(models.Model):
    _inherit = 'property.sale'

    state = fields.Selection(selection_add=[('approve', 'Approved'), ('done', 'Done'), ('void', 'Void')])
    has_pending_void_request = fields.Boolean(
        string='Has Pending Void Request', 
        compute='_compute_has_pending_void_request'
    )
    is_schedule_unlocked = fields.Boolean(string="Schedule Unlocked", default=False, copy=False, tracking=True)
    schedule_history_ids = fields.One2many('property.payment.schedule.history', 'sale_id', string="Schedule History")

    def _compute_has_pending_void_request(self):
        for sale in self:
            existing_request = self.env['property.contract.void.request'].search([
                ('sale_id', '=', sale.id),
                ('state', 'in', ['draft', 'approved'])
            ], limit=1)
            sale.has_pending_void_request = bool(existing_request)

    def action_approve_sale(self):
        """Action for the Approve button"""
        to_approve = self.filtered(lambda r: r.state == 'confirm')
        if not to_approve:
            raise UserError(_("You can only approve contracts that are currently in the 'Confirm' state.\n"
                            "Please deselect any records that are Draft, already Approved, or Void."))

        # Process only the valid records
        for rec in to_approve:
            term_ids = [line.payment_term_id.id for line in rec.payment_installment_line_ids if line.payment_term_id]
            if len(term_ids) != len(set(term_ids)):
                raise UserError(_("Validation Error: Duplicate payment terms found in the schedule. Each payment line must have a distinct Payment Term."))
            
            rec.write({'state': 'approve'})
            
            # Create Collection Order logic
            if hasattr(rec, '_create_collection_order') and not rec.collection_order_id:
                rec._create_collection_order()
                
            # Log
            if rec.collection_order_id:
                rec.message_post(body=Markup("<b>Collection Order Created</b><br/>Ref: %s") % rec.collection_order_id.name)

    def action_open_void_wizard(self):
        self.ensure_one()
        return {
            'name': 'Void Contract Request',
            'type': 'ir.actions.act_window',
            'res_model': 'void.contract.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_sale_id': self.id}
        }
    
    def action_open_amendment_wizard(self):
        self.ensure_one()
        if self.state == 'done':
            raise UserError(_("You cannot amend the schedule for a fully paid (Done) contract."))
        return {
            'name': 'Amend Payment Schedule',
            'type': 'ir.actions.act_window',
            'res_model': 'schedule.amendment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_sale_id': self.id}
        }

    def action_sync_and_lock_schedule(self):
        for sale in self:
            term_ids = [line.payment_term_id.id for line in sale.payment_installment_line_ids if line.payment_term_id]
            if len(term_ids) != len(set(term_ids)):
                raise UserError(_("Validation Error: Duplicate payment terms found in the amended schedule. Each payment line must have a distinct Payment Term before syncing."))
            
            # Sync with Collection Order
            if sale.collection_order_id:
                collection = sale.collection_order_id.sudo()

                active_term_ids = sale.payment_installment_line_ids.mapped('payment_term_id').ids
                existing_term_ids = collection.installment_ids.mapped('payment_term_line_id.id')
                orphaned_installments = collection.installment_ids.filtered(
                    lambda i: i.payment_term_line_id and i.payment_term_line_id.id not in active_term_ids
                )
                # for orphan in orphaned_installments:
                #     if orphan.state in ['partial', 'paid', 'pending'] or orphan.amount_paid > 0:
                #         raise UserError(_(
                #             "Validation Error: You removed the payment line corresponding to '%s', but it is already '%s' (Paid: %s) in the Collection Order.\n\n"
                #             "You cannot remove lines that have active payments."
                #         ) % (orphan.name, orphan.state, orphan.amount_paid))

                # # Check for modified amounts on paid/partial installments
                # for line in sale.payment_installment_line_ids:
                #     if line.payment_term_id and line.payment_term_id.id in existing_term_ids:
                #         inst = collection.installment_ids.filtered(lambda i: i.payment_term_line_id.id == line.payment_term_id.id)
                #         if inst:
                #             first_inst = inst[0]
                #             if first_inst.state in ['partial', 'paid', 'pending'] or first_inst.amount_paid > 0:
                #                 if float_compare(line.expected_amount, first_inst.amount_total, precision_digits=2) != 0:
                #                     raise UserError(_(
                #                         "Validation Error: You changed the expected amount for '%s', but it is already '%s' in the Collection Order.\n\n"
                #                         "You cannot modify the amount of lines that have payments.\n"
                #                         "(Expected: %s, Current Collection Amount: %s)"
                #                     ) % (first_inst.name, first_inst.state, line.expected_amount, first_inst.amount_total))

                if hasattr(collection, 'payment_schedule_type'):
                    collection.write({'payment_schedule_type': getattr(sale, 'payment_schedule_type', False)})
                
                if orphaned_installments:
                    orphaned_installments.unlink()

                for line in sale.payment_installment_line_ids:
                    due_date = getattr(line, 'due_date', False)
                    sequence = getattr(line, 'sequence', 10)
                    
                    if line.payment_term_id and line.payment_term_id.id in existing_term_ids:
                        # Update existing unpaid/partial/paid installment
                        inst = collection.installment_ids.filtered(lambda i: i.payment_term_line_id.id == line.payment_term_id.id)
                        if inst:
                            update_vals = {
                                'sequence': sequence,
                                'amount_total': line.expected_amount, #added for temp
                                'amount_paid': line.paid_amount, #added fpor temp
                            }
                            
                            #commented for temp
                            #if inst[0].state == 'unpaid' and inst[0].amount_paid <= 0:
                            #    update_vals['amount_total'] = line.expected_amount
                            
                            # ONLY update due_date if the installment is NOT paid
                            if getattr(sale, 'payment_schedule_type', False) == 'time' and inst[0].state != 'paid':
                                update_vals['due_date'] = due_date
                                
                            #inst[0].write(update_vals)
                            inst[0].sudo().write(update_vals)
                    else:
                        create_vals = {
                            'collection_id': collection.id,
                            'name': line.payment_term_id.name if line.payment_term_id else 'Installment',
                            'amount_total': line.expected_amount,
                            'amount_paid': line.paid_amount,
                            'payment_term_line_id': line.payment_term_id.id if line.payment_term_id else False,
                            'sequence': sequence,
                        }
                        if getattr(sale, 'payment_schedule_type', False) == 'time':
                            create_vals['due_date'] = due_date
                            
                        self.env['collection.installment'].sudo().create(create_vals)

            # Lock the schedule
            sale.is_schedule_unlocked = False
            sale.message_post(body=Markup("<b>Payment Schedule Amended and Synced with Collection Order.</b>"))
            if sale.collection_order_id:
                sale.collection_order_id.sudo().message_post(
                    body=Markup("<b>Payment Schedule Amended and Synced with Collection Order.</b>")
                )