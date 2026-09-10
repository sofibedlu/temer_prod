from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CollectionInstallmentPaymentOrder(models.Model):
    _inherit = 'collection.installment'

    def action_open_payment_wizard(self):
        """Opens the Payment Register Wizard.
        Validates that previous installments are paid or have pending payments.
        If previous installment has pending payments, validation passes.
        """
        self.ensure_one()
        
        if not self.collection_id:
            # No collection, allow payment
            return self._get_payment_wizard_action()
        
        # Get all installments for this collection, ordered by due_date and id
        all_installments = self.collection_id.installment_ids.sorted(
            key=lambda x: (x.due_date or fields.Date.today(), x.id)
        )
        
        # Find the current installment's position
        current_index = None
        for idx, inst in enumerate(all_installments):
            if inst.id == self.id:
                current_index = idx
                break
        
        # If current installment is the first one, allow payment
        if current_index is None or current_index == 0:
            return self._get_payment_wizard_action()
        
        # Check all previous installments
        previous_installments = all_installments[:current_index]
        
        for prev_inst in previous_installments:
            # If previous installment is paid, it's OK - PASS validation
            if prev_inst.state == 'paid':
                continue


            has_pending_payment = self.env['collection.installment.payment'].search_count([
                ('installment_id', '=', prev_inst.id),
                ('status', '=', 'pending'),
            ]) > 0


            if has_pending_payment:
                continue

            # if prev_inst.state == 'unpaid' and prev_inst.amount_residual > 0:
            #     raise UserError(
            #         _("Cannot pay this installment. Please pay the previous installment first: %s")
            #         % prev_inst.name
            #     )
            #
            # if prev_inst.state == 'partial' and prev_inst.amount_residual > 0:
            #     raise UserError(
            #         _("Cannot pay this installment. Please pay the previous installment first: %s")
            #         % prev_inst.name
            #     )
            #
            #
            # if prev_inst.state == 'overdue' and prev_inst.amount_residual > 0:
            #     raise UserError(
            #         _("Cannot pay this installment. Please pay the previous installment first: %s")
            #         % prev_inst.name
            #     )
        

        return self._get_payment_wizard_action()
    
    def _get_payment_wizard_action(self):
        """Returns the action to open payment wizard."""
        return {
            'name': 'Register Payment',
            'type': 'ir.actions.act_window',
            'res_model': 'property.payment.register.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_installment_id': self.id, 'default_amount': self.amount_residual}
        }

