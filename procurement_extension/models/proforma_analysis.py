from odoo import models, fields, api, _

class ProcurementProformaAnalysis(models.Model):
    _inherit = 'procurement.proforma.analysis'

    has_duplicate_po_warning = fields.Boolean(compute='_compute_duplicate_po_warning')
    duplicate_po_warning_text = fields.Char(compute='_compute_duplicate_po_warning')

    procurement_count = fields.Integer(compute='_compute_procurement_count')

    @api.depends('procurement_ids')
    def _compute_procurement_count(self):
        for rec in self:
            rec.procurement_count = len(rec.procurement_ids)

    def action_view_procurement_requests(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Requests',
            'res_model': 'procurement.request',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.procurement_ids.ids)],
        }

    @api.depends('line_ids.product_id', 'procurement_ids', 'state')
    def _compute_duplicate_po_warning(self):
        for rec in self:
            rec.has_duplicate_po_warning = False
            rec.duplicate_po_warning_text = ""

            if rec.state == 'done' or not rec.procurement_ids or not rec.line_ids:
                continue
                
            # Exclude POs that originated from THIS specific collection
            domain = [
                ('order_id.custom_evaluation_id.procurement_ids', 'in', rec.procurement_ids.ids),
                ('order_id.state', '!=', 'cancel')
            ]
            
            # Handle real records
            if isinstance(rec.id, int): 
                domain.append(('order_id.custom_evaluation_id.collection_id', '!=', rec.id))

            po_lines = self.env['purchase.order.line'].search(domain)
            ordered_product_ids = po_lines.mapped('product_id.id')
            
            duplicate_products = rec.line_ids.filtered(
                lambda l: l.product_id.id in ordered_product_ids
            ).mapped('product_id.display_name')
            
            duplicate_products = list(set(duplicate_products)) 
            
            if duplicate_products:
                rec.has_duplicate_po_warning = True
                rec.duplicate_po_warning_text = _("Purchase Orders from other Proformas have already been processed for: %s.") % (", ".join(duplicate_products))