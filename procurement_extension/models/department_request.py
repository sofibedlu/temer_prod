from odoo import models, fields, api

class DepartmentRequest(models.Model):
    _inherit = 'department.request'

    internal_request_id = fields.Many2one(
        'internal.request',
        string='Source Internal Request',
        compute='_compute_internal_request',
        store=True
    )

    original_department_id = fields.Many2one(
        'hr.department',
        related='internal_request_id.department_id',
        string='Original Requesting Dept',
        store=True
    )

    picking_ids = fields.Many2many('stock.picking', compute='_compute_picking_ids', string='Receipts')
    picking_count = fields.Integer(compute='_compute_picking_ids')

    def _compute_picking_ids(self):
        for req in self:
            # Trace: Dept Request -> Procurement -> Evaluation -> PO -> Picking
            procs = self.env['procurement.request'].search([('department_request_id', '=', req.id)])
            evals = self.env['procurement.proforma.evaluation'].search([('procurement_ids', 'in', procs.ids)])
            pos = self.env['purchase.order'].search([('custom_evaluation_id', 'in', evals.ids)])
            pickings = pos.mapped('picking_ids')
            
            req.picking_ids = pickings
            req.picking_count = len(pickings)

    def action_view_pickings(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Receipts',
            'res_model': 'stock.picking',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.picking_ids.ids)],
        }

    @api.depends('origin')
    def _compute_internal_request(self):
        for rec in self:
            rec.internal_request_id = False
            if rec.origin:
                internal_req = self.env['internal.request'].search([('name', '=', rec.origin)], limit=1)
                if internal_req:
                    rec.internal_request_id = internal_req.id

    def action_view_internal_request(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Source Document',
            'res_model': 'internal.request',
            'view_mode': 'form',
            'res_id': self.internal_request_id.id,
        }