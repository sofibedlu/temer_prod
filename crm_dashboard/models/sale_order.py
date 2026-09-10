# # In reservation/hr/crm_dashboard/models/property_site.py
# from odoo import models
# from odoo import api

# class PropertySite(models.Model):
#     _inherit = 'property.site'
#     @api.model
#     def get_site_status_data(self):
#         self.env.cr.execute("""
#             SELECT
#                 ps.id AS site_id,
#                 ps.name AS site_name,
#                 COUNT(DISTINCT CASE WHEN pr.status = 'reserved' THEN pr.partner_id END) AS reserved_count,
#                 COUNT(DISTINCT CASE WHEN pr.status = 'requested' THEN pr.partner_id END) AS requested_count,
#                 COUNT(DISTINCT CASE WHEN pr.status = 'cancelled' THEN pr.partner_id END) AS cancelled_count,
#                 COUNT(DISTINCT CASE WHEN pr.status = 'expired' THEN pr.partner_id END) AS expired_count,
#                 COUNT(DISTINCT CASE WHEN pr.status = 'sold' THEN pr.partner_id END) AS sold_count,
#                 COUNT(DISTINCT pr.partner_id) AS total_customers
#             FROM crm_lead_property_site_rel clpsr
#             JOIN property_site ps ON ps.id = clpsr.property_site_id
#             JOIN crm_lead cl ON cl.id = clpsr.crm_lead_id
#             JOIN property_reservation pr ON pr.partner_id = cl.partner_id
#             GROUP BY ps.id, ps.name
#             ORDER BY ps.name;
#         """)
#         print("siteStatusData:", self.env.cr.dictfetchall())
#         return self.env.cr.dictfetchall()
    











from odoo import models, api

class PropertySite(models.Model):
    _inherit = 'property.site'

    @api.model
    def get_site_status_data(self):
        self.env.cr.execute("""
            SELECT
                ps.id AS site_id,
                ps.name AS site_name,
                COUNT(DISTINCT CASE WHEN pr.status = 'reserved' THEN pr.partner_id END) AS reserved_count,
                COUNT(DISTINCT CASE WHEN pr.status = 'requested' THEN pr.partner_id END) AS requested_count,
                COUNT(DISTINCT CASE WHEN pr.status = 'cancelled' THEN pr.partner_id END) AS cancelled_count,
                COUNT(DISTINCT CASE WHEN pr.status = 'expired' THEN pr.partner_id END) AS expired_count,
                COUNT(DISTINCT CASE WHEN pr.status = 'sold' THEN pr.partner_id END) AS sold_count,
                COUNT(DISTINCT pr.partner_id) AS total_customers
            FROM crm_lead_property_site_rel clpsr
            JOIN property_site ps ON ps.id = clpsr.property_site_id
            JOIN crm_lead cl ON cl.id = clpsr.crm_lead_id
            JOIN property_reservation pr ON pr.partner_id = cl.partner_id
            GROUP BY ps.id, ps.name
            ORDER BY ps.id
        """)
        # fetchall into dicts and return
        return self.env.cr.dictfetchall()

    