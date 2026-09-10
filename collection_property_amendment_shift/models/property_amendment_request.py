from odoo import models, fields, api

class PropertyAmendmentRequest(models.Model):
    _inherit = 'property.amendment.request'

    new_site_id = fields.Many2one('property.site', string="New Target Site", tracking=True)
    is_site_shift = fields.Boolean(string="Is Site Shift?", compute="_compute_is_site_shift", store=True)

    @api.depends('site_id', 'new_site_id')
    def _compute_is_site_shift(self):
        for req in self:
            if req.site_id and req.new_site_id:
                req.is_site_shift = req.site_id.id != req.new_site_id.id
            else:
                req.is_site_shift = False