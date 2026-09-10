from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ProcurementProformaEvaluation(models.Model):
    _name = 'procurement.proforma.evaluation'
    _description = 'Proforma Analysis'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'

    name = fields.Char(string='Reference', required=True, default='New', readonly=True)
    collection_id = fields.Many2one('procurement.proforma.analysis', string='Source Collection', required=False, ondelete='cascade')
    procurement_ids = fields.Many2many('procurement.request', string='Source Procurements')
    state = fields.Selection([('draft', 'Draft'), ('done', 'Done')], default='draft', tracking=True)
    line_ids = fields.One2many('procurement.proforma.evaluation.line', 'evaluation_id', string='Analysis Lines')
    po_count = fields.Integer(compute='_compute_po_count', string='RFQs')
    procurement_summary = fields.Html(compute='_compute_procurement_summary', string='Procurement Details')

    spec_line_ids = fields.Many2many(
        'procurement.proforma.evaluation.line',
        compute='_compute_spec_line_ids',
        string='Unique Specifications'
    )

    @api.depends('line_ids', 'line_ids.product_id')
    def _compute_spec_line_ids(self):
        for rec in self:
            unique_products = set()
            spec_lines = self.env['procurement.proforma.evaluation.line']
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

    def unlink(self):
        for rec in self:
            related_pos = self.env['purchase.order'].search([('custom_evaluation_id', '=', rec.id)])
            if related_pos and any(po.state != 'cancel' for po in related_pos):
                raise ValidationError(_("You can only delete an analysis if all its generated Purchase Orders are cancelled."))
        return super(ProcurementProformaEvaluation, self).unlink()

    def _compute_po_count(self):
        for rec in self:
            rec.po_count = self.env['purchase.order'].search_count([('custom_evaluation_id', '=', rec.id)])

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('procurement.evaluation') or 'New'
        records = super().create(vals_list)
        if not self.env.context.get('skip_auto_populate_lines'):
            for record in records:
                if record.procurement_ids:
                    record._populate_evaluation_lines()
                
        return records

    def action_create_rfqs(self):
        self.ensure_one()

        if any(line.proforma_line_id.price <= 0 for line in self.line_ids):
            raise ValidationError(_("All evaluated proforma lines must have a unit price greater than zero."))
        
        winning_lines = self.line_ids.filtered(lambda l: l.is_winner and l.proforma_line_id.vendor_id)
        if not winning_lines:
            raise ValidationError(_("Please mark at least one line with a valid vendor as a winner to generate RFQs."))

        vendors = winning_lines.mapped('proforma_line_id.vendor_id')
        for vendor in vendors:
            # Group lines by vendor
            lines = winning_lines.filtered(lambda l: l.proforma_line_id.vendor_id == vendor)
            po_vals = {
                'partner_id': vendor.id,
                'custom_evaluation_id': self.id,
                'origin': self.name,
                'order_line': [(0, 0, {
                    'product_id': l.product_id.id,
                    'name': l.product_id.display_name or 'Purchase Product',
                    'product_qty': l.proforma_line_id.quantity,
                    'product_uom': l.proforma_line_id.product_uom_id.id,
                    'price_unit': l.proforma_line_id.price,
                    'date_planned': fields.Datetime.now(),
                    'specifications': l.specifications,
                }) for l in lines]
            }
            self.env['purchase.order'].create(po_vals)

    def action_view_rfqs(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Orders',
            'res_model': 'purchase.order',
            'view_mode': 'tree,form',
            'domain': [('custom_evaluation_id', '=', self.id)],
            'context': {'default_custom_evaluation_id': self.id}
        }
    
    @api.onchange('procurement_ids')
    def _onchange_procurement_ids_populate_lines(self):
        self._populate_evaluation_lines()

    def _populate_evaluation_lines(self):
        for rec in self:
            if not rec.procurement_ids:
                if rec.line_ids:
                    rec.line_ids = [(5, 0, 0)]
                continue

            existing_proforma_line_ids = rec.line_ids.mapped('proforma_line_id').ids
            requested_product_ids = rec.procurement_ids.mapped('line_ids.product_id').ids
            collections = self.env['procurement.proforma.analysis'].search([
                ('procurement_ids', 'in', rec.procurement_ids.ids),
            ])
            all_target_proforma_lines = collections.mapped('line_ids').filtered(
                lambda pl: pl.product_id.id in requested_product_ids
            )
            target_ids = all_target_proforma_lines.ids
            lines_to_add = all_target_proforma_lines.filtered(lambda l: l.id not in existing_proforma_line_ids)
            lines_to_remove = rec.line_ids.filtered(lambda l: l.proforma_line_id.id not in target_ids)

            commands = []
            for line in lines_to_remove:
                real_id = line.id if not isinstance(line.id, models.NewId) else False
                if real_id:
                    commands.append((2, real_id, 0))

            for pl in lines_to_add:
                commands.append((0, 0, {
                    'proforma_line_id': pl.id,
                    'technical': 0.0,
                    'financial': 0.0,
                }))
            
            if commands:
                rec.line_ids = commands

    def write(self, vals):
        res = super(ProcurementProformaEvaluation, self).write(vals)
        if 'procurement_ids' in vals:
            self._populate_evaluation_lines()
        return res

class ProcurementProformaEvaluationLine(models.Model):
    _name = 'procurement.proforma.evaluation.line'
    _description = 'Proforma Analysis Line'

    evaluation_id = fields.Many2one('procurement.proforma.evaluation', ondelete='cascade')
    proforma_line_id = fields.Many2one('procurement.proforma.line', string='Vendor Quote', required=True)
    collection_id = fields.Many2one(
        'procurement.proforma.analysis',
        string='Source Collection',
        related='proforma_line_id.analysis_id',
        store=True,
        readonly=True,
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        related='proforma_line_id.product_id',
        store=True,
        readonly=True,
    )
    vendor_id = fields.Many2one('res.partner', string='Vendor', related='proforma_line_id.vendor_id', store=True)
    quantity = fields.Float(related='proforma_line_id.quantity', store=True)
    product_uom_id = fields.Many2one('uom.uom', string='UoM', related='proforma_line_id.product_uom_id', store=True)
    price = fields.Float(string='Unit Price', related='proforma_line_id.price', store=True)

    # manual scoring
    technical = fields.Float(string='Technical', default=0.0)
    financial = fields.Float(string='Financial', default=0.0)
    total_score = fields.Float(compute='_compute_total_score', string='Sum', store=True)
    is_winner = fields.Boolean(string='Winner?')

    specifications = fields.Html(
        string='Specifications',
        related='proforma_line_id.specifications',
        store=True,
        readonly=True,
    )

    @api.constrains('technical', 'financial')
    def _check_scores_against_request(self):
        for line in self:
            if not line.evaluation_id.procurement_ids or not line.product_id:
                continue

            req_line = self.env['procurement.request.line'].search([
                ('procurement_id', 'in', line.evaluation_id.procurement_ids.ids),
                ('product_id', '=', line.product_id.id)
            ], limit=1)
            
            if req_line:
                if line.technical > req_line.technical:
                    raise ValidationError(_("Technical score for %(prod)s cannot exceed the requested weight (%(weight)s%%).") % {
                        'prod': line.product_id.display_name, 'weight': req_line.technical
                    })
                if line.financial > req_line.financial:
                    raise ValidationError(_("Financial score for %(prod)s cannot exceed the requested weight (%(weight)s%%).") % {
                        'prod': line.product_id.display_name, 'weight': req_line.financial
                    })

    @api.depends('technical', 'financial')
    def _compute_total_score(self):
        for line in self:
            line.total_score = line.technical + line.financial