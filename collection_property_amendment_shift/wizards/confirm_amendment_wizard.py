from odoo import models, fields, api

class PropertyAmendmentConfirmWizard(models.TransientModel):
    _inherit = 'property.amendment.confirm.wizard'

    @api.depends('amendment_request_id')
    def _compute_summary(self):
        super()._compute_summary()
        for wizard in self:
            req = wizard.amendment_request_id
            if not req:
                active_id = self.env.context.get('default_amendment_request_id') or self.env.context.get('active_id')
                req = self.env['property.amendment.request'].sudo().browse(active_id) if active_id else False

            # Inject the Site Shift warning into the inherited HTML
            if req and req.is_site_shift and wizard.summary:
                shift_warning = f"<li style='color: #d9534f;'><b>WARNING: SITE SHIFT DETECTED!</b> Transferring from <b>{req.site_id.name}</b> to <b>{req.new_site_id.name}</b></li>"
                wizard.summary = wizard.summary.replace('<li><b>Reservations:</b>', f'{shift_warning}<li><b>Reservations:</b>')

    def action_confirm_transfer(self):
        res = super().action_confirm_transfer()

        # new tracking flags
        req = self.amendment_request_id
        if req.is_site_shift:
            if req.property_sale_id:
                req.property_sale_id.sudo().write({'is_site_shifted': True})
            if req.collection_order_id:
                req.collection_order_id.sudo().write({'is_site_shifted': True})

        return res