# from odoo import models, api

# class PropertyProperty(models.Model):
#     _inherit = "property.property"

#     def action_set_to_draft(self):
#         for rec in self:
#             rec.state = 'draft'


from odoo import models, api

class PropertyProperty(models.Model):
    _inherit = "property.property"

    def action_set_to_draft(self):
        self.ensure_one()
        self.state = 'draft'