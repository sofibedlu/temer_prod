# from odoo import models, fields,api
# from datetime import datetime
# from collections import defaultdict
# from odoo.exceptions import ValidationError
# import json

# class CrmLead(models.Model):
#     _inherit = 'crm.lead'
#     @api.model
#     def get_wing_dashboard_data_ajwa(self, start_date, end_date=None):
#         if not end_date:
#             end_date = datetime.now().strftime('%Y-%m-%d')

#         # Convert dates to datetime objects
#         start_date = fields.Date.from_string(start_date)
#         end_date = fields.Date.from_string(end_date)
       
#         # 1. Fetch filtered leads
#         leads = self.env['crm.lead'].search([
#             ('create_date', '>=', start_date),
#             ('create_date', '<=', end_date),
#             ('wing_id.name', '=', 'Team - Ajwa')  # Filter for wing_name = 'Team - Ajwa'
#         ])

#         # 2. Process lead events
#         lead_events = []
#         for lead in leads:
#             stage_name = lead.stage_id.name
#             event_type = None
#             if stage_name:
#                 stage_name_en = json.loads(stage_name).get('en_US', '').lower()
#                 if 'expired' in stage_name_en:
#                     event_type = 'Expired'
#                 elif 'won' in stage_name_en:
#                     event_type = 'Won'
#                 elif 'reservation' in stage_name_en:
#                     event_type = 'Reservation'
#                 elif 'follow' in stage_name_en:
#                     event_type = 'Follow Up'
#                 elif 'prospect' in stage_name_en:
#                     event_type = 'Prospect'

#             if event_type:
#                 wing_name = lead.wing_id.name or 'No Wing'
#                 if wing_name == 'Team - Ajwa':  # Additional check to ensure only Team - Ajwa
#                     lead_events.append({
#                         'lead_id': lead.id,
#                         'sales_person': lead.user_id.partner_id.name or '',
#                         'supervisor_name': lead.supervisor_id.name.partner_id.name if lead.supervisor_id and lead.supervisor_id.name else '',
#                         'wing_manager_name': lead.wing_id.manager_id.partner_id.name if lead.wing_id and lead.wing_id.manager_id else '',
#                         'wing_name': wing_name,
#                         'event_type': event_type
#                     })

#         # 3. Process activity events (mail tracking for 'Won')
#         activity_events = []
#         messages = self.env['mail.message'].search([
#             ('model', '=', 'crm.lead'),
#             ('res_id', 'in', leads.ids),
#             ('subtype_id', '!=', 5)
#         ])
#         for message in messages:
#             tracking_values = self.env['mail.tracking.value'].search([
#                 ('mail_message_id', '=', message.id),
#                 ('new_value_char', '=', 'Won'),
#                 ('old_value_char', '!=', 'sales')
#             ])
#             if tracking_values:
#                 lead = self.env['crm.lead'].browse(message.res_id)
#                 wing_name = lead.wing_id.name or 'No Wing'
#                 if wing_name == 'Team - Ajwa':  # Filter for Team - Ajwa
#                     activity_events.append({
#                         'lead_id': lead.id,
#                         'sales_person': lead.user_id.partner_id.name or '',
#                         'supervisor_name': lead.supervisor_id.name.partner_id.name if lead.supervisor_id and lead.supervisor_id.name else '',
#                         'wing_manager_name': lead.wing_id.manager_id.partner_id.name if lead.wing_id and lead.wing_id.manager_id else '',
#                         'wing_name': wing_name,
#                         'event_type': 'Won'
#                     })

#         # 4. Combine events
#         unioned_events = lead_events + activity_events

#         # 5. Count events
#         event_counts = defaultdict(lambda: {
#             'wing_name': None,
#             'wing_manager_name': None,
#             'supervisor_name': None,
#             'sales_person': None,
#             'prospect': 0,
#             'follow_up': 0,
#             'won': 0,
#             'expired': 0
#         })
#         for event in unioned_events:
#             key = (
#                 event['wing_name'],
#                 event['wing_manager_name'],
#                 event['supervisor_name'],
#                 event['sales_person']
#             )
#             event_counts[key]['wing_name'] = event['wing_name']
#             event_counts[key]['wing_manager_name'] = event['wing_manager_name']
#             event_counts[key]['supervisor_name'] = event['supervisor_name']
#             event_counts[key]['sales_person'] = event['sales_person']
#             if event['event_type'] == 'Prospect':
#                 event_counts[key]['prospect'] += 1
#             elif event['event_type'] == 'Follow Up':
#                 event_counts[key]['follow_up'] += 1
#             elif event['event_type'] == 'Won':
#                 event_counts[key]['won'] += 1
#             elif event['event_type'] == 'Expired':
#                 event_counts[key]['expired'] += 1

#         # 6. Fetch reservation summary
#         reservations = self.env['property.reservation'].search([
#             ('crm_lead_id.create_date', '>=', '2025-01-01'),
#             ('crm_lead_id.wing_id.name', '=', 'Team - Ajwa')  # Filter for Team - Ajwa
#         ])
#         reservation_counts = defaultdict(lambda: {
#             'wing_name': None,
#             'wing_manager_name': None,
#             'supervisor_name': None,
#             'sales_person': None,
#             'reservation_count': 0,
#             'sold_reservation_count': 0
#         })
#         for reservation in reservations:
#             lead = reservation.crm_lead_id
#             wing_name = lead.wing_id.name or 'No Wing'
#             if wing_name == 'Team - Ajwa':  # Filter for Team - Ajwa
#                 key = (
#                     wing_name,
#                     lead.wing_id.manager_id.partner_id.name if lead.wing_id and lead.wing_id.manager_id else '',
#                     lead.supervisor_id.name.partner_id.name if lead.supervisor_id and lead.supervisor_id.name else '',
#                     lead.user_id.partner_id.name or ''
#                 )
#                 reservation_counts[key]['wing_name'] = wing_name
#                 reservation_counts[key]['wing_manager_name'] = lead.wing_id.manager_id.partner_id.name if lead.wing_id and lead.wing_id.manager_id else ''
#                 reservation_counts[key]['supervisor_name'] = lead.supervisor_id.name.partner_id.name if lead.supervisor_id and lead.supervisor_id.name else ''
#                 reservation_counts[key]['sales_person'] = lead.user_id.partner_id.name or ''
#                 reservation_counts[key]['reservation_count'] += 1
#                 if reservation.status == 'sold':
#                     reservation_counts[key]['sold_reservation_count'] += 1

#         # 7. Combine event and reservation counts
#         result = []
#         all_keys = set(event_counts.keys()) | set(reservation_counts.keys())
#         for key in all_keys:
#             wing_name, wing_manager_name, supervisor_name, sales_person = key
#             # Find a lead to get supervisor_id and supervisor_name if possible
#             supervisor_id = None
#             supervisor_name_val = supervisor_name or ''
#             for lead in leads:
#                 if lead.supervisor_id:
#                     if lead.supervisor_id.name and lead.supervisor_id.name.partner_id.name == supervisor_name:
#                         supervisor_id = [lead.supervisor_id.id, lead.supervisor_id.name.partner_id.name]
#                         supervisor_name_val = lead.supervisor_id.name.partner_id.name
#                         break
#             # If not found, set supervisor_id to None or [0, 'No Supervisor']
#             if not supervisor_id:
#                 supervisor_id = [0, 'No Supervisor']
#             data_flag = '🟡 Missing wing_name' if wing_name == 'No Wing' and wing_manager_name else '✅ OK'
#             record = {
#                 'wing_name': wing_name,
#                 'wing_manager_name': wing_manager_name,
#                 'supervisor_name': supervisor_name_val,
#                 'supervisor_id': supervisor_id,
#                 'sales_person': sales_person,
#                 'prospect': event_counts[key]['prospect'] if key in event_counts else 0,
#                 'follow_up': event_counts[key]['follow_up'] if key in event_counts else 0,
#                 'won': event_counts[key]['won'] if key in event_counts else 0,
#                 'expired': event_counts[key]['expired'] if key in event_counts else 0,
#                 'reservation_count': reservation_counts[key]['reservation_count'] if key in reservation_counts else 0,
#                 'sold_reservation_count': reservation_counts[key]['sold_reservation_count'] if key in reservation_counts else 0,
#                 'data_flag': data_flag
#             }
#             result.append(record)

#         # 8. Sort results with None handling
#         def safe_str(value):
#             return value or ''  # Convert None to empty string for sorting

#         result.sort(key=lambda x: (
#             x['data_flag'] != '✅ OK',
#             safe_str(x['wing_name']),
#             safe_str(x['supervisor_name']),
#             safe_str(x['sales_person'])
#         ))
#         print("this is the result for Ajwa")
#         print(result)

#         return result

#     def get_wing_dashboard_data_ajwa(self, start_date, end_date=None):
#         # Ensure end_date is provided   
#         if not end_date:
#             end_date = datetime.now().strftime('%Y-%m-%d')

#         # Convert dates to datetime objects
#         start_date = fields.Date.from_string(start_date)
#         end_date = fields.Date.from_string(end_date)

#         # 1. Fetch filtered leads
#         leads = self.env['crm.lead'].search([
#             ('create_date', '>=', start_date),
#             ('create_date', '<=', end_date),
#             ('wing_id.name', '=', 'Team - Ajwa')  # Filter for wing_name = 'Team - Ajwa'
#         ])

#         # 2. Process lead events
#         lead_events = []
#         for lead in leads:
#             stage_name = lead.stage_id.name
#             event_type = None
#             if stage_name:
#                 stage_name_lc = stage_name.lower()
#                 if 'expired' in stage_name_lc:
#                     event_type = 'Expired'
#                 elif 'won' in stage_name_lc:
#                     event_type = 'Won'
#                 elif 'reservation' in stage_name_lc:
#                     event_type = 'Reservation'
#                 elif 'follow' in stage_name_lc:
#                     event_type = 'Follow Up'
#                 elif 'prospect' in stage_name_lc:
#                     event_type = 'Prospect'

#             if event_type:
#                 wing_name = lead.wing_id.name or 'No Wing'
#                 if wing_name == 'Team - Ajwa':  # Additional check to ensure only Team - Ajwa
#                     lead_events.append({
#                         'lead_id': lead.id,
#                         'sales_person': lead.user_id.partner_id.name or '',
#                         'supervisor_name': lead.supervisor_id.name.partner_id.name if lead.supervisor_id and lead.supervisor_id.name else '',
#                         'wing_manager_name': lead.wing_id.manager_id.partner_id.name if lead.wing_id and lead.wing_id.manager_id else '',
#                         'wing_name': wing_name,
#                         'event_type': event_type
#                     })

#         # 3. Process activity events (mail tracking for 'Won')
#         activity_events = []
#         messages = self.env['mail.message'].search([
#             ('model', '=', 'crm.lead'),
#             ('res_id', 'in', leads.ids),
#             ('subtype_id', '!=', 5)
#         ])
#         for message in messages:
#             tracking_values = self.env['mail.tracking.value'].search([
#                 ('mail_message_id', '=', message.id),
#                 ('new_value_char', '=', 'Won'),
#                 ('old_value_char', '!=', 'sales')
#             ])
#             if tracking_values:
#                 lead = self.env['crm.lead'].browse(message.res_id)
#                 wing_name = lead.wing_id.name or 'No Wing'
#                 if wing_name == 'Team - Ajwa':  # Filter for Team - Ajwa
#                     activity_events.append({
#                         'lead_id': lead.id,
#                         'sales_person': lead.user_id.partner_id.name or '',
#                         'supervisor_name': lead.supervisor_id.name.partner_id.name if lead.supervisor_id and lead.supervisor_id.name else '',
#                         'wing_manager_name': lead.wing_id.manager_id.partner_id.name if lead.wing_id and lead.wing_id.manager_id else '',
#                         'wing_name': wing_name,
#                         'event_type': 'Won'
#                     })

#         # 4. Combine events
#         unioned_events = lead_events + activity_events

#         # 5. Count events
#         event_counts = defaultdict(lambda: {
#             'wing_name': None,
#             'wing_manager_name': None,
#             'supervisor_name': None,
#             'sales_person': None,
#             'prospect': 0,
#             'follow_up': 0,
#             'won': 0,
#             'expired': 0
#         })
#         for event in unioned_events:
#             key = (
#                 event['wing_name'],
#                 event['wing_manager_name'],
#                 event['supervisor_name'],
#                 event['sales_person']
#             )
#             event_counts[key]['wing_name'] = event['wing_name']
#             event_counts[key]['wing_manager_name'] = event['wing_manager_name']
#             event_counts[key]['supervisor_name'] = event['supervisor_name']
#             event_counts[key]['sales_person'] = event['sales_person']
#             if event['event_type'] == 'Prospect':
#                 event_counts[key]['prospect'] += 1
#             elif event['event_type'] == 'Follow Up':
#                 event_counts[key]['follow_up'] += 1
#             elif event['event_type'] == 'Won':
#                 event_counts[key]['won'] += 1
#             elif event['event_type'] == 'Expired':
#                 event_counts[key]['expired'] += 1

#         # 6. Fetch reservation summary
#         reservations = self.env['property.reservation'].search([
#             ('crm_lead_id.create_date', '>=', '2025-01-01'),
#             ('crm_lead_id.wing_id.name', '=', 'Team - Ajwa')  # Filter for Team - Ajwa
#         ])
#         reservation_counts = defaultdict(lambda: {
#             'wing_name': None,
#             'wing_manager_name': None,
#             'supervisor_name': None,
#             'sales_person': None,
#             'reservation_count': 0,
#             'sold_reservation_count': 0
#         })
#         for reservation in reservations:
#             lead = reservation.crm_lead_id
#             wing_name = lead.wing_id.name or 'No Wing'
#             if wing_name == 'Team - Ajwa':  # Filter for Team - Ajwa
#                 key = (
#                     wing_name,
#                     lead.wing_id.manager_id.partner_id.name if lead.wing_id and lead.wing_id.manager_id else '',
#                     lead.supervisor_id.name.partner_id.name if lead.supervisor_id and lead.supervisor_id.name else '',
#                     lead.user_id.partner_id.name or ''
#                 )
#                 reservation_counts[key]['wing_name'] = wing_name
#                 reservation_counts[key]['wing_manager_name'] = lead.wing_id.manager_id.partner_id.name if lead.wing_id and lead.wing_id.manager_id else ''
#                 reservation_counts[key]['supervisor_name'] = lead.supervisor_id.name.partner_id.name if lead.supervisor_id and lead.supervisor_id.name else ''
#                 reservation_counts[key]['sales_person'] = lead.user_id.partner_id.name or ''
#                 reservation_counts[key]['reservation_count'] += 1
#                 if reservation.status == 'sold':
#                     reservation_counts[key]['sold_reservation_count'] += 1

#         # 7. Combine event and reservation counts
#         result = []
#         all_keys = set(event_counts.keys()) | set(reservation_counts.keys())
#         for key in all_keys:
#             wing_name, wing_manager_name, supervisor_name, sales_person = key
#             # Find a lead to get supervisor_id and supervisor_name if possible
#             supervisor_id = None
#             supervisor_name_val = supervisor_name or ''
#             for lead in leads:
#                 if lead.supervisor_id:
#                     if lead.supervisor_id.name and lead.supervisor_id.name.partner_id.name == supervisor_name:
#                         supervisor_id = [lead.supervisor_id.id, lead.supervisor_id.name.partner_id.name]
#                         supervisor_name_val = lead.supervisor_id.name.partner_id.name
#                         break
#             # If not found, set supervisor_id to None or [0, 'No Supervisor']
#             if not supervisor_id:
#                 supervisor_id = [0, 'No Supervisor']
#             data_flag = '🟡 Missing wing_name' if wing_name == 'No Wing' and wing_manager_name else '✅ OK'
#             record = {
#                 'wing_name': wing_name,
#                 'wing_manager_name': wing_manager_name,
#                 'supervisor_name': supervisor_name_val,
#                 'supervisor_id': supervisor_id,
#                 'sales_person': sales_person,
#                 'prospect': event_counts[key]['prospect'] if key in event_counts else 0,
#                 'follow_up': event_counts[key]['follow_up'] if key in event_counts else 0,
#                 'won': event_counts[key]['won'] if key in event_counts else 0,
#                 'expired': event_counts[key]['expired'] if key in event_counts else 0,
#                 'reservation_count': reservation_counts[key]['reservation_count'] if key in reservation_counts else 0,
#                 'sold_reservation_count': reservation_counts[key]['sold_reservation_count'] if key in reservation_counts else 0,
#                 'data_flag': data_flag
#             }
#             result.append(record)

#         # 8. Sort results with None handling
#         def safe_str(value):
#             return value or ''  # Convert None to empty string for sorting

#         result.sort(key=lambda x: (
#             x['data_flag'] != '✅ OK',
#             safe_str(x['wing_name']),
#             safe_str(x['supervisor_name']),
#             safe_str(x['sales_person'])
#         ))
#         print("this is the result for Ajwa")
#         print(result)

#         return result






from odoo import models, fields
from datetime import datetime
from collections import defaultdict
import json
import logging

_logger = logging.getLogger(__name__)

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    def get_wing_dashboard_data_ajwa(self, start_date=None, end_date=None):
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
                    'Team - Ajwa' AS wing_name,
                    '' AS wing_manager_name
                FROM 
                    crm_lead cl
                LEFT JOIN all_supervisors asup ON cl.supervisor_id = asup.supervisor_id
                LEFT JOIN crm_stage s ON cl.stage_id = s.id
                LEFT JOIN res_users u ON cl.user_id = u.id
                LEFT JOIN res_partner up ON u.partner_id = up.id
                LEFT JOIN property_sales_wing psw ON cl.wing_id = psw.id
                WHERE 
                    psw.name = 'Team - Ajwa'
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
                asup.supervisor_id,
                'Team Ajwa' AS classification_flag
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

        # Sort by supervisor_name, sales_person as per the SQL query
        results.sort(key=lambda x: (
            x['supervisor_name'] or '',
            x['sales_person'] or ''
        ))

        # Log supervisor info
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
                        'wing_name': 'Team - Ajwa',
                        'sales_person': 'No recent leads',
                        'prospect': 0,
                        'follow_up': 0,
                        'won': 0,
                        'expired': 0,
                        'reservation_count': 0,
                        'sold_reservation_count': 0,
                        'data_flag': '⚪ No leads',
                        'classification_flag': 'Team Ajwa'
                    })

        return results