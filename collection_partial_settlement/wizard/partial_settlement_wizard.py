from odoo import models, fields, api, _
from odoo.exceptions import UserError
from markupsafe import Markup

class PartialSettlementWizard(models.TransientModel):
    _name = 'partial.settlement.wizard'
    _description = 'Partial Settlement Wizard'

    collection_id = fields.Many2one('collection.order', string="Collection Order", required=True)
    installment_ids = fields.Many2many(
        'collection.installment', 
        string="Installments to Merge",
        domain="[('collection_id', '=', collection_id), ('state', '!=', 'paid')]",
        required=True
    )
    new_due_date = fields.Date(string="New Due Date", required=False, default=False)
    custom_name = fields.Char(
        string="Custom Installment Name", 
        compute="_compute_custom_name",
        store=True,
        readonly=False,
        help="Leave blank to use the default merged name."
    )

    linked_installment_id = fields.Many2one(
        'collection.installment', 
        string="Link to Installment", 
        domain="[('collection_id', '=', collection_id), ('state', '!=', 'paid'), ('id', 'not in', installment_ids)]"
    )

    @api.depends('installment_ids')
    def _compute_custom_name(self):
        for rec in self:
            if rec.installment_ids:
                names = rec.installment_ids.mapped('name')
                rec.custom_name = f"Settlement for {', '.join(names)}"
            else:
                rec.custom_name = "Settlement for"

    def action_apply_partial_settlement(self):
        self.ensure_one()

        if not self.new_due_date and not self.linked_installment_id:
            raise UserError(_("You must either select a New Due Date or link an Installment."))

        if hasattr(self.collection_id, 'has_pending_discount_request') and self.collection_id.has_pending_discount_request:
            raise UserError(_("This collection order has a pending discount request. Please resolve it before applying a partial settlement."))

        if len(self.installment_ids) <= 1:
            raise UserError(_("Please select at least two installments to merge."))

        for inst in self.installment_ids:
            if inst.state == 'paid':
                raise UserError(_("You cannot merge paid installments. Installment '%s' is already fully paid.") % inst.name)
            if inst.state == 'pending':
                raise UserError(_("You cannot merge installments that are in a 'Pending' state. Please resolve installment '%s' first.") % inst.name)
            if hasattr(inst, 'discount_amount') and inst.discount_amount > 0:
                raise UserError(_("You cannot merge installments that already have an applied discount. Installment '%s' has a discount amount of %s.") % (inst.name, inst.discount_amount))
            
        # Determine the initial due date
        initial_due_date = self.new_due_date
        if self.linked_installment_id and not self.new_due_date:
            initial_due_date = self.linked_installment_id.due_date

        total_amount = sum(self.installment_ids.mapped('amount_total'))

        if self.custom_name:
            new_installment_name = self.custom_name
        else:
            new_installment_name = _("Partial Settlement (%s Installments)") % len(self.installment_ids)
        
        # new folded installment
        new_installment = self.env['collection.installment'].sudo().create({
            'collection_id': self.collection_id.id,
            'name': self.custom_name,
            'amount_total': total_amount,
            'due_date': initial_due_date,
            'state': 'unpaid',
            'linked_installment_id': self.linked_installment_id.id if self.linked_installment_id else False,
        })

        # Session record for grouping/history
        session = self.env['partial.settlement.session'].sudo().create({
            'name': new_installment_name,
            'collection_id': self.collection_id.id,
            'new_installment_amount': total_amount,
        })

        # Handle History and Transfer Payments
        old_installment_names = []
        for inst in self.installment_ids:
            old_installment_names.append(inst.name)
            self.env['collection.installment.history'].sudo().create({
                'session_id': session.id,
                'name': inst.name,
                'due_date': inst.due_date,
                'amount_total': inst.amount_total,
                'amount_paid': inst.amount_paid,
                'amount_residual': inst.amount_residual,
                'discount_amount': inst.discount_amount,
                'state': inst.state,
            })

            # Transfer payments 
            if inst.payment_ids:
                inst.payment_ids.sudo().write({
                    'installment_id': new_installment.id
                })
            
        # unlink the old installments
        self.installment_ids.sudo().unlink()

        msg_date = initial_due_date if initial_due_date else "Linked to " + self.linked_installment_id.name
        msg = f"""
            <b>Partial Settlement Applied</b><br/>
            <b>Merged Installments:</b> {", ".join(old_installment_names)}<br/>
            <b>Resulting Installment:</b> {new_installment_name}<br/>
            <b>Amount:</b> {total_amount:,.2f}<br/>
            <b>Due Date / Link:</b> {msg_date}
        """
        self.collection_id.sudo().message_post(body=Markup(msg))

        return {'type': 'ir.actions.act_window_close'}