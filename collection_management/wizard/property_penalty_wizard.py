from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import Markup
from ..models.access_control import require_feature
import logging
_logger = logging.getLogger(__name__)

class PropertyPenaltyApplyWizard(models.TransientModel):
    _name = 'property.penalty.apply.wizard'
    _description = 'Apply Penalty Wizard'

    collection_id = fields.Many2one('collection.order', string='Collection', required=True)
    installment_id = fields.Many2one(
        'collection.installment',
        string='Installment',
        required=True,
        domain="[('collection_id','=',collection_id), ('state','=','overdue'), ('penalty_applied','=',False)]"
    )
    percent = fields.Float(string='Penalty %', default=3.0, required=True)
    preview_amount = fields.Monetary(string='Computed Penalty', compute='_compute_preview', store=False, currency_field='currency_id')
    reason = fields.Text(string='Reason', required=True)
    currency_id = fields.Many2one('res.currency', related='collection_id.currency_id')

    @api.depends('installment_id', 'percent')
    def _compute_preview(self):
        for rec in self:
            if rec.installment_id:
                base_amount = rec.installment_id.amount_residual or 0.0
                currency = rec.currency_id or rec.collection_id.currency_id or rec.env.company.currency_id
                rec.preview_amount = currency.round(base_amount * (rec.percent / 100.0))
            else:
                rec.preview_amount = 0.0

    def action_confirm_apply(self):
        self.ensure_one()
        require_feature(self.env, "penalty_manage", message="You are not allowed to apply penalties.")

        if self.preview_amount <= 0:
            raise UserError(_("Penalty amount must be greater than zero."))
        self.installment_id.sudo().apply_manual_penalty(self.preview_amount, self.reason)
        if self.collection_id:
            self.collection_id.sudo().message_post(body=Markup(
                "<b>Penalty Applied</b><br/>Installment: %s<br/>Penalty Added: %s (%s%%)<br/>Reason: %s"
            ) % (self.installment_id.name, self.preview_amount, self.percent, self.reason))
        return {'type': 'ir.actions.act_window_close'}
