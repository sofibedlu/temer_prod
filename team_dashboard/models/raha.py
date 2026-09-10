from odoo import models, fields
from datetime import datetime
from collections import defaultdict
import json
import logging

_logger = logging.getLogger(__name__)

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    def get_wing_dashboard_data_raha(self, start_date=None, end_date=None):
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')

        query = """
            WITH 
            all_supervisors AS (
                SELECT DISTINCT
                    pss.id AS supervisor_id,
                    rp_sup.name AS supervisor_name
                FROM property_sales_supervisor pss
                JOIN res_users ru_sup ON pss.name = ru_sup.id
                JOIN res_partner rp_sup ON ru_sup.partner_id = rp_sup.id
                WHERE EXISTS (
                    SELECT 1 FROM crm_lead 
                    WHERE supervisor_id = pss.id
                )
            ),
            filtered_leads AS (
                SELECT 
                    cl.id AS lead_id,
                    cl.create_date,
                    cl.stage_id,
                    s.name::jsonb->>'en_US' AS stage_name,
                    cl.user_id,
                    up.name AS sales_person,
                    cl.supervisor_id,
                    COALESCE(asup.supervisor_name, 'No Supervisor') AS supervisor_name,
                    'Team - Raha' AS wing_name,
                    '' AS wing_manager_name
                FROM 
                    crm_lead cl
                LEFT JOIN all_supervisors asup ON cl.supervisor_id = asup.supervisor_id
                LEFT JOIN crm_stage s ON cl.stage_id = s.id
                LEFT JOIN res_users u ON cl.user_id = u.id
                LEFT JOIN res_partner up ON u.partner_id = up.id
                LEFT JOIN property_sales_wing psw ON cl.wing_id = psw.id
                WHERE 
                    psw.name = 'Team - Raha'
            ),
            lead_events AS (
                SELECT
                    lead_id,
                    sales_person,
                    supervisor_name,
                    wing_manager_name,
                    wing_name,
                    CASE
                        WHEN stage_name IS NULL THEN NULL
                        WHEN LOWER(stage_name::text) LIKE '%%expired%%' THEN 'Expired'
                        WHEN LOWER(stage_name::text) LIKE '%%won%%' THEN 'Won'
                        WHEN LOWER(stage_name::text) LIKE '%%reservation%%' THEN 'Reservation'
                        WHEN LOWER(stage_name::text) LIKE '%%follow%%' THEN 'Follow Up'
                        WHEN LOWER(stage_name::text) LIKE '%%prospect%%' THEN 'Prospect'
                    END AS event_type
                FROM 
                    filtered_leads
            ),
            activity_events AS (
                SELECT
                    fl.lead_id,
                    fl.sales_person,
                    fl.supervisor_name,
                    fl.wing_manager_name,
                    fl.wing_name,
                    'Won' AS event_type
                FROM
                    mail_message mm
                JOIN
                    filtered_leads fl ON mm.res_id = fl.lead_id
                JOIN
                    mail_tracking_value mtv ON mm.id = mtv.mail_message_id
                WHERE
                    mm.model = 'crm.lead'
                    AND mm.subtype_id != 5
                    AND mtv.new_value_char = 'Won'
                    AND mtv.old_value_char != 'sales'
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
                    COUNT(CASE WHEN event_type = 'Prospect' THEN 1 END) AS prospect,
                    COUNT(CASE WHEN event_type = 'Follow Up' THEN 1 END) AS follow_up,
                    COUNT(CASE WHEN event_type = 'Won' THEN 1 END) AS won,
                    COUNT(CASE WHEN event_type = 'Expired' THEN 1 END) AS expired
                FROM
                    unioned_events
                GROUP BY
                    wing_name, wing_manager_name, supervisor_name, sales_person
            ),
            reservation_counts AS (
                SELECT
                    fl.wing_name,
                    fl.wing_manager_name,
                    fl.supervisor_name,
                    fl.sales_person,
                    COUNT(pr.id) AS reservation_count,
                    COUNT(CASE WHEN pr.status = 'sold' THEN 1 END) AS sold_reservation_count
                FROM
                    property_reservation pr
                JOIN
                    filtered_leads fl ON pr.crm_lead_id = fl.lead_id
                GROUP BY
                    fl.wing_name, fl.wing_manager_name, fl.supervisor_name, fl.sales_person
            )
            SELECT
                COALESCE(ec.wing_name, rc.wing_name) AS wing_name,
                COALESCE(ec.wing_manager_name, rc.wing_manager_name) AS wing_manager_name,
                COALESCE(ec.supervisor_name, rc.supervisor_name) AS supervisor_name,
                COALESCE(ec.sales_person, rc.sales_person) AS sales_person,
                COALESCE(ec.prospect, 0) AS prospect,
                COALESCE(ec.follow_up, 0) AS follow_up,
                COALESCE(ec.won, 0) AS won,
                COALESCE(ec.expired, 0) AS expired,
                COALESCE(rc.reservation_count, 0) AS reservation_count,
                COALESCE(rc.sold_reservation_count, 0) AS sold_reservation_count,
                asup.supervisor_id
            FROM
                event_counts ec
            FULL OUTER JOIN
                reservation_counts rc ON 
                    ec.wing_name = rc.wing_name AND
                    ec.wing_manager_name = rc.wing_manager_name AND
                    ec.supervisor_name = rc.supervisor_name AND
                    ec.sales_person = rc.sales_person
            LEFT JOIN
                all_supervisors asup ON COALESCE(ec.supervisor_name, rc.supervisor_name) = asup.supervisor_name
            """

        self.env.cr.execute(query)
        results = self.env.cr.dictfetchall()

        for record in results:
            data_flag = '🟡 Missing wing_name' if record['wing_name'] == 'No Wing' and record['wing_manager_name'] else '✅ OK'
            record['data_flag'] = data_flag
            # Set supervisor_id as integer or null instead of array
            record['supervisor_id'] = record['supervisor_id'] or 0 if record['supervisor_name'] != 'No Supervisor' else 0

        results.sort(key=lambda x: (
            x['data_flag'] != '✅ OK',
            x['wing_name'] or '',
            x['supervisor_name'] or '',
            x['sales_person'] or ''
        ))

        # Log supervisor info more accurately
        unique_supervisors = {r['supervisor_name'] for r in results if r['supervisor_name'] != 'No Supervisor'}
        _logger.info(f"Found {len(results)} records with {len(unique_supervisors)} unique supervisors: {', '.join(unique_supervisors)}")
        if not unique_supervisors:
            _logger.warning("No active supervisors found.")
            all_sups = self.env['property.sales.supervisor'].search([])
            _logger.info(f"Total supervisors in system: {len(all_sups)}")
            for sup in all_sups:
                if sup.name and sup.name not in {r['supervisor_name'] for r in results}:
                    results.append({
                        'supervisor_name': sup.name.name,  # Access res.users name
                        'supervisor_id': sup.id,
                        'wing_name': 'Team - Raha',
                        'sales_person': 'No recent leads',
                        'prospect': 0,
                        'follow_up': 0,
                        'won': 0,
                        'expired': 0,
                        'reservation_count': 0,
                        'sold_reservation_count': 0,
                        'data_flag': '⚪ No leads'
                    })

        return results