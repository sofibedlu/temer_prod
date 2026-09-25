from odoo import fields, models

class RebarProductionRequestLine(models.Model):
    _name = 'rebar.production.request.line'
    _description = 'Rebar Production Request Line'

    request_id = fields.Many2one(
        comodel_name='rebar.production.request',
        string='Request Reference',
        ondelete='cascade',
        required=True
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Rebar Product',
        required=True
    )
    bar_mark_id = fields.Many2one(
        comodel_name='rebar.bar.mark',
        string='Bar Mark'
    )
    diameter = fields.Float(string='Diameter (mm)', required=True)
    shape = fields.Char(string='Shape / Shape Code', help="e.g., L-Shape, Stirrup, Shape 21")
    length = fields.Float(string='Shape Length (m)', required=True, help="Cutting/individual shape length")
    quantity = fields.Float(string='Quantity (Pcs)', required=True, default=1.0)