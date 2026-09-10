from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ProcurementProformaEvaluation(models.Model):
    _inherit = 'procurement.proforma.evaluation'

    state = fields.Selection(
        [('draft', 'Draft'), ('approved', 'Approved'), ('done', 'Done')],
        default='draft', tracking=True
    )

    approved_by_id = fields.Many2one('res.users', string='Approved By', readonly=True)
    approved_date = fields.Datetime(string='Approved Date', readonly=True)

    def action_approve(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError(_("You cannot approve an empty analysis. Please generate lines first."))

            # choosing a winner
            winners = rec.line_ids.filtered(lambda l: l.is_winner)
            if not winners:
                raise UserError(_("You must select at least one winning vendor quote before approving the analysis."))
            
            # check (total score > 0)
            for winner in winners:
                if winner.total_score <= 0.0:
                    raise UserError(_(
                        "The winning quote for '%s' has a total score of 0. "
                        "Please input the Technical and Financial values before approving."
                    ) % winner.product_id.display_name)

            rec.write({
                'state': 'approved',
                'approved_by_id': self.env.user.id,
                'approved_date': fields.Datetime.now(),
            })
            rec.message_post(body=_("Analysis Approved by %s") % self.env.user.name)


    def action_view_proforma_collection(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Proforma Collection',
            'res_model': 'procurement.proforma.analysis',
            'view_mode': 'form',
            'res_id': self.collection_id.id,
        }
        
    def action_create_rfqs(self):
        for rec in self:
            if rec.state != 'approved':
                raise UserError(_("You can only generate Purchase Orders from an Approved analysis."))
    
        res = super().action_create_rfqs()
        rfqs = self.env['purchase.order'].search([
            ('custom_evaluation_id', '=', self.id),
            ('state', 'in', ['draft', 'sent'])
        ])
        for rfq in rfqs:
            rfq.button_confirm()
        return res