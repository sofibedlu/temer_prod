from odoo import models, fields, api, _

class PropertyCollectionConfig(models.Model):
    _name = 'property.collection.config'
    _description = 'Collection Configuration'
    _rec_name = 'name'

    name = fields.Char(string="Name", default="Collection Configuration", readonly=True)
    termination_threshold_days = fields.Integer(
        string="Termination Threshold (Days)",
        default=30,
        help="Number of days after the due date before an overdue installment causes the collection order to be terminated."
    )

    @api.model_create_multi
    def create(self, vals_list):
        existing = self.search([], limit=1)
        if existing:
            return existing
        return super().create(vals_list)