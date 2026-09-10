# from odoo import models, api, fields
# from dateutil.relativedelta import relativedelta  # <-- Add this import
# import logging

# _logger = logging.getLogger(__name__)

# class CrmLead(models.Model):
#     _inherit = 'crm.lead'

#     @api.model
#     def get_supervisor_dashboard_data(self, date_range, filters=None):
#         for i in range (1, 31):
#             print(i)
#         from_date = None
#         if date_range == '30days':
#             from_date = (fields.Date.context_today(self) - relativedelta(days=30)).strftime('%Y-%m-%d')
#         elif date_range == '90days':
#             from_date = (fields.Date.context_today(self) - relativedelta(days=90)).strftime('%Y-%m-%d')
        
#         domain = []
#         if from_date:
#             domain.append(('create_date', '>=', from_date))
        
#         leads = self.search(domain)
#         result = []
#         for lead in leads:
#             result.append({
#                 'wing_name': lead.wing_id.name if lead.wing_id else '',
#                 'supervisor_name': lead.supervisor_id.name if lead.supervisor_id else '',  # Ensure this returns a string
#                 'sales_person': lead.user_id.name if lead.user_id else '',
#                 'event_type': lead.stage_id.name if lead.stage_id else '',
#                 'count': 1,
#             })
#         return result


#     @api.model
#     def get_detailed_sales_performance(self, filters):
#         for i in range (1, 31):
#             print(i)
#         date_from = filters.get('date_from')
#         date_to = filters.get('date_to')

#         params = []
#         conditions = []

#         if date_from:
#             conditions.append("cl.create_date >= %s")
#             params.append(date_from)
#         if date_to:
#             conditions.append("cl.create_date <= %s")
#             params.append(date_to)

#         where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

#         query = f"""
#             WITH filtered_leads AS (
#                 SELECT cl.id, cl.stage_id, cl.user_id, cl.supervisor_id, cl.wing_id
#                 FROM crm_lead cl
#                 {where_clause}
#             ),
#             lead_events AS (
#                 SELECT
#                     fl.id AS lead_id,
#                     rp.name AS sales_person,
#                     rp_sup.name AS supervisor_name,
#                     rp_wing.name AS wing_manager_name,
#                     COALESCE(psw.name, 'No Wing') AS wing_name,

#                     CASE 
#                         WHEN stage.name::jsonb ->> 'en_US' ILIKE '%%expired%%' THEN 'Expired'
#                         WHEN stage.name::jsonb ->> 'en_US' ILIKE '%%won%%' THEN 'Won'
#                         WHEN stage.name::jsonb ->> 'en_US' ILIKE '%%reservation%%' THEN 'Reservation'
#                         WHEN stage.name::jsonb ->> 'en_US' ILIKE '%%lost%%' THEN 'Lost'
#                         WHEN stage.name::jsonb ->> 'en_US' ILIKE '%%follow%%' THEN 'Follow Up'
#                         WHEN stage.name::jsonb ->> 'en_US' ILIKE '%%prospect%%' THEN 'Prospect'
#                         ELSE NULL
#                     END AS event_type
#                 FROM filtered_leads fl
#                 JOIN crm_stage stage ON fl.stage_id = stage.id
#                 JOIN res_users ru ON fl.user_id = ru.id
#                 JOIN res_partner rp ON ru.partner_id = rp.id
#                 LEFT JOIN property_sales_supervisor pss ON fl.supervisor_id = pss.id
#                 LEFT JOIN res_users ru_sup ON pss.name = ru_sup.id
#                 LEFT JOIN res_partner rp_sup ON ru_sup.partner_id = rp_sup.id
#                 LEFT JOIN property_sales_wing psw ON fl.wing_id = psw.id
#                 LEFT JOIN res_users ru_wing ON psw.manager_id = ru_wing.id
#                 LEFT JOIN res_partner rp_wing ON ru_wing.partner_id = rp_wing.id
#                 LEFT JOIN property_wing_config pwc ON fl.wing_id = pwc.id
#             ),
#             activity_events AS (
#                 SELECT
#                     cl.id AS lead_id,
#                     rp.name AS sales_person,
#                     rp_sup.name AS supervisor_name,
#                     rp_wing.name AS wing_manager_name,
                    
#                     COALESCE(psw.name, 'No Wing') AS wing_name,
#                     CASE
#                         WHEN mm.mail_activity_type_id = 1 THEN 'Email'
#                         WHEN mm.mail_activity_type_id = 2 THEN 'SMS'
#                         WHEN mm.mail_activity_type_id = 4 THEN 'Call'
#                         WHEN mm.mail_activity_type_id = 8 THEN 'Office Visit'
#                         WHEN mm.mail_activity_type_id = 9 THEN 'Site Visit'
#                         ELSE NULL
#                     END AS activity_type
#                 FROM crm_lead cl
#                 JOIN mail_message mm ON mm.model = 'crm.lead' AND mm.res_id = cl.id
#                 JOIN res_users ru ON cl.user_id = ru.id
#                 JOIN res_partner rp ON ru.partner_id = rp.id
#                 LEFT JOIN property_sales_supervisor pss ON cl.supervisor_id = pss.id
#                 LEFT JOIN res_users ru_sup ON pss.name = ru_sup.id
#                 LEFT JOIN res_partner rp_sup ON ru_sup.partner_id = rp_sup.id
#                 LEFT JOIN property_sales_wing psw ON cl.wing_id = psw.id
#                 LEFT JOIN res_users ru_wing ON psw.manager_id = ru_wing.id
#                 LEFT JOIN res_partner rp_wing ON ru_wing.partner_id = rp_wing.id
#                 LEFT JOIN property_wing_config pwc ON cl.wing_id = pwc.id
#             )
#             SELECT
#                 le.wing_name,
#                 le.supervisor_name,
#                 le.sales_person,
#                 COUNT(DISTINCT le.lead_id) FILTER (WHERE le.event_type = 'Reservation') AS reservation_count,
#                 COUNT(DISTINCT le.lead_id) FILTER (WHERE le.event_type = 'Won') AS won_count,
#                 COUNT(DISTINCT le.lead_id) FILTER (WHERE le.event_type = 'Expired') AS expired_count,
#                 COUNT(DISTINCT le.lead_id) FILTER (WHERE le.event_type = 'Lost') AS lost_count,
#                 COUNT(DISTINCT le.lead_id) FILTER (WHERE le.event_type = 'Follow Up') AS follow_up_count,
#                 COUNT(DISTINCT le.lead_id) FILTER (WHERE le.event_type = 'Prospect') AS prospect_count,
#                 COUNT(ae.lead_id) FILTER (WHERE ae.activity_type = 'Office Visit') AS office_visit_count,
#                 COUNT(ae.lead_id) FILTER (WHERE ae.activity_type = 'Site Visit') AS site_visit_count,
#                 COUNT(ae.lead_id) FILTER (WHERE ae.activity_type = 'Email') AS email_count,
#                 COUNT(ae.lead_id) FILTER (WHERE ae.activity_type = 'SMS') AS sms_count,
#                 COUNT(ae.lead_id) FILTER (WHERE ae.activity_type = 'Call') AS call_count,
#                 COUNT(DISTINCT le.lead_id) AS total_events
#             FROM lead_events le
#             LEFT JOIN activity_events ae ON le.lead_id = ae.lead_id
#             GROUP BY le.wing_name, le.supervisor_name, le.sales_person
#             ORDER BY le.wing_name, le.supervisor_name, le.sales_person
#         """

#         # Defensive: If no params, pass an empty tuple to avoid IndexError
#         self.env.cr.execute(query, tuple(params) if params else ())
#         results = self.env.cr.fetchall()
#         _logger.info("Executing query with parameters: %s", params)
#         _logger.info("Query results: %s", results)
#         columns = [desc[0] for desc in self.env.cr.description]
#         return [dict(zip(columns, row)) for row in results]


from odoo import models, fields, api
from datetime import datetime

class PropertySalesDashboard(models.Model):
    _name = 'property.sales.dashboard'
    _description = 'Property Sales Dashboard'

    def get_supervisor_dashboard_data(self, date_from, date_to):
        """
        Returns the dashboard data for the supervisor view
        """
        query = """
            WITH filtered_leads AS (
                SELECT cl.id, cl.stage_id, cl.user_id, cl.supervisor_id, cl.wing_id, cl.create_date
                FROM crm_lead cl
                WHERE cl.create_date >= %s
                AND cl.create_date <= %s
            ),
            lead_events AS (
                SELECT
                    fl.id AS lead_id,
                    rp.name AS sales_person,
                    rp_sup.name AS supervisor_name,
                    rp_wing.name AS wing_manager_name,
                    COALESCE(psw.name, 'No Wing') AS wing_name,

                    CASE 
                        WHEN stage.name::jsonb ->> 'en_US' ILIKE '%expired%' THEN 'Expired'
                        WHEN stage.name::jsonb ->> 'en_US' ILIKE '%won%' THEN 'Won'
                        WHEN stage.name::jsonb ->> 'en_US' ILIKE '%reservation%' THEN 'Reservation'
                        WHEN stage.name::jsonb ->> 'en_US' ILIKE '%lost%' THEN 'Lost'
                        WHEN stage.name::jsonb ->> 'en_US' ILIKE '%follow%' THEN 'Follow Up'
                        WHEN stage.name::jsonb ->> 'en_US' ILIKE '%prospect%' THEN 'Prospect'
                        ELSE NULL
                    END AS event_type
                FROM filtered_leads fl
                JOIN crm_stage stage ON fl.stage_id = stage.id
                JOIN res_users ru ON fl.user_id = ru.id
                JOIN res_partner rp ON ru.partner_id = rp.id
                LEFT JOIN property_sales_supervisor pss ON fl.supervisor_id = pss.id
                LEFT JOIN res_users ru_sup ON pss.name = ru_sup.id
                LEFT JOIN res_partner rp_sup ON ru_sup.partner_id = rp_sup.id
                LEFT JOIN property_sales_wing psw ON fl.wing_id = psw.id
                LEFT JOIN res_users ru_wing ON psw.manager_id = ru_wing.id
                LEFT JOIN res_partner rp_wing ON ru_wing.partner_id = rp_wing.id
                LEFT JOIN property_wing_config pwc ON fl.wing_id = pwc.id
            ),
            activity_events AS (
                SELECT
                    cl.id AS lead_id,
                    rp.name AS sales_person,
                    rp_sup.name AS supervisor_name,
                    rp_wing.name AS wing_manager_name,
                    
                    COALESCE(psw.name, 'No Wing') AS wing_name,
                    CASE
                        WHEN mm.mail_activity_type_id = 1 THEN 'Email'
                        WHEN mm.mail_activity_type_id = 2 THEN 'SMS'
                        WHEN mm.mail_activity_type_id = 4 THEN 'Call'
                        WHEN mm.mail_activity_type_id = 8 THEN 'Office Visit'
                        WHEN mm.mail_activity_type_id = 9 THEN 'Site Visit'
                        ELSE NULL
                    END AS activity_type
                FROM crm_lead cl
                JOIN mail_message mm ON mm.model = 'crm.lead' AND mm.res_id = cl.id
                JOIN res_users ru ON cl.user_id = ru.id
                JOIN res_partner rp ON ru.partner_id = rp.id
                LEFT JOIN property_sales_supervisor pss ON cl.supervisor_id = pss.id
                LEFT JOIN res_users ru_sup ON pss.name = ru_sup.id
                LEFT JOIN res_partner rp_sup ON ru_sup.partner_id = rp_sup.id
                LEFT JOIN property_sales_wing psw ON cl.wing_id = psw.id
                LEFT JOIN res_users ru_wing ON psw.manager_id = ru_wing.id
                LEFT JOIN res_partner rp_wing ON ru_wing.partner_id = rp_wing.id
                LEFT JOIN property_wing_config pwc ON cl.wing_id = pwc.id
                WHERE cl.create_date >= %s
                AND cl.create_date <= %s
            )
            SELECT
                le.wing_name,
                le.supervisor_name,
                le.sales_person,
                COUNT(DISTINCT le.lead_id) FILTER (WHERE le.event_type = 'Reservation') AS reservation_count,
                COUNT(DISTINCT le.lead_id) FILTER (WHERE le.event_type = 'Won') AS won_count,
                COUNT(DISTINCT le.lead_id) FILTER (WHERE le.event_type = 'Expired') AS expired_count,
                COUNT(DISTINCT le.lead_id) FILTER (WHERE le.event_type = 'Lost') AS lost_count,
                COUNT(DISTINCT le.lead_id) FILTER (WHERE le.event_type = 'Follow Up') AS follow_up_count,
                COUNT(DISTINCT le.lead_id) FILTER (WHERE le.event_type = 'Prospect') AS prospect_count,
                COUNT(ae.lead_id) FILTER (WHERE ae.activity_type = 'Office Visit') AS office_visit_count,
                COUNT(ae.lead_id) FILTER (WHERE ae.activity_type = 'Site Visit') AS site_visit_count,
                COUNT(ae.lead_id) FILTER (WHERE ae.activity_type = 'Email') AS email_count,
                COUNT(ae.lead_id) FILTER (WHERE ae.activity_type = 'SMS') AS sms_count,
                COUNT(ae.lead_id) FILTER (WHERE ae.activity_type = 'Call') AS call_count,
                COUNT(DISTINCT le.lead_id) AS total_events
            FROM lead_events le
            LEFT JOIN activity_events ae ON le.lead_id = ae.lead_id
            GROUP BY le.wing_name, le.supervisor_name, le.sales_person
            ORDER BY le.wing_name, le.supervisor_name, le.sales_person
        """
        
        self.env.cr.execute(query, (date_from, date_to, date_from, date_to))
        results = self.env.cr.dictfetchall()
        
        return results