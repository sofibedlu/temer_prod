from odoo import models, api, fields

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    @api.model
    def get_my_sales_summary(self, date_to=None):
        user_id = self.env.uid
        date_to = date_to or fields.Date.context_today(self)
        query = """
            WITH filtered_leads AS (
                SELECT cl.id, cl.stage_id, cl.user_id
                FROM crm_lead cl
                WHERE cl.create_date <= %s AND cl.user_id = %s
            ),
            lead_events AS (
                SELECT
                    fl.id AS lead_id,
                    rp.name AS sales_person,
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
            ),
            activity_events AS (
                SELECT 
                    cl.id AS lead_id,
                    rp.name AS sales_person,
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
                    sales_person,
                    event_type,
                    COUNT(*) AS count
                FROM unioned_events
                WHERE event_type IS NOT NULL
                GROUP BY sales_person, event_type
            ),
            reservation_summary AS (
                SELECT 
                    rp.name AS sales_person,
                    COUNT(pr.id) AS reservation_count,
                    SUM(CASE WHEN pr.status = 'sold' THEN 1 ELSE 0 END) AS sold_reservation_count
                FROM property_reservation pr
                JOIN crm_lead cl ON pr.crm_lead_id = cl.id
                JOIN res_users ru ON cl.user_id = ru.id
                JOIN res_partner rp ON ru.partner_id = rp.id
                WHERE cl.create_date <= %s AND cl.user_id = %s
                GROUP BY rp.name
            )
            SELECT
                COALESCE(ec.sales_person, rs.sales_person) AS sales_person,
                COALESCE(MAX(CASE WHEN ec.event_type = 'Prospect' THEN ec.count END), 0) AS prospect,
                COALESCE(MAX(CASE WHEN ec.event_type = 'Follow Up' THEN ec.count END), 0) AS follow_up,
                COALESCE(MAX(CASE WHEN ec.event_type = 'Won' THEN ec.count END), 0) AS won,
                COALESCE(MAX(CASE WHEN ec.event_type = 'Expired' THEN ec.count END), 0) AS expired,
                COALESCE(MAX(rs.reservation_count), 0) AS reservation_count,
                COALESCE(MAX(rs.sold_reservation_count), 0) AS sold_reservation_count
            FROM event_counts ec
            FULL OUTER JOIN reservation_summary rs ON ec.sales_person = rs.sales_person
            GROUP BY COALESCE(ec.sales_person, rs.sales_person)
            ORDER BY sales_person
        """
        self.env.cr.execute(query, (date_to, user_id, date_to, user_id))
        columns = [desc[0] for desc in self.env.cr.description]
        results = [dict(zip(columns, row)) for row in self.env.cr.fetchall()]
        
        # Filter for current user only (though query should already do this)
        return [r for r in results if r['sales_person'] == self.env.user.partner_id.name]