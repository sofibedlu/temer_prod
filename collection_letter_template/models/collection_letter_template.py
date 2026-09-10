from odoo import models, fields, api, _

class CollectionLetterTemplate(models.Model):
    _name = 'collection.letter.template'
    _description = 'Collection Letter Template'
    _inherit = ['mail.render.mixin']

    name = fields.Char(string='Template Name', required=True)
    subject = fields.Char(string='Subject', required=True, 
                          help="Use placeholders like {{ object.collection_id.name }}")
    model_id = fields.Many2one(
        'ir.model', 
        default=lambda self: self.env['ir.model']._get_id('collection.installment')
    )
    model = fields.Char(related='model_id.model', string='Collection Installment Line', readonly=True)

    receiver_html = fields.Html(
        string='Receiver contents', 
        required=True, 
        sanitize=False,
        help="Press '/' inside the editor to insert a Dynamic Placeholder easily."
    )
    body_html = fields.Html(string='Body contents', required=True, sanitize=False,  
                            help="Use placeholders like {{ object.partner_id.name }}")

    @api.depends('model')
    def _compute_render_model(self):
        for template in self:
            template.render_model = template.model
    
    def _render_context(self):
        return super()._render_context()