from odoo import models, api

class CollectionSiteAccess(models.Model):
    _inherit = "collection.site.access"

    def _sync_users_collection_sites(self, users):
        users = users.filtered(lambda u: u)
        if not users:
            return
        for user in users:
            access_recs = self.sudo().search([("user_id", "=", user.id), ("active", "=", True)])
            sites = access_recs.mapped("site_ids")
            user.sudo().write({"collection_site_ids": [(6, 0, sites.ids)]})