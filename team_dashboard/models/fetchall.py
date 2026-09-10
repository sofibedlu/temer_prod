# # from odoo import models, fields, api
# # from datetime import datetime

# # class CRMLead(models.Model):
# #     _inherit = 'crm.lead'
# #     def get_wing_dashboard_data(self, start_date, end_date=None):
# #         if not end_date:
# #             end_date = datetime.now().strftime('%Y-%m-%d')
# #         query = """
# #             WITH filtered_leads AS (
# #                 SELECT cl.id, cl.stage_id, cl.user_id, cl.supervisor_id, cl.wing_id
# #                 FROM crm_lead cl
# #                 WHERE cl.create_date >= %s
# #             ),
# #             lead_events AS (
# #                 SELECT
# #                     fl.id AS lead_id,
# #                     rp.name AS sales_person,
# #                     rp_sup.name AS supervisor_name,
# #                     rp_wing.name AS wing_manager_name,
# #                     COALESCE(pwc.name, psw.name, 'No Wing') AS wing_name,
# #                     CASE 
# #                         WHEN stage.name::jsonb ->> 'en_US' ILIKE '%%expired%%' THEN 'Expired'
# #                         WHEN stage.name::jsonb ->> 'en_US' ILIKE '%%reservation%%' THEN 'Reservation'
# #                         WHEN stage.name::jsonb ->> 'en_US' ILIKE '%%follow%%' THEN 'Follow Up'
# #                         WHEN stage.name::jsonb ->> 'en_US' ILIKE '%%prospect%%' THEN 'Prospect'
# #                         WHEN stage.name::jsonb ->> 'en_US' ILIKE '%%lost%%' THEN 'Lost'
# #                         ELSE NULL
# #                     END AS event_type
# #                 FROM filtered_leads fl
# #                 JOIN crm_stage stage ON fl.stage_id = stage.id
# #                 JOIN res_users ru ON fl.user_id = ru.id
# #                 JOIN res_partner rp ON ru.partner_id = rp.id
# #                 JOIN property_sales_supervisor pss ON fl.supervisor_id = pss.id
# #                 JOIN res_users ru_sup ON pss.name = ru_sup.id
# #                 JOIN res_partner rp_sup ON ru_sup.partner_id = rp_sup.id
# #                 LEFT JOIN property_sales_wing psw ON fl.wing_id = psw.id
# #                 LEFT JOIN res_users ru_wing ON psw.manager_id = ru_wing.id
# #                 LEFT JOIN res_partner rp_wing ON ru_wing.partner_id = rp_wing.id
# #                 LEFT JOIN property_wing_config pwc ON fl.wing_id = pwc.id
# #             ),
# #             activity_events AS (
# #                 SELECT 
# #                     cl.id AS lead_id,
# #                     rp.name AS sales_person,
# #                     rp_sup.name AS supervisor_name,
# #                     rp_wing.name AS wing_manager_name,
# #                     COALESCE(pwc.name, psw.name, 'No Wing') AS wing_name,
# #                     CASE 
# #                         WHEN mtv.new_value_char = 'Lost' THEN 'Lost'
# #                         ELSE NULL
# #                     END AS event_type
# #                 FROM crm_lead cl
# #                 JOIN filtered_leads fl ON cl.id = fl.id
# #                 JOIN res_users ru ON cl.user_id = ru.id
# #                 JOIN res_partner rp ON ru.partner_id = rp.id
# #                 JOIN mail_message mm ON mm.model = 'crm.lead' AND mm.res_id = cl.id
# #                 LEFT JOIN mail_tracking_value mtv ON mm.id = mtv.mail_message_id
# #                 JOIN property_sales_supervisor pss ON cl.supervisor_id = pss.id
# #                 JOIN res_users ru_sup ON pss.name = ru_sup.id
# #                 JOIN res_partner rp_sup ON ru_sup.partner_id = rp_sup.id
# #                 LEFT JOIN property_sales_wing psw ON cl.wing_id = psw.id
# #                 LEFT JOIN res_users ru_wing ON psw.manager_id = ru_wing.id
# #                 LEFT JOIN res_partner rp_wing ON ru_wing.partner_id = rp_wing.id
# #                 LEFT JOIN property_wing_config pwc ON cl.wing_id = pwc.id
# #                 WHERE 
# #                     TRIM(BOTH FROM LOWER(COALESCE(mtv.old_value_char, ''))) <> 'sales'
# #                     AND mm.subtype_id <> 5
# #             ),
# #             unioned_events AS (
# #                 SELECT * FROM lead_events
# #                 UNION ALL
# #                 SELECT * FROM activity_events
# #             ),
# #             event_counts AS (
# #                 SELECT 
# #                     wing_name,
# #                     wing_manager_name,
# #                     supervisor_name,
# #                     sales_person,
# #                     event_type,
# #                     COUNT(*) AS count
# #                 FROM unioned_events
# #                 WHERE event_type IS NOT NULL
# #                 GROUP BY wing_name, wing_manager_name, supervisor_name, sales_person, event_type
# #             ),
# #             reservation_summary AS (
# #                 SELECT 
# #                     rp.name AS sales_person,
# #                     rp_sup.name AS supervisor_name,
# #                     rp_wing.name AS wing_manager_name,
# #                     COALESCE(pwc.name, psw.name, 'No Wing') AS wing_name,
# #                     COUNT(pr.id) AS reservation_count,
# #                     SUM(CASE WHEN pr.status = 'sold' THEN 1 ELSE 0 END) AS sold_reservation_count
# #                 FROM property_reservation pr
# #                 JOIN crm_lead cl ON pr.crm_lead_id = cl.id
# #                 JOIN res_users ru ON cl.user_id = ru.id
# #                 JOIN res_partner rp ON ru.partner_id = rp.id
# #                 JOIN property_sales_supervisor pss ON cl.supervisor_id = pss.id
# #                 JOIN res_users ru_sup ON pss.name = ru_sup.id
# #                 JOIN res_partner rp_sup ON ru_sup.partner_id = rp_sup.id
# #                 LEFT JOIN property_sales_wing psw ON cl.wing_id = psw.id
# #                 LEFT JOIN res_users ru_wing ON psw.manager_id = ru_wing.id
# #                 LEFT JOIN res_partner rp_wing ON ru_wing.partner_id = rp_wing.id
# #                 LEFT JOIN property_wing_config pwc ON cl.wing_id = pwc.id
# #                 WHERE cl.create_date >= %s
# #                 GROUP BY wing_name, wing_manager_name, supervisor_name, sales_person
# #             )
# #             SELECT *,
# #                 CASE 
# #                     WHEN wing_name = 'No Wing' AND wing_manager_name IS NOT NULL THEN '🟡 Missing wing_name'
# #                     ELSE '✅ OK'
# #                 END AS data_flag
# #             FROM (
# #                 SELECT
# #                     COALESCE(ec.wing_name, rs.wing_name, 'No Wing') AS wing_name,
# #                     COALESCE(ec.wing_manager_name, rs.wing_manager_name) AS wing_manager_name,
# #                     COALESCE(ec.supervisor_name, rs.supervisor_name) AS supervisor_name,
# #                     COALESCE(ec.sales_person, rs.sales_person) AS sales_person,
# #                     COALESCE(MAX(CASE WHEN ec.event_type = 'Prospect' THEN ec.count END), 0) AS prospect,
# #                     COALESCE(MAX(CASE WHEN ec.event_type = 'Follow Up' THEN ec.count END), 0) AS follow_up,
# #                     COALESCE(MAX(rs.reservation_count), 0) AS reservation_count,
# #                     COALESCE(MAX(rs.sold_reservation_count), 0) AS sold_reservation_count,
# #                     COALESCE(MAX(CASE WHEN ec.event_type = 'Expired' THEN ec.count END), 0) AS expired,
# #                     COALESCE(MAX(CASE WHEN ec.event_type = 'Lost' THEN ec.count END), 0) AS lost
# #                 FROM event_counts ec
# #                 FULL OUTER JOIN reservation_summary rs 
# #                 ON COALESCE(ec.sales_person, '') = COALESCE(rs.sales_person, '')
# #                 AND COALESCE(ec.supervisor_name, '') = COALESCE(rs.supervisor_name, '')
# #                 AND COALESCE(ec.wing_name, 'No Wing') = COALESCE(rs.wing_name, 'No Wing')
# #                 AND COALESCE(ec.wing_manager_name, '') = COALESCE(rs.wing_manager_name, '')
# #                 GROUP BY 
# #                     COALESCE(ec.wing_name, rs.wing_name, 'No Wing'),
# #                     COALESCE(ec.wing_manager_name, rs.wing_manager_name),
# #                     COALESCE(ec.supervisor_name, rs.supervisor_name),
# #                     COALESCE(ec.sales_person, rs.sales_person)
# #             ) final_result
# #             ORDER BY wing_name, wing_manager_name, supervisor_name, sales_person;
# #         """
# #         # Pass start_date as both parameters (to match the query), or adapt as needed for your use case.
# #         self.env.cr.execute(query, (start_date, end_date))
# #         results = self.env.cr.dictfetchall()
# #         print("Wing Dashboard Data:", results)
# #         return results





# from odoo import models, fields, api
# from datetime import datetime

# class CRMLead(models.Model):
#     _inherit = 'crm.lead'
    
#     def get_wing_dashboard_data(self, start_date, end_date=None):
#         if not end_date:
#             end_date = datetime.now().strftime('%Y-%m-%d')
#         query = """
#             WITH filtered_leads AS (
#                 SELECT cl.id, cl.stage_id, cl.user_id, cl.supervisor_id, cl.wing_id
#                 FROM crm_lead cl
#                 WHERE cl.create_date::date BETWEEN %s AND %s
#             ),
#             lead_events AS (
#                 SELECT
#                     fl.id AS lead_id,
#                     rp.name AS sales_person,
#                     rp_sup.name AS supervisor_name,
#                     rp_wing.name AS wing_manager_name,
#                     COALESCE(pwc.name, psw.name, 'No Wing') AS wing_name,
#                     CASE 
#                         WHEN stage.name::jsonb ->> 'en_US' ILIKE '%%expired%%' THEN 'Expired'
#                         WHEN stage.name::jsonb ->> 'en_US' ILIKE '%%won%%' THEN 'Won'
#                         WHEN stage.name::jsonb ->> 'en_US' ILIKE '%%reservation%%' THEN 'Reservation'
#                         WHEN stage.name::jsonb ->> 'en_US' ILIKE '%%follow%%' THEN 'Follow Up'
#                         WHEN stage.name::jsonb ->> 'en_US' ILIKE '%%prospect%%' THEN 'Prospect'
#                         ELSE NULL
#                     END AS event_type
#                 FROM filtered_leads fl
#                 JOIN crm_stage stage ON fl.stage_id = stage.id
#                 JOIN res_users ru ON fl.user_id = ru.id
#                 JOIN res_partner rp ON ru.partner_id = rp.id
#                 JOIN property_sales_supervisor pss ON fl.supervisor_id = pss.id
#                 JOIN res_users ru_sup ON pss.name = ru_sup.id
#                 JOIN res_partner rp_sup ON ru_sup.partner_id = rp_sup.id
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
#                     COALESCE(pwc.name, psw.name, 'No Wing') AS wing_name,
#                     CASE 
#                         WHEN mtv.new_value_char = 'Won' THEN 'Won'
#                         ELSE NULL
#                     END AS event_type
#                 FROM crm_lead cl
#                 JOIN filtered_leads fl ON cl.id = fl.id
#                 JOIN res_users ru ON cl.user_id = ru.id
#                 JOIN res_partner rp ON ru.partner_id = rp.id
#                 JOIN mail_message mm ON mm.model = 'crm.lead' AND mm.res_id = cl.id
#                 LEFT JOIN mail_tracking_value mtv ON mm.id = mtv.mail_message_id
#                 JOIN property_sales_supervisor pss ON cl.supervisor_id = pss.id
#                 JOIN res_users ru_sup ON pss.name = ru_sup.id
#                 JOIN res_partner rp_sup ON ru_sup.partner_id = rp_sup.id
#                 LEFT JOIN property_sales_wing psw ON cl.wing_id = psw.id
#                 LEFT JOIN res_users ru_wing ON psw.manager_id = ru_wing.id
#                 LEFT JOIN res_partner rp_wing ON ru_wing.partner_id = rp_wing.id
#                 LEFT JOIN property_wing_config pwc ON cl.wing_id = pwc.id
#                 WHERE 
#                     TRIM(BOTH FROM LOWER(COALESCE(mtv.old_value_char, ''))) <> 'sales'
#                     AND mm.subtype_id <> 5
#             ),
#             unioned_events AS (
#                 SELECT * FROM lead_events
#                 UNION ALL
#                 SELECT * FROM activity_events
#             ),
#             event_counts AS (
#                 SELECT 
#                     wing_name,
#                     wing_manager_name,
#                     supervisor_name,
#                     sales_person,
#                     event_type,
#                     COUNT(*) AS count
#                 FROM unioned_events
#                 WHERE event_type IS NOT NULL
#                 GROUP BY wing_name, wing_manager_name, supervisor_name, sales_person, event_type
#             ),
#             reservation_summary AS (
#                 SELECT 
#                     rp.name AS sales_person,
#                     rp_sup.name AS supervisor_name,
#                     rp_wing.name AS wing_manager_name,
#                     COALESCE(pwc.name, psw.name, 'No Wing') AS wing_name,
#                     COUNT(pr.id) AS reservation_count,
#                     SUM(CASE WHEN pr.status = 'sold' THEN 1 ELSE 0 END) AS sold_reservation_count
#                 FROM property_reservation pr
#                 JOIN crm_lead cl ON pr.crm_lead_id = cl.id
#                 JOIN res_users ru ON cl.user_id = ru.id
#                 JOIN res_partner rp ON ru.partner_id = rp.id
#                 JOIN property_sales_supervisor pss ON cl.supervisor_id = pss.id
#                 JOIN res_users ru_sup ON pss.name = ru_sup.id
#                 JOIN res_partner rp_sup ON ru_sup.partner_id = rp_sup.id
#                 LEFT JOIN property_sales_wing psw ON cl.wing_id = psw.id
#                 LEFT JOIN res_users ru_wing ON psw.manager_id = ru_wing.id
#                 LEFT JOIN res_partner rp_wing ON ru_wing.partner_id = rp_wing.id
#                 LEFT JOIN property_wing_config pwc ON cl.wing_id = pwc.id
#                 WHERE cl.create_date::date BETWEEN %s AND %s
#                 GROUP BY wing_name, wing_manager_name, supervisor_name, sales_person
#             )
#             SELECT *,
#                 CASE 
#                     WHEN wing_name = 'No Wing' AND wing_manager_name IS NOT NULL THEN '🟡 Missing wing_name'
#                     ELSE '✅ OK'
#                 END AS data_flag
#             FROM (
#                 SELECT
#                     COALESCE(ec.wing_name, rs.wing_name, 'No Wing') AS wing_name,
#                     COALESCE(ec.wing_manager_name, rs.wing_manager_name) AS wing_manager_name,
#                     COALESCE(ec.supervisor_name, rs.supervisor_name) AS supervisor_name,
#                     COALESCE(ec.sales_person, rs.sales_person) AS sales_person,
#                     COALESCE(MAX(CASE WHEN ec.event_type = 'Prospect' THEN ec.count END), 0) AS prospect,
#                     COALESCE(MAX(CASE WHEN ec.event_type = 'Follow Up' THEN ec.count END), 0) AS follow_up,
#                     COALESCE(MAX(CASE WHEN ec.event_type = 'Won' THEN ec.count END), 0) AS won,
#                     COALESCE(MAX(CASE WHEN ec.event_type = 'Expired' THEN ec.count END), 0) AS expired,
#                     COALESCE(MAX(rs.reservation_count), 0) AS reservation_count,
#                     COALESCE(MAX(rs.sold_reservation_count), 0) AS sold_reservation_count
#                 FROM event_counts ec
#                 FULL OUTER JOIN reservation_summary rs 
#                 ON COALESCE(ec.sales_person, '') = COALESCE(rs.sales_person, '')
#                 AND COALESCE(ec.supervisor_name, '') = COALESCE(rs.supervisor_name, '')
#                 AND COALESCE(ec.wing_name, 'No Wing') = COALESCE(rs.wing_name, 'No Wing')
#                 AND COALESCE(ec.wing_manager_name, '') = COALESCE(rs.wing_manager_name, '')
#                 GROUP BY 
#                     COALESCE(ec.wing_name, rs.wing_name, 'No Wing'),
#                     COALESCE(ec.wing_manager_name, rs.wing_manager_name),
#                     COALESCE(ec.supervisor_name, rs.supervisor_name),
#                     COALESCE(ec.sales_person, rs.sales_person)
#             ) final_result
#             ORDER BY data_flag DESC, wing_name, supervisor_name, sales_person;
#         """
#         self.env.cr.execute(query, (start_date, end_date, start_date, end_date))
#         results = self.env.cr.dictfetchall()
#         return results







from odoo import models, fields, api
from datetime import datetime

class CRMLead(models.Model):
    _inherit = 'crm.lead'

    def get_wing_dashboard_data(self, start_date, end_date=None):
        # ensure end_date is provided
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        query = """
            WITH filtered_leads AS (
                SELECT cl.id, cl.stage_id, cl.user_id, cl.supervisor_id, cl.wing_id
                FROM crm_lead cl
                WHERE cl.create_date::date BETWEEN %s AND %s
            ),
            lead_events AS (
                SELECT
                    fl.id AS lead_id,
                    rp.name AS sales_person,
                    rp_sup.name AS supervisor_name,
                    rp_wing.name AS wing_manager_name,
                    COALESCE(pwc.name, psw.name, 'No Wing') AS wing_name,
                    CASE 
                        WHEN stage.name::jsonb ->> 'en_US' ILIKE '%%expired%%' THEN 'Expired'
                        WHEN stage.name::jsonb ->> 'en_US' ILIKE '%%won%%' THEN 'Won'
                        WHEN stage.name::jsonb ->> 'en_US' ILIKE '%%reservation%%' THEN 'Reservation'
                        WHEN stage.name::jsonb ->> 'en_US' ILIKE '%%follow%%' THEN 'Follow Up'
                        WHEN stage.name::jsonb ->> 'en_US' ILIKE '%%prospect%%' THEN 'Prospect'
                        ELSE NULL
                    END AS event_type
                FROM filtered_leads fl
                JOIN crm_stage stage ON fl.stage_id = stage.id
                JOIN res_users ru ON fl.user_id = ru.id
                JOIN res_partner rp ON ru.partner_id = rp.id
                JOIN property_sales_supervisor pss ON fl.supervisor_id = pss.id
                JOIN res_users ru_sup ON pss.name = ru_sup.id
                JOIN res_partner rp_sup ON ru_sup.partner_id = rp_sup.id
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
                    COALESCE(pwc.name, psw.name, 'No Wing') AS wing_name,
                    CASE 
                        WHEN mtv.new_value_char = 'Won' THEN 'Won'
                        ELSE NULL
                    END AS event_type
                FROM crm_lead cl
                JOIN filtered_leads fl ON cl.id = fl.id
                JOIN res_users ru ON cl.user_id = ru.id
                JOIN res_partner rp ON ru.partner_id = rp.id
                JOIN mail_message mm ON mm.model = 'crm.lead' AND mm.res_id = cl.id
                LEFT JOIN mail_tracking_value mtv ON mm.id = mtv.mail_message_id
                JOIN property_sales_supervisor pss ON cl.supervisor_id = pss.id
                JOIN res_users ru_sup ON pss.name = ru_sup.id
                JOIN res_partner rp_sup ON ru_sup.partner_id = rp_sup.id
                LEFT JOIN property_sales_wing psw ON cl.wing_id = psw.id
                LEFT JOIN res_users ru_wing ON psw.manager_id = ru_wing.id
                LEFT JOIN res_partner rp_wing ON ru_wing.partner_id = rp_wing.id
                LEFT JOIN property_wing_config pwc ON cl.wing_id = pwc.id
                WHERE 
                    TRIM(BOTH FROM LOWER(COALESCE(mtv.old_value_char, ''))) <> 'sales'
                    AND mm.subtype_id <> 5
            ),
            unioned_events AS (
                SELECT * FROM lead_events
                UNION ALL
                SELECT * FROM activity_events
            ),
            event_counts AS (
                SELECT 
                    wing_name,
                    wing_manager_name,
                    supervisor_name,
                    sales_person,
                    event_type,
                    COUNT(*) AS count
                FROM unioned_events
                WHERE event_type IS NOT NULL
                GROUP BY wing_name, wing_manager_name, supervisor_name, sales_person, event_type
            ),
            reservation_summary AS (
                SELECT 
                    rp.name AS sales_person,
                    rp_sup.name AS supervisor_name,
                    rp_wing.name AS wing_manager_name,
                    COALESCE(pwc.name, psw.name, 'No Wing') AS wing_name,
                    COUNT(pr.id) AS reservation_count,
                    SUM(CASE WHEN pr.status = 'sold' THEN 1 ELSE 0 END) AS sold_reservation_count
                FROM property_reservation pr
                JOIN crm_lead cl ON pr.crm_lead_id = cl.id
                JOIN res_users ru ON cl.user_id = ru.id
                JOIN res_partner rp ON ru.partner_id = rp.id
                JOIN property_sales_supervisor pss ON cl.supervisor_id = pss.id
                JOIN res_users ru_sup ON pss.name = ru_sup.id
                JOIN res_partner rp_sup ON ru_sup.partner_id = rp_sup.id
                LEFT JOIN property_sales_wing psw ON cl.wing_id = psw.id
                LEFT JOIN res_users ru_wing ON psw.manager_id = ru_wing.id
                LEFT JOIN res_partner rp_wing ON ru_wing.partner_id = rp_wing.id
                LEFT JOIN property_wing_config pwc ON cl.wing_id = pwc.id
                WHERE cl.create_date::date BETWEEN %s AND %s
                GROUP BY wing_name, wing_manager_name, supervisor_name, sales_person
            )
            SELECT *,
                CASE 
                    WHEN wing_name = 'No Wing' AND wing_manager_name IS NOT NULL THEN '🟡 Missing wing_name'
                    ELSE '✅ OK'
                END AS data_flag
            FROM (
                SELECT
                    COALESCE(ec.wing_name, rs.wing_name, 'No Wing') AS wing_name,
                    COALESCE(ec.wing_manager_name, rs.wing_manager_name) AS wing_manager_name,
                    COALESCE(ec.supervisor_name, rs.supervisor_name) AS supervisor_name,
                    COALESCE(ec.sales_person, rs.sales_person) AS sales_person,
                    COALESCE(MAX(CASE WHEN ec.event_type = 'Prospect' THEN ec.count END), 0) AS prospect,
                    COALESCE(MAX(CASE WHEN ec.event_type = 'Follow Up' THEN ec.count END), 0) AS follow_up,
                    COALESCE(MAX(CASE WHEN ec.event_type = 'Won' THEN ec.count END), 0) AS won,
                    COALESCE(MAX(CASE WHEN ec.event_type = 'Expired' THEN ec.count END), 0) AS expired,
                    COALESCE(MAX(rs.reservation_count), 0) AS reservation_count,
                    COALESCE(MAX(rs.sold_reservation_count), 0) AS sold_reservation_count
                FROM event_counts ec
                FULL OUTER JOIN reservation_summary rs 
                ON COALESCE(ec.sales_person, '') = COALESCE(rs.sales_person, '')
                AND COALESCE(ec.supervisor_name, '') = COALESCE(rs.supervisor_name, '')
                AND COALESCE(ec.wing_name, 'No Wing') = COALESCE(rs.wing_name, 'No Wing')
                AND COALESCE(ec.wing_manager_name, '') = COALESCE(rs.wing_manager_name, '')
                GROUP BY 
                    COALESCE(ec.wing_name, rs.wing_name, 'No Wing'),
                    COALESCE(ec.wing_manager_name, rs.wing_manager_name),
                    COALESCE(ec.supervisor_name, rs.supervisor_name),
                    COALESCE(ec.sales_person, rs.sales_person)
            ) final_result
            ORDER BY data_flag DESC, wing_name, supervisor_name, sales_person;
        """
        self.env.cr.execute(query, (start_date, end_date, start_date, end_date))
        results = self.env.cr.dictfetchall()
        print("Wing Dashboard Data:", results)
        return results
