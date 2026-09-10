from odoo import models, fields

class CollectionInstallment(models.Model):
    _inherit = "collection.installment"

    def _get_default_can_edit_due_date(self):
        return self.env.user.has_group("collection_management.group_collection_manager")

    can_edit_due_date = fields.Boolean(
        default=_get_default_can_edit_due_date, 
        store=False
    )