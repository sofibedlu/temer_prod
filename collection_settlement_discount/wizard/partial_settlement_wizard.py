from odoo import models, fields, api, _
from odoo.exceptions import UserError
from markupsafe import Markup

class PartialSettlementWizard(models.TransientModel):
    _inherit = 'partial.settlement.wizard'

    apply_discount_request = fields.Boolean(string="Apply Discount Request")
    agreed_settlement_amount = fields.Float(string="Agreed Settlement Amount")
    discount_target_installment_id = fields.Many2one(
        'collection.installment', 
        string="Target Installment",
        domain="[('collection_id', '=', collection_id), ('state', '!=', 'paid'), ('id', 'not in', installment_ids)]"
    )
    discount_percentage = fields.Float(string="Discount (%)")
    discount_amount = fields.Float(string="Discount Amount")
    discount_reason = fields.Text(string="Reason")
    discount_attachment_ids = fields.Many2many('ir.attachment', string="Attachments")

    extra_discount_installment_ids = fields.Many2many(
        'collection.installment',
        'wizard_extra_discount_rel',
        string="Fallback Target Installments",
        domain="[('collection_id', '=', collection_id), ('state', '!=', 'paid'), ('id', 'not in', installment_ids), ('id', '!=', discount_target_installment_id)]"
    )

    needs_fallback_installments = fields.Boolean(
        string="Needs Fallback",
        compute="_compute_needs_fallback"
    )

    @api.onchange('installment_ids')
    def _onchange_installment_ids_agreed_amount(self):
        """ Default Agreed amount to the sum of selected folded installments. """
        for rec in self:
            rec.agreed_settlement_amount = sum(rec.installment_ids.mapped('amount_residual'))

    @api.onchange('apply_discount_request', 'installment_ids')
    def _onchange_apply_discount_request(self):
        for rec in self:
            if rec.apply_discount_request and rec.collection_id:
                excluded_ids = rec.installment_ids.ids if rec.installment_ids else []
                domain = [
                    ('collection_id', '=', rec.collection_id.id),
                    ('state', '!=', 'paid'),
                    ('id', 'not in', excluded_ids)
                ]
                last_inst = self.env['collection.installment'].search(
                    domain, order='sequence desc, id desc', limit=1
                )
                if last_inst:
                    rec.discount_target_installment_id = last_inst.id
            else:
                rec.discount_target_installment_id = False
                rec.discount_percentage = 0.0
                rec.discount_reason = False
    
    @api.onchange('discount_percentage', 'agreed_settlement_amount')
    def _onchange_discount_percentage(self):
        for rec in self:
            if rec.discount_target_installment_id:
                base = self.agreed_settlement_amount
                if base:
                    rec.discount_amount = rec.discount_percentage * base / 100.0

    @api.onchange('discount_amount', 'agreed_settlement_amount')
    def _onchange_discount_amount(self):
        for rec in self:
            if rec.discount_target_installment_id:
                base = self.agreed_settlement_amount
                if base:
                    rec.discount_percentage = (rec.discount_amount / base) * 100.0

    @api.depends('discount_amount', 'discount_target_installment_id')
    def _compute_needs_fallback(self):
        for rec in self:
            if rec.apply_discount_request and rec.discount_target_installment_id and rec.discount_amount:
                residual = rec.discount_target_installment_id.amount_residual or 0.0
                rec.needs_fallback_installments = rec.discount_amount > residual
            else:
                rec.needs_fallback_installments = False

    def action_apply_partial_settlement(self):
        if self.apply_discount_request:
            if not self.discount_target_installment_id:
                raise UserError(_("Please select a target installment for the discount."))
            
            target_residual = self.discount_target_installment_id.amount_residual or 0.0
            total_available_residual = target_residual

            if self.needs_fallback_installments:
                if not self.extra_discount_installment_ids:
                    raise UserError(_("The discount amount exceeds the target installment's remaining amount. Please select fallback target installments."))
                total_available_residual += sum(self.extra_discount_installment_ids.mapped('amount_residual'))
                
            if self.discount_amount > total_available_residual:
                diff = self.discount_amount - total_available_residual
                raise UserError(_(
                    "The calculated discount amount (%(disc)s) cannot be fully consumed by the target and fallback installments. "
                    "You need an additional %(diff)s available amount to cover the discount. Please adjust the installments."
                ) % {'disc': self.discount_amount, 'diff': diff})
            
            # 1. Determine Initial Due Date
            initial_due_date = self.new_due_date
            if self.linked_installment_id and not self.new_due_date:
                initial_due_date = self.linked_installment_id.due_date

            request = self.env['discount.request'].sudo().create({
                'collection_id': self.collection_id.id,
                'installment_id': self.discount_target_installment_id.id,
                'extra_discount_installment_ids': [(6, 0, self.extra_discount_installment_ids.ids)],
                'discount_percentage': self.discount_percentage,
                'agreed_settlement_amount': self.agreed_settlement_amount,
                'reason': self.discount_reason,
                'attachment_ids': [(6, 0, self.discount_attachment_ids.ids)],
                'state': 'draft',
                'pending_installment_ids': [(6, 0, self.installment_ids.ids)],
                'merge_due_date': initial_due_date,
                'merge_custom_name': self.custom_name,
                'merge_linked_installment_id': self.linked_installment_id.id if self.linked_installment_id else False,
            })
            
            for att in self.discount_attachment_ids:
                att.sudo().write({
                    'res_model': 'discount.request', 
                    'res_id': request.id
                })
                
            request.action_submit()
            return {'type': 'ir.actions.act_window_close'}
            
        else:
            # If no discount requested, call the original partial settlement merge immediately
            return super(PartialSettlementWizard, self).action_apply_partial_settlement()


class DiscountRequest(models.Model):
    _inherit = 'discount.request'

    # hold the installments waiting to be merged
    pending_installment_ids = fields.Many2many(
        'collection.installment', 
        'discount_pending_installment_rel', 
        string='Selected for Folding',
        help="Installments selected to be merged once this request is approved."
    )
    merge_due_date = fields.Date(string="Merge Due Date")
    merge_custom_name = fields.Char(string="Merged Custom Name")

    source_merged_installment_id = fields.Many2one(
        'collection.installment', 
        string='Source Merged Settlement',
        readonly=True,
    )

    settlement_session_id = fields.Many2one(
        'partial.settlement.session',
        string="Settlement Session",
        readonly=True
    )
    
    folded_installment_history_ids = fields.One2many(
        related='settlement_session_id.history_line_ids',
        string="Folded Installments",
        readonly=True
    )

    agreed_settlement_amount = fields.Monetary(
        string='Agreed Settlement Amount',
        help='Used as the base for discount calculation if the request originated from a partial settlement.'
    )

    has_pending_installments = fields.Boolean(
        compute='_compute_has_pending_installments', 
        string="Has Pending Installments"
    )

    extra_discount_installment_ids = fields.Many2many(
        'collection.installment',
        'discount_extra_inst_rel',
        string="Fallback Target Installments",
        readonly=True,
        states={'draft': [('readonly', False)]}
    )
    allocation_ids = fields.One2many(
        'discount.request.allocation',
        'request_id',
        string="Discount Allocations",
        readonly=True
    )

    target_installments_text = fields.Char(
        string="Target Installments", 
        compute="_compute_target_installments_text"
    )
    
    preview_allocation_ids = fields.One2many(
        'discount.request.preview.line',
        'request_id',
        string="Possible Discount Allocation",
        compute="_compute_preview_allocation_ids",
        store=True
    )

    merge_linked_installment_id = fields.Many2one('collection.installment', string="Merge Linked Installment")

    @api.depends('installment_id', 'extra_discount_installment_ids')
    def _compute_target_installments_text(self):
        for req in self:
            names = []
            if req.installment_id:
                names.append(req.installment_id.name)
            for inst in req.extra_discount_installment_ids:
                names.append(inst.name)
            req.target_installments_text = ", ".join(names)

    @api.depends('discount_amount', 'installment_id', 'extra_discount_installment_ids')
    def _compute_preview_allocation_ids(self):
        for req in self:
            commands = [(5, 0, 0)]
            remaining_discount = req.discount_amount or 0.0

            targets = []
            if req.installment_id:
                targets.append(req.installment_id)
            if req.extra_discount_installment_ids:
                # maintain the explicit list order
                targets.extend(list(req.extra_discount_installment_ids))

            for inst in targets:
                if remaining_discount <= 0:
                    break
                
                residual = inst.amount_residual or 0.0
                apply_amt = min(remaining_discount, residual)
                rem_after = residual - apply_amt

                commands.append((0, 0, {
                    'installment_id': inst.id,
                    'applied_discount': apply_amt,
                    'remaining_amount': round(rem_after, 2),
                }))

                remaining_discount -= apply_amt

            req.preview_allocation_ids = commands

    @api.depends('pending_installment_ids')
    def _compute_has_pending_installments(self):
        for rec in self:
            rec.has_pending_installments = bool(rec.pending_installment_ids)

    @api.depends('discount_percentage', 'installment_id.amount_total', 'installment_id.amount_paid', 'state', 'agreed_settlement_amount')
    def _compute_discount_amount(self):
        for rec in self:
            if rec.state in ['approved', 'rejected'] and rec.discount_amount > 0:
                continue
            
            # custom base
            if rec.agreed_settlement_amount > 0 and rec.installment_id:
                rec.discount_amount = rec.agreed_settlement_amount * (rec.discount_percentage / 100.0)

            # The remaining amount
                target_base = rec.installment_id.amount_total - rec.installment_id.amount_paid
                rec.remaining_amount = target_base - rec.discount_amount
            # original fallback logic
            elif rec.installment_id:
                base_amount = rec.installment_id.amount_total - rec.installment_id.amount_paid
                rec.discount_amount = base_amount * (rec.discount_percentage / 100.0)
                rec.remaining_amount = base_amount - rec.discount_amount
            else:
                rec.discount_amount = 0.0
                rec.remaining_amount = 0.0

    def action_approve(self):
        """ Update action_approve to execute folding before processing discount approval """
        for req in self:
            if req.pending_installment_ids and not req.settlement_session_id:
                total_amount = sum(req.pending_installment_ids.mapped('amount_total'))
                
                # prevent errors during merge
                for inst in req.pending_installment_ids:
                    if inst.discount_amount > 0:
                        raise UserError(_("You cannot merge installments that already have an applied discount. Installment '%s' has a discount amount.") % inst.name)
                
                new_installment_name = req.merge_custom_name if req.merge_custom_name else _("Partial Settlement (%s Installments)") % len(req.pending_installment_ids)
                
                # Create the new merged installment
                new_installment = self.env['collection.installment'].sudo().create({
                    'collection_id': req.collection_id.id,
                    'name': new_installment_name,
                    'amount_total': total_amount,
                    'due_date': req.merge_due_date,
                    'state': 'unpaid',
                    'linked_installment_id': req.merge_linked_installment_id.id if req.merge_linked_installment_id else False,
                })
                
                # Create Session and History Lines
                session = self.env['partial.settlement.session'].sudo().create({
                    'name': new_installment_name,
                    'collection_id': req.collection_id.id,
                    'new_installment_amount': total_amount,
                })
                
                for inst in req.pending_installment_ids:
                    self.env['collection.installment.history'].sudo().create({
                        'session_id': session.id,
                        'name': inst.name,
                        'due_date': inst.due_date,
                        'amount_total': inst.amount_total,
                        'amount_paid': inst.amount_paid,
                        'amount_residual': inst.amount_residual,
                        'discount_amount': inst.discount_amount,
                        'state': inst.state
                    })
                
                    # Transfer any existing payments to the newly merged installment
                    if inst.payment_ids:
                        inst.payment_ids.sudo().write({
                            'installment_id': new_installment.id
                        })
                
                # Delete original folded installments
                req.pending_installment_ids.sudo().unlink()

                # Link new folded installment back to discount request
                req.write({
                    'source_merged_installment_id': new_installment.id,
                    'settlement_session_id': session.id
                })
            
            # Check status before applying discount allocations
            if req.state != 'pending':
                raise UserError(_("Only pending requests can be approved."))
            
            req.state = 'approved'
            applied_amount = req.discount_amount
            remaining_to_apply = applied_amount

            allocated_details_msg = []
            
            # Apply to target installment first
            target_residual = req.installment_id.amount_residual or 0.0
            amount_for_target = min(remaining_to_apply, target_residual)
            
            if amount_for_target > 0:
                req.installment_id.sudo().write({'discount_amount': req.installment_id.discount_amount + amount_for_target})
                remaining_to_apply -= amount_for_target
                
                self.env['discount.request.allocation'].sudo().create({
                    'request_id': req.id,
                    'collection_id': req.collection_id.id,
                    'installment_id': req.installment_id.id,
                    'amount': amount_for_target,
                })
                allocated_details_msg.append(f"<li>{req.installment_id.name}: {amount_for_target}</li>")

            # Route overflow to extra installments in the selected order
            if remaining_to_apply > 0 and req.extra_discount_installment_ids:
                extras = req.extra_discount_installment_ids
                for inst in extras:
                    if remaining_to_apply <= 0: break
                    inst_residual = inst.amount_residual or 0.0
                    amount_for_inst = min(remaining_to_apply, inst_residual)
                    
                    if amount_for_inst > 0:
                        inst.sudo().write({'discount_amount': inst.discount_amount + amount_for_inst})
                        remaining_to_apply -= amount_for_inst
                        
                        self.env['discount.request.allocation'].sudo().create({
                            'request_id': req.id,
                            'collection_id': req.collection_id.id,
                            'installment_id': inst.id,
                            'amount': amount_for_inst,
                        })
                        allocated_details_msg.append(f"<li>{inst.name}: {amount_for_inst}</li>")

            # Log
            msg = Markup(
                "<b>Discount Request Approved & Allocated</b><br/>"
                "Total Discount Applied: {:.2f}<br/>"
                "<b>Allocations:</b><ul>{}</ul>"
            ).format(applied_amount, Markup("".join(allocated_details_msg)))
            
            req.collection_id.sudo().message_post(body=msg)
            
        return True

        # apply the discount to the configured target_installment
        #return super(DiscountRequest, self).action_approve()