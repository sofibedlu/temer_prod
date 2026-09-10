from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class CollectionSiteAccess(models.Model):
    _name = "collection.site.access"
    _description = "Collection User Site Access"
    _rec_name = "user_id"
    _order = "user_id"

    user_id = fields.Many2one("res.users", string="User", required=True, ondelete="cascade")
    site_ids = fields.Many2many(
        "property.site",
        "collection_site_access_site_rel",
        "access_id",
        "site_id",
        string="Sites",
    )

    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("uniq_user", "unique(user_id)", "There is already a site access record for this user."),
    ]

    @api.constrains("user_id")
    def _check_user_required(self):
        for rec in self:
            if not rec.user_id:
                raise ValidationError(_("User is required."))

    def _sync_users_collection_sites(self, users):
        users = users.filtered(lambda u: u)
        if not users:
            return
        for user in users:
            access_recs = self.search([("user_id", "=", user.id), ("active", "=", True)])
            sites = access_recs.mapped("site_ids")
            user.write({"collection_site_ids": [(6, 0, sites.ids)]})

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_users_collection_sites(records.mapped("user_id"))
        return records

    def write(self, vals):
        old_users = self.mapped("user_id")
        res = super().write(vals)
        new_users = self.mapped("user_id")
        self._sync_users_collection_sites(old_users | new_users)
        return res

    def unlink(self):
        users = self.mapped("user_id")
        res = super().unlink()
        self._sync_users_collection_sites(users)
        return res