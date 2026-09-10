from odoo import models, fields, api

class AddVendorQuotationWizard(models.TransientModel):
    _name = 'add.vendor.quotation.wizard'
    _description = 'Add Vendor Quotation to Analysis'

    analysis_id = fields.Many2one('procurement.proforma.analysis', string="Analysis", required=True)
    vendor_id = fields.Many2one('res.partner', string="Vendor", required=True)
    attachment_file = fields.Binary(string='Upload Proforma (PDF)')
    attachment_name = fields.Char(string='Filename')
    consolidate_lines = fields.Boolean(
        string='Consolidate Products', 
        default=True,
        help="If checked, multiple requests for the same product will be merged into one line using the Purchase UoM."
    )

    def action_apply(self):
        self.ensure_one()
        lines_to_create = []

        if self.consolidate_lines:
            products_data = {}
            for pr in self.analysis_id.procurement_ids:
                for line in pr.line_ids:
                    target_uom = line.product_id.uom_po_id or line.product_id.uom_id
                    converted_qty = line.product_uom_id._compute_quantity(line.quantity, target_uom)
                    
                    if line.product_id.id not in products_data:
                        products_data[line.product_id.id] = {
                            'uom_id': target_uom.id,
                            'quantity': converted_qty,
                            'specifications': line.specifications,
                        }
                    else:
                        products_data[line.product_id.id]['quantity'] += converted_qty

            for product_id, vals in products_data.items():
                lines_to_create.append((0, 0, self._prepare_line_vals(
                    product_id, 
                    vals['uom_id'], 
                    vals['quantity'], 
                    vals.get('specifications')
                )))

        else:
            for pr in self.analysis_id.procurement_ids:
                for line in pr.line_ids:
                    lines_to_create.append((0, 0, self._prepare_line_vals(
                        line.product_id.id, 
                        line.product_uom_id.id, 
                        line.quantity,
                        line.specifications
                    )))

        self.analysis_id.write({'line_ids': lines_to_create})
        return {'type': 'ir.actions.act_window_close'}

    def _prepare_line_vals(self, product_id, uom_id, qty, specifications=None):
        
        return {
            'product_id': product_id,
            'product_uom_id': uom_id,
            'quantity': qty,
            'vendor_id': self.vendor_id.id,
            'attachment_file': self.attachment_file,
            'attachment_name': self.attachment_name,
            'price': 0.0,
            'specifications': specifications,
        }