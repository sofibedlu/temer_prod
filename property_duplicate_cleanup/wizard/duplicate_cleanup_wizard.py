from odoo import models, fields, api, _
from odoo.exceptions import UserError
from markupsafe import Markup

class PropertyDuplicateCleanupWizard(models.TransientModel):
    _name = 'property.duplicate.cleanup.wizard'
    _description = 'Property Duplicate Cleanup Wizard'

    valid_property_id = fields.Many2one('property.property', string="Valid Property (Target)", required=True, domain="[('is_invalid_duplicate', '=', False)]")
    invalid_property_id = fields.Many2one('property.property', string="Invalid Property (Source)", required=True)

    valid_summary = fields.Html(string="Valid Property Data", compute="_compute_summaries")
    invalid_summary = fields.Html(string="Invalid Property Data", compute="_compute_summaries")

    transfer_reservations = fields.Boolean(string="Transfer Reservations (And Payments)", default=True)
    
    update_valid_sale_reservation = fields.Boolean(
        string="Link Existing Contract to Transferred Reservation", 
        default=True,
        help="If the Valid Property already has a Contract (Property Sale), this will update its reservation link to point to the Real Reservation you are transferring."
    )
    
    transfer_sales = fields.Boolean(string="Transfer Property Sales (Contracts)", default=False)
    transfer_collections = fields.Boolean(string="Transfer Collection Orders", default=False)

    @api.depends('valid_property_id', 'invalid_property_id')
    def _compute_summaries(self):
        for rec in self:
            rec.valid_summary = rec._build_summary_html(rec.valid_property_id)
            rec.invalid_summary = rec._build_summary_html(rec.invalid_property_id)

    def _build_summary_html(self, prop):
        if not prop:
            return Markup("<p class='text-muted mt-2'><i>Select a property to view data...</i></p>")
        
        # Fetch the actual records
        reservations = self.env['property.reservation'].search([('property_id', '=', prop.id)])
        sales = self.env['property.sale'].search([('property_id', '=', prop.id)])
        collections = self.env['collection.order'].search([('property_id', '=', prop.id)])
        
        # Bootstrap badges for the names
        def get_tags(records, color_class):
            if not records:
                return '<span class="text-muted" style="font-size: 0.85em;">None</span>'
            return "".join([
                f'<span class="badge {color_class} fw-normal text-wrap text-start">{rec.display_name}</span>' 
                for rec in records
            ])
        
        res_html = get_tags(reservations, 'bg-primary')
        sale_html = get_tags(sales, 'bg-success')
        col_html = get_tags(collections, 'bg-danger')
        
        # card layout
        html = f"""
            <div class="card bg-light border-0 shadow-sm mt-2">
                <div class="card-body p-3">
                    <h6 class="card-title text-dark mb-3 border-bottom pb-2">
                        <i class="fa fa-building-o me-2 text-muted"></i><b>{prop.display_name}</b>
                    </h6>
                    <div class="row g-2">
                        
                        <!-- Reservations Column -->
                        <div class="col-4">
                            <div class="text-muted mb-2" style="font-size: 0.85em; font-weight: bold;">
                                Reservations ({len(reservations)})
                            </div>
                            <div class="d-flex flex-wrap gap-1" style="max-height: 120px; overflow-y: auto;">
                                {res_html}
                            </div>
                        </div>
                        
                        <!-- Sales Column -->
                        <div class="col-4 border-start">
                            <div class="text-muted mb-2" style="font-size: 0.85em; font-weight: bold;">
                                Sales ({len(sales)})
                            </div>
                            <div class="d-flex flex-wrap gap-1" style="max-height: 120px; overflow-y: auto;">
                                {sale_html}
                            </div>
                        </div>
                        
                        <!-- Collections Column -->
                        <div class="col-4 border-start">
                            <div class="text-muted mb-2" style="font-size: 0.85em; font-weight: bold;">
                                Collections ({len(collections)})
                            </div>
                            <div class="d-flex flex-wrap gap-1" style="max-height: 120px; overflow-y: auto;">
                                {col_html}
                            </div>
                        </div>
                        
                    </div>
                </div>
            </div>
        """
        return Markup(html)

    def action_execute_transfer(self):
        self.ensure_one()

        if self.valid_property_id.id == self.invalid_property_id.id:
            raise UserError(_("The Valid Property and Invalid Property cannot be the same!"))

        valid_prop = self.valid_property_id
        invalid_prop = self.invalid_property_id
        logs = []

        # Transfer Reservations
        if self.transfer_reservations:
            reservations = self.env['property.reservation'].search([('property_id', '=', invalid_prop.id)])
            if reservations:
                for res in reservations:
                    res.write({'property_id': valid_prop.id})
                logs.append(f"Transferred {len(reservations)} Reservation(s).")
                
                # Relink Valid Property's Contract to the newly transferred Real Reservation
                if self.update_valid_sale_reservation:
                    valid_sales = self.env['property.sale'].search([('property_id', '=', valid_prop.id)])
                    if valid_sales:

                        # Prioritize the reservation that is actually 'sold'
                        best_reservations = reservations.filtered(lambda r: getattr(r, 'status', '') == 'sold')
                        
                        if not best_reservations:
                            best_reservations = reservations.filtered(lambda r: getattr(r, 'status', '') in ['reserved', 'pending_sales'])
                            
                        if not best_reservations:
                            non_canceled = reservations.filtered(lambda r: getattr(r, 'status', '') != 'canceled')
                            best_reservations = non_canceled if non_canceled else reservations

                        # select most relevant one
                        target_res = best_reservations[0]
                        target_res_id = target_res.id
                        
                        # Find any OLD/INVALID sales pointing to this reservation and make them NULL
                        conflicting_sales = self.env['property.sale'].search([
                            ('reservation_id', '=', target_res_id),
                            ('id', 'not in', valid_sales.ids)
                        ])
                        for bad_sale in conflicting_sales:
                            bad_sale.write({'reservation_id': False})
                            
                        # link the valid sales safely AND sync the salesperson
                        for sale in valid_sales:
                            sale_update_vals = {
                                'reservation_id': target_res_id
                            }
                            
                            # If the real reservation has a salesperson, pass it to the contract!
                            if target_res.salesperson_ids:
                                sale_update_vals['sales_person'] = target_res.salesperson_ids.id
                                
                            sale.write(sale_update_vals)
                            
                        logs.append(f"Linked Valid Property Sale(s) to real reservation and synchronized Salesperson.")
                        
                        if conflicting_sales:
                            logs.append(f"Unlinked {len(conflicting_sales)} old invalid sale(s) to fix singleton errors.")

        # Transfer Property Sales
        if self.transfer_sales:
            sales = self.env['property.sale'].search([('property_id', '=', invalid_prop.id)])
            if sales:
                for sale in sales:
                    sale.write({'property_id': valid_prop.id})
                logs.append(f"Transferred {len(sales)} Property Sale(s).")

        # Transfer Collection Orders
        if self.transfer_collections:
            collections = self.env['collection.order'].search([('property_id', '=', invalid_prop.id)])
            if collections:
                for col in collections:
                    col.write({'property_id': valid_prop.id})
                logs.append(f"Transferred {len(collections)} Collection Order(s).")

        # Flag the Invalid Property
        invalid_prop.write({'is_invalid_duplicate': True})
        logs.append(f"Flagged '{invalid_prop.name}' as Invalid Duplicate.")

        # Post summary to the Valid Property Chatter
        if logs:
            log_text = "<br/>".join(logs)
            valid_prop.message_post(body=Markup(f"<b>Data Recovery / Cleanup:</b><br/>Merged data from invalid duplicate '{invalid_prop.name}'.<br/>{log_text}"))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Cleanup Complete',
                'message': f"Successfully executed cleanup and flagged {invalid_prop.name} as invalid.",
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }