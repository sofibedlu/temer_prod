from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.modules.module import get_module_resource
from markupsafe import Markup
from .access_control import require_feature
import base64
import logging
_logger = logging.getLogger(__name__)

class CollectionInstallment(models.Model):
    _name = 'collection.installment'
    _description = 'Collection Installment Line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'due_date asc, id asc'

    collection_id = fields.Many2one('collection.order', string='Collection Order', ondelete='cascade')
    name = fields.Char(string='Description', required=True)
    amount_total = fields.Monetary(string='Total Amount', currency_field='currency_id')
    amount_paid = fields.Monetary(string='Paid Amount', compute='_compute_amount_paid', store=True, currency_field='currency_id')
    amount_residual = fields.Monetary(string='Remaining Amount', compute='_compute_residual', store=True, currency_field='currency_id')
    
    currency_id = fields.Many2one('res.currency', related='collection_id.currency_id')
    due_date = fields.Date(
        string='Due Date', 
        tracking=True, 
        states={'paid': [('readonly', True)]}
    )
    payment_schedule_type = fields.Selection(
        [('progress', 'Progress Based'), ('time', 'Time Based')],
        compute='_compute_payment_schedule_type',
        readonly=True
    )

    extended_date = fields.Date(string='Extended Due Date', tracking=True)
    remark = fields.Text(string='Remark')
    is_progress_based = fields.Boolean(string='Progress Based', default=False)
    penalty_amount = fields.Monetary(string='Penalty Amount', currency_field='currency_id', default=0.0, help="Amount of penalty added to this installment.")
    penalty_applied = fields.Boolean(string='Penalty Applied', default=False, help="Indicates if a penalty has been manually applied.")
    discount_amount = fields.Monetary(string='Discount Amount', currency_field='currency_id', default=0.0, help="Amount of discount applied to this installment.")
    partner_id = fields.Many2one(related='collection_id.partner_id', store=True, string='Customer')
    property_id = fields.Many2one(related='collection_id.property_id', store=True, string='Property')
    site_id = fields.Many2one(related='property_id.site', store=True, string='Site/Project')
    payment_ids = fields.One2many('collection.installment.payment', 'installment_id', string='Payments', readonly=True)

    state = fields.Selection([
        ('unpaid', 'Unpaid'),
        ('partial', 'Partial'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue')
    ], string='Status', default='unpaid', compute='_compute_state', store=True)
    payment_term_line_id = fields.Many2one(
        'property.payment.term.line', 
        string='Milestone / Term',
        help="The configuration line this installment was created from."
    )

    def _get_default_can_edit_due_date(self):
        return self.env.user.has_group("collection_management.group_collection_due_date_editor")
    can_edit_due_date = fields.Boolean(
        default=_get_default_can_edit_due_date, 
        store=False
    )

    @api.depends('collection_id')
    def _compute_payment_schedule_type(self):
        for rec in self:
            rec.payment_schedule_type = rec.collection_id.payment_schedule_type

    @api.constrains('due_date', 'collection_id')
    def _check_due_date_required_for_time_based(self):
        for rec in self:
            if rec.collection_id and rec.collection_id.payment_schedule_type == 'time' and not rec.due_date:
                raise ValidationError(_("Due Date is required when Payment Schedule Type is Time Based."))
    
    @api.depends('amount_total', 'amount_paid', 'penalty_amount', 'discount_amount')
    def _compute_residual(self):
        for rec in self:
            rec.amount_residual = (rec.amount_total + rec.penalty_amount) - rec.amount_paid - rec.discount_amount
    
    @api.depends('payment_ids.amount', 'payment_ids.status')
    def _compute_amount_paid(self):
        """
        Compute the total amount paid. 
        Only consider payments with status 'paid'.
        """
        for rec in self:
            paid_payments = rec.payment_ids.filtered(lambda p: p.status == 'paid')
            rec.amount_paid = sum(paid_payments.mapped('amount') or [0.0])

    @api.depends('amount_residual', 'due_date', 'amount_paid')
    def _compute_state(self):
        """
        Compute the installment state.
        """
        today = fields.Date.today()
        for rec in self:
            if rec.amount_residual <= 0:
                rec.state = 'paid'
            elif rec.due_date and rec.due_date < today:
                rec.state = 'overdue'
            elif rec.amount_paid > 0:
                rec.state = 'partial'
            else:
                rec.state = 'unpaid'
            
            if rec.collection_id and rec.collection_id.state == 'active':
                rec.collection_id._check_and_update_completed_status()
    
    def write(self, vals):
        if 'due_date' in vals:
            for rec in self:
                if rec.state == 'paid':
                    raise UserError(_("You cannot change the Due Date of a paid installment (%s).") % rec.name)
                
        old_dates = {}
        if 'due_date' in vals:
            for rec in self:
                old_dates[rec.id] = rec.due_date

        res = super(CollectionInstallment, self).write(vals)
        if 'due_date' in vals:
            source = self.env.context.get('due_date_update_source', 'manual')
            if source == 'extension':
                return res

            for rec in self:
                if not rec.collection_id:
                    continue
                    
                old_d = old_dates.get(rec.id)
                new_d = vals.get('due_date')
                if old_d != new_d:
                    old_str = str(old_d) if old_d else "Not Set"
                    new_str = str(new_d) if new_d else "Not Set"
                    msg = ""

                    if source == 'manual':
                        msg = Markup(_("Installment <b>%s</b>: Due Date changed manually from %s to %s.")) % (rec.name, old_str, new_str)
                    elif source == 'progress':
                        ref = self.env.context.get('progress_ref', 'Construction Progress')
                        msg = Markup(_("Installment <b>%s</b>: Due Date updated by %s from %s to %s.")) % (rec.name, ref, old_str, new_str)
                    elif source == 'batch_milestone':
                        msg = Markup(_("Installment <b>%s</b>: Due Date batch updated from %s to %s.")) % (rec.name, old_str, new_str)

                    if msg:
                        rec.collection_id.message_post(body=msg)

        return res
    
    def apply_manual_penalty(self, amount, reason):
        """ Applies a specific penalty amount to the installment and logs it on the collection. """
        self.ensure_one()
        if amount <= 0:
            raise UserError(_("Penalty amount must be greater than zero."))

        if self.penalty_applied:
            raise UserError(_("Penalty already applied on installment %s.") % self.name)

        self.sudo().write({
            'penalty_amount': amount,
            'penalty_applied': True,
            'remark': (self.remark or '') + f"\n[Penalty Applied] {amount} - {reason}"
        })

        return True

    def action_reset_penalty(self):
        """Reset the penalty on this installment (remove penalty from total)."""
        require_feature(self.env, "penalty_manage", message="You are not allowed to reset penalties.")
        for rec in self:
            if rec.penalty_applied and rec.penalty_amount > 0:
                amount_to_remove = rec.penalty_amount
                rec.sudo().write({
                    'penalty_amount': 0.0,
                    'penalty_applied': False,
                    'remark': (rec.remark or '') + f"\n[Penalty Reset] {amount_to_remove}"
                })
                if rec.collection_id:
                    rec.collection_id.sudo().message_post(body=f"Penalty of {amount_to_remove} reset for installment '{rec.name}'")
        return True

    def action_open_apply_penalty_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Apply Penalty',
            'res_model': 'property.penalty.apply.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_installment_id': self.id, 
                'default_collection_id': self.collection_id.id if self.collection_id else False
            }
        }
    

    def action_open_payment_wizard(self):
        """Opens the existing Payment Register Wizard."""
        self.ensure_one()
        require_feature(self.env, "payment_initiate", message="You are not allowed to initiate payments.")
        return {
            'name': 'Register Payment',
            'type': 'ir.actions.act_window',
            'res_model': 'property.payment.register.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_installment_id': self.id, 'default_amount': self.amount_residual}
        }

    def action_open_letter_wizard(self):
        """Opens the existing Letter Print Wizard."""
        self.ensure_one()
        return {
            'name': 'Print Letter',
            'type': 'ir.actions.act_window',
            'res_model': 'property.contract.print.letter.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_installment_id': self.id}
        }

    @api.model
    def _cron_update_overdue_status(self):
        """
        Cron method called daily to update the state of installments 
        that have passed their due date.
        """
        today = fields.Date.today()
        overdue_candidates = self.search([
            ('state', 'in', ['unpaid', 'partial']),
            ('due_date', '<', today)
        ])

        if overdue_candidates:
            overdue_candidates._compute_state()
            _logger.info(f"Cron: Updated {len(overdue_candidates)} installments to Overdue status.")

    def get_stamp_image(self):
        """Reads the static stamp image and returns it as base64 string."""
        image_path = get_module_resource('collection_management', 'static/src/img/filtema_stamp.png')
        if image_path:
            with open(image_path, 'rb') as f:
                return base64.b64encode(f.read()).decode('utf-8')
        return ''