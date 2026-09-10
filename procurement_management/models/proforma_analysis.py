from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from markupsafe import Markup

class ProcurementProformaAnalysis(models.Model):
    _name = 'procurement.proforma.analysis'
    _description = 'Proforma Collection'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'

    name = fields.Char(string='Reference', required=True, default='New', readonly=True)
    procurement_ids = fields.Many2many('procurement.request', string='Source Procurements')
    state = fields.Selection([('draft', 'Draft'), ('done', 'Done')], default='draft', tracking=True)
    line_ids = fields.One2many('procurement.proforma.line', 'analysis_id', string='Analysis Lines')
    evaluation_count = fields.Integer(compute='_compute_evaluation_count', string='Analyses')
    procurement_summary = fields.Html(compute='_compute_procurement_summary', string='Procurement Details')

    spec_line_ids = fields.Many2many(
        'procurement.proforma.line',
        compute='_compute_spec_line_ids',
        string='Unique Specifications'
    )

    @api.depends('line_ids', 'line_ids.product_id')
    def _compute_spec_line_ids(self):
        for rec in self:
            unique_products = set()
            spec_lines = self.env['procurement.proforma.line']
            for line in rec.line_ids:
                if line.product_id.id not in unique_products:
                    spec_lines |= line
                    unique_products.add(line.product_id.id)
            rec.spec_line_ids = spec_lines

    @api.depends('procurement_ids', 'procurement_ids.line_ids.product_id')
    def _compute_procurement_summary(self):
        for rec in self:
            if not rec.procurement_ids:
                rec.procurement_summary = False
                continue
            
            summary = "<div style='margin-top: 5px; padding: 10px; background-color: #f8f9fa; border-radius: 5px;'><ul>"
            for pr in rec.procurement_ids:
                dept = pr.department_id.name or 'No Department'
                products = ", ".join(pr.line_ids.mapped('product_id.display_name'))
                summary += f"<li><b>{pr.name}</b> ({dept}) - <i>{products}</i></li>"
            summary += "</ul></div>"
            rec.procurement_summary = summary

    def _compute_evaluation_count(self):
        for rec in self:
            rec.evaluation_count = self.env['procurement.proforma.evaluation'].search_count([
                '|', 
                ('collection_id', '=', rec.id),
                ('line_ids.collection_id', '=', rec.id)
            ])

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('procurement.proforma') or 'New'
        return super().create(vals_list)

    def action_generate_analysis(self):
        self.ensure_one()
        if not self.line_ids:
            raise ValidationError(_("You cannot generate an analysis without any quotations."))

        if any(line.price <= 0 for line in self.line_ids):
            raise ValidationError(_("All proforma collection unit prices must be greater than zero."))
        
        eval_vals = {
            'collection_id': self.id,
            'procurement_ids': [(6, 0, self.procurement_ids.ids)],
            'line_ids': [(0, 0, {
                'proforma_line_id': line.id,
            }) for line in self.line_ids],
        }
        
        proforma = self.env['procurement.proforma.evaluation'].with_context(skip_auto_populate_lines=True).create(eval_vals)

        return {
            'type': 'ir.actions.act_window',
            'name': 'Proforma Analysis',
            'res_model': 'procurement.proforma.evaluation',
            'view_mode': 'form',
            'res_id': proforma.id,
            'target': 'current',
        }

    def action_view_analysis(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Proforma Analyses',
            'res_model': 'procurement.proforma.evaluation',
            'view_mode': 'tree,form',
            'domain': ['|', ('collection_id', '=', self.id), ('line_ids.collection_id', '=', self.id)],
            'context': {'default_collection_id': self.id}
        }
    
    def action_launch_add_vendor_wizard(self):
        self.ensure_one()
        return {
            'name': 'Add Vendor Quotation',
            'type': 'ir.actions.act_window',
            'res_model': 'add.vendor.quotation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_analysis_id': self.id}
        }


class ProcurementProformaLine(models.Model):
    _name = 'procurement.proforma.line'
    _description = 'Proforma Collection Line'
    _rec_name = 'display_name'

    analysis_id = fields.Many2one('procurement.proforma.analysis', ondelete='cascade')
    product_id = fields.Many2one('product.product', required=True)
    quantity = fields.Float(default=1.0)
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True)
    vendor_id = fields.Many2one('res.partner', string='Vendor')
    price = fields.Float(string='Unit Price')
    attachment_file = fields.Binary(string='Proforma Copy')
    attachment_name = fields.Char(string='File Name')
    is_winner = fields.Boolean(string='Winner?', compute='_compute_is_winner', store=True)
    price_normalized = fields.Float(compute='_compute_price_normalized', store=True)

    product_uom_category_id = fields.Many2one(
        related='product_id.uom_id.category_id', 
        string='Product UoM Category'
    )
    req_technical = fields.Float(string='Technical Weight (%)', compute='_compute_requirements')
    req_financial = fields.Float(string='Financial Weight (%)', compute='_compute_requirements')
    display_name = fields.Char(compute='_compute_display_name', store=True)

    specifications = fields.Html(string='Specifications', sanitize=True)

    @api.depends('product_id', 'analysis_id.procurement_ids')
    def _compute_requirements(self):
        for line in self:
            tech = 0.0
            fin = 0.0
            if line.analysis_id and line.analysis_id.procurement_ids and line.product_id:
                req_line = self.env['procurement.request.line'].search([
                    ('procurement_id', 'in', line.analysis_id.procurement_ids.ids),
                    ('product_id', '=', line.product_id.id)
                ], limit=1)
                
                if req_line:
                    tech = req_line.technical
                    fin = req_line.financial
            
            line.req_technical = tech
            line.req_financial = fin

    @api.depends('vendor_id', 'price', 'product_uom_id')
    def _compute_display_name(self):
        for line in self:
            vendor = line.vendor_id.name or 'No Vendor'
            price = line.price
            uom = line.product_uom_id.name or ''
            line.display_name = f"{vendor} - {price} {uom}"

    @api.depends('price', 'product_uom_id', 'product_id', 'quantity')
    def _compute_price_normalized(self):
        for line in self:
            if line.price > 0 and line.product_id and line.product_uom_id and line.quantity > 0:
                total_cost = line.price * line.quantity
                qty_in_ref_uom = line.product_uom_id._compute_quantity(line.quantity, line.product_id.uom_id)
                line.price_normalized = total_cost / qty_in_ref_uom if qty_in_ref_uom else 0
            else:
                line.price_normalized = 0

    @api.depends('price_normalized', 'vendor_id', 'analysis_id.line_ids.price_normalized')
    def _compute_is_winner(self):
        for line in self:
            line.is_winner = False
            if not line.vendor_id or line.price_normalized <= 0:
                continue

            all_quotes_for_this_product = line.analysis_id.line_ids.filtered(
                lambda l: l.product_id == line.product_id and l.price_normalized > 0 and l.vendor_id
            )
            
            if all_quotes_for_this_product:
                best_price = min(all_quotes_for_this_product.mapped('price_normalized'))
                if round(line.price_normalized, 2) <= round(best_price, 2):
                    line.is_winner = True


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    
    custom_proforma_id = fields.Many2one('procurement.proforma.analysis', string='Linked Proforma Collection', readonly=True)
    custom_evaluation_id = fields.Many2one('procurement.proforma.evaluation', string='Linked Proforma Analysis', readonly=True)

    technical_approved = fields.Boolean(string='Technical Requirements Met', default=False, tracking=True, copy=False)
    technical_approved_by = fields.Many2one('res.users', string='Technical Checker', readonly=True, copy=False)
    technical_approval_date = fields.Datetime(string='Technical Checked On', readonly=True, copy=False)


    def button_confirm(self):
        res = super(PurchaseOrder, self).button_confirm()
        
        for po in self:
            if po.custom_evaluation_id:
                evaluation = po.custom_evaluation_id
                collections = evaluation.line_ids.mapped('collection_id')
                requests = evaluation.procurement_ids
                
                msg = Markup(f"Purchase Order <b>{po.name}</b> has been <b style='color:green;'>Confirmed</b>.")

                evaluation.sudo().write({'state': 'done'})
                evaluation.sudo().message_post(body=msg)

                if collections:
                    collections.sudo().write({'state': 'done'})
                    for col in collections:
                        col.sudo().message_post(body=msg)

                if requests:
                    requests.sudo().write({'state': 'done'})
                    for req in requests:
                        req.sudo().message_post(body=msg)
                        
        return res
    
    def action_view_custom_evaluation(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Proforma Analysis',
            'res_model': 'procurement.proforma.evaluation',
            'view_mode': 'form',
            'res_id': self.custom_evaluation_id.id,
        }
    
class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'
    
    specifications = fields.Html(string='Specifications', sanitize=True)