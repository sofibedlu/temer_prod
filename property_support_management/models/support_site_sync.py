from odoo import models, fields, api

class PropertySite(models.Model):
    _inherit = 'property.site'

    def write(self, vals):
        res = super().write(vals)
        if 'name' in vals:
            for record in self:
                union = self.env['support.location'].search([('site_id', '=', record.id)], limit=1)
                if union:
                    union.name = record.name
        return res

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            self.env['support.location'].create({
                'name': record.name,
                'type': 'site',
                'site_id': record.id,
            })
        return records

    def unlink(self):
        for record in self:
            union = self.env['support.location'].search([('site_id', '=', record.id)])
            union.unlink()
        return super().unlink()
