# from . import sale_order
from . import sale_order_ajwa ,sale_order_taj
# from . import fetchall
#             COALESCE(pwc.name, psw.name, 'No Wing') AS wing_name
# from odoo import models, api
# import logging

# _logger = logging.getLogger(__name__)

# class CrmLead(models.Model):
#     _inherit = 'crm.lead'

#     @api.model
#     def get_supervisor_dashboard_data(self, date_range):
#         query = """
#         WITH filtered_leads AS (
#             SELECT cl.id, cl.stage_id, cl.user_id, cl.supervisor_id, cl.wing_id
#             FROM crm_lead cl
#             WHERE %s
#         ),
#         lead_events AS (
#             SELECT
#                 fl.id AS lead_id,
#                 rp_wing.name AS wing_name,
#                 rp_sup.name AS supervisor_name,
#                 rp.name AS sales_person,
#                 CASE 
#                     WHEN stage.name::jsonb ->> 'en_US' ILIKE '%%expired%%' THEN 'Expired'
#                     WHEN stage.name::jsonb ->> 'en_US' ILIKE '%%won%%' THEN 'Won'
#                     WHEN stage.name::jsonb ->> 'en_US' ILIKE '%%reservation%%' THEN 'Reservation'
#                     WHEN stage.name::jsonb ->> 'en_US' ILIKE '%%follow%%' THEN 'Follow Up'
#                     WHEN stage.name::jsonb ->> 'en_US' ILIKE '%%prospect%%' THEN 'Prospect'
#                     ELSE NULL
#                 END AS event_type
#             FROM filtered_leads fl
#             JOIN crm_stage stage ON fl.stage_id = stage.id
#             JOIN res_users ru ON fl.user_id = ru.id
#             JOIN res_partner rp ON ru.partner_id = rp.id
#             JOIN property_sales_supervisor pss ON fl.supervisor_id = pss.id
#             JOIN res_users ru_sup ON pss.name = ru_sup.id
#             JOIN res_partner rp_sup ON ru_sup.partner_id = rp_sup.id
#             JOIN property_sales_wing psw ON fl.wing_id = psw.id
#             JOIN res_users ru_wing ON psw.manager_id = ru_wing.id
#             JOIN res_partner rp_wing ON ru_wing.partner_id = rp_wing.id
#         ),
#         activity_events AS (
#             SELECT 
#                 cl.id AS lead_id,
#                 rp_wing.name AS wing_name,
#                 rp_sup.name AS supervisor_name,
#                 rp.name AS sales_person,
#                 CASE 
#                     WHEN mm.subtype_id = 3 AND mtv.new_value_char IS NULL THEN
#                         CASE mm.mail_activity_type_id
#                             WHEN 1 THEN 'Email'
#                             WHEN 2 THEN 'SMS'
#                             WHEN 4 THEN 'Call'
#                             WHEN 8 THEN 'Office Visit'
#                             WHEN 9 THEN 'Site Visit'
#                             WHEN 10 THEN 'To Do'
#                             ELSE NULL
#                         END
#                     WHEN mtv.new_value_char = 'Won' THEN 'Won'
#                     ELSE NULL
#                 END AS event_type
#             FROM crm_lead cl
#             JOIN filtered_leads fl ON cl.id = fl.id
#             JOIN res_users ru ON cl.user_id = ru.id
#             JOIN res_partner rp ON ru.partner_id = rp.id
#             JOIN mail_message mm ON mm.model = 'crm.lead' AND mm.res_id = cl.id
#             LEFT JOIN mail_tracking_value mtv ON mm.id = mtv.mail_message_id
#             JOIN property_sales_supervisor pss ON cl.supervisor_id = pss.id
#             JOIN res_users ru_sup ON pss.name = ru_sup.id
#             JOIN res_partner rp_sup ON ru_sup.partner_id = rp_sup.id
#             JOIN property_sales_wing psw ON cl.wing_id = psw.id
#             JOIN res_users ru_wing ON psw.manager_id = ru_wing.id
#             JOIN res_partner rp_wing ON ru_wing.partner_id = rp_wing.id
#             WHERE 
#                 TRIM(BOTH FROM LOWER(COALESCE(mtv.old_value_char, ''))) <> 'sales'
#                 AND mm.subtype_id <> 5
#         ),
#         unioned_events AS (
#             SELECT * FROM lead_events
#             UNION ALL
#             SELECT * FROM activity_events
#         )

#         SELECT
#             wing_name,
#             supervisor_name,
#             sales_person,
#             event_type,
#             COUNT(*) AS count,
#             SUM(CASE 
#                 WHEN event_type IN ('Reservation', 'Won', 'Expired') THEN 1
#                 ELSE 0
#             END) OVER (PARTITION BY wing_name, supervisor_name, sales_person) AS total_key_events
#         FROM unioned_events
#         WHERE event_type IS NOT NULL
#         GROUP BY
#             wing_name, supervisor_name, sales_person, event_type
#         ORDER BY
#             wing_name, supervisor_name, sales_person, event_type
#         """
        
#         # Set date condition based on range
#         date_condition = "1=1"
#         if date_range == '30days':
#             date_condition = "cl.create_date >= CURRENT_DATE - INTERVAL '30 days' AND cl.create_date <= CURRENT_DATE"
#         elif date_range == '90days':
#             date_condition = "cl.create_date >= CURRENT_DATE - INTERVAL '90 days' AND cl.create_date <= CURRENT_DATE"
        
#         self.env.cr.execute(query % date_condition)
#         results = self.env.cr.dictfetchall()
#         _logger.info("Dashboard data fetched: %s records", len(results))
#         return results