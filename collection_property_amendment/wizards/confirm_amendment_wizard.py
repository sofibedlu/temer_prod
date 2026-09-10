from odoo import models, fields, api
from markupsafe import Markup

class PropertyAmendmentConfirmWizard(models.TransientModel):
    _name = 'property.amendment.confirm.wizard'
    _description = 'Confirm Property Amendment Transfer'

    amendment_request_id = fields.Many2one('property.amendment.request', required=True)
    summary = fields.Html(string="Transfer Summary", compute="_compute_summary")

    @api.depends('amendment_request_id')
    def _compute_summary(self):
        for wizard in self:
            if not wizard.amendment_request_id:
                active_id = self.env.context.get('default_amendment_request_id') or self.env.context.get('active_id')
                req = self.env['property.amendment.request'].sudo().browse(active_id) if active_id else False
            else:
                req = wizard.amendment_request_id

            if req:
                sale_name = req.property_sale_id.name if req.property_sale_id else 'N/A'
                wizard.summary = f"""
                    <div style="padding: 15px; border-left: 4px solid #f0ad4e; background-color: #fcf8e3; margin-bottom: 10px;">
                        <strong>Entities that will be migrated and updated:</strong>
                        <ul style="margin-top: 10px;">
                            <li><b>Collection Order:</b> {req.collection_order_id.name}</li>
                            <li><b>Property Sale:</b> {sale_name} (Schedule will be UNLOCKED)</li>
                            <li><b>Reservations:</b> Automatically Migrated</li>
                            <li><b>Property Change:</b> <del>{req.old_property_id.name}</del> &rarr; <b>{req.new_property_id.name}</b></li>
                        </ul>
                        <p style="margin-top: 10px;">Approving this request will immediately execute the transfer and unlock the sale schedule.</p>
                    </div>
                """
            else:
                wizard.summary = "<p><i>Loading summary...</i></p>"

    def action_confirm_transfer(self):
        req = self.amendment_request_id
        new_prop = req.new_property_id
        old_prop = req.old_property_id
        sale = req.property_sale_id
        col_order = req.collection_order_id
        
        # Update Property Sale and UNLOCK schedule
        if sale:
            sale.property_id = new_prop.id
            sale.sale_price = new_prop.unit_price

            history = self.env['property.payment.schedule.history'].sudo().create({
                'sale_id': sale.id,
                'reason': f"Property amended from {old_prop.name} to {new_prop.name}. Reason: {req.reason}",
            })
            
            for line in sale.payment_installment_line_ids:
                self.env['property.payment.schedule.history.line'].sudo().create({
                    'history_id': history.id,
                    'name': line.payment_term_id.name if line.payment_term_id else 'Installment',
                    'expected_amount': line.expected_amount,
                    'paid_amount': line.paid_amount,
                    'expected': line.expected,
                })
            
            sale.is_schedule_unlocked = True
            sale.message_post(body=Markup(f"<b>Payment Schedule Unlocked due to Property Amendment ({req.name})</b><br/>Migrated from {old_prop.name} to {new_prop.name}"))

            # Update Reservation directly from sale
            if sale.reservation_id:
                sale.reservation_id.sudo().write({'property_id': new_prop.id})

        # Update Collection order
        if col_order:
            col_order.property_id = new_prop.id
            col_order.amount_total = new_prop.unit_price

        # 4. Update the States of both Properties
        if new_prop and old_prop:
            new_prop.sudo().write({'state': old_prop.state}) 
            old_prop.sudo().write({'state': 'available'})
            
        if col_order:
            msg = f"<b>Property Amendment Approved ({req.name})</b><ul>" \
                  f"<li><b>Old Property:</b> {old_prop.name}</li>" \
                  f"<li><b>New Property:</b> {new_prop.name}</li>" \
                  f"</ul>"
            col_order.sudo().message_post(body=Markup(msg))

        req.sudo().write({'state': 'approved'})
        
        return {'type': 'ir.actions.act_window_close'}