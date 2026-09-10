from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_custom_procurement = fields.Boolean(
        compute='_compute_is_custom_procurement', 
        store=True, 
        string="Is Custom Procurement"
    )

    technical_approved = fields.Boolean(string='Technical Requirements Met', default=False, tracking=True, copy=False)
    technical_approved_by = fields.Many2one('res.users', string='Technical Checker', readonly=True, copy=False)
    technical_approval_date = fields.Datetime(string='Technical Checked On', readonly=True, copy=False)

    @api.depends('purchase_id.custom_evaluation_id')
    def _compute_is_custom_procurement(self):
        for picking in self:
            picking.is_custom_procurement = bool(picking.purchase_id and picking.purchase_id.custom_evaluation_id)

    def action_technical_approve(self):
        for picking in self:
            picking.technical_approved = True
            picking.technical_approved_by = self.env.user.id
            picking.technical_approval_date = fields.Datetime.now()
            picking.message_post(body="Technical requirements of the received goods have been verified and approved.")

    def button_validate(self):
        for picking in self:
            if picking.picking_type_code == 'incoming' and picking.is_custom_procurement and not picking.technical_approved:
                raise ValidationError(_("You must verify and approve the Technical Specifications before receiving these products into stock."))
                
        return super(StockPicking, self).button_validate()