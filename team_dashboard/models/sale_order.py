from odoo import models, fields
from datetime import datetime
from collections import defaultdict
import json

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    def get_wing_dashboard_data(self, start_date, end_date=None):
        # Ensure end_date is provided
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')

        # Convert dates to datetime objects
        start_date = fields.Date.from_string(start_date)
        end_date = fields.Date.from_string(end_date)

        # Get accessible wings for the cur[('manager_id','=',user.id)]rent user
        accessible_wings = self.env['property.sales.wing'].search([('manager_id', '=', self.env.user.id)]).ids
        accessible_wings.append(False)  # Include leads with no wing (wing_id = False)

        # 1. Fetch filtered leads where wing_id is accessible
        leads = self.env['crm.lead'].search([
            ('create_date', '>=', start_date),
            ('create_date', '<=', end_date),
            ('wing_id', 'in', accessible_wings)
        ])

        # 2. Process lead events
        lead_events = []
        for lead in leads:
            stage_name = lead.stage_id.name
            event_type = None
            if stage_name:
                stage_name_en = json.loads(stage_name).get('en_US', '').lower()
                if 'expired' in stage_name_en:
                    event_type = 'Expired'
                elif 'won' in stage_name_en:
                    event_type = 'Won'
                elif 'reservation' in stage_name_en:
                    event_type = 'Reservation'
                elif 'follow' in stage_name_en:
                    event_type = 'Follow Up'
                elif 'prospect' in stage_name_en:
                    event_type = 'Prospect'

            if event_type:
                wing_name = lead.wing_id.name or 'No Wing'
                lead_events.append({
                    'lead_id': lead.id,
                    'sales_person': lead.user_id.partner_id.name or '',
                    'supervisor_name': lead.supervisor_id.name.partner_id.name if lead.supervisor_id and lead.supervisor_id.name else '',
                    'wing_manager_name': lead.wing_id.manager_id.partner_id.name if lead.wing_id and lead.wing_id.manager_id else '',
                    'wing_name': wing_name,
                    'event_type': event_type
                })

        # 3. Process activity events (mail tracking for 'Won')
        activity_events = []
        messages = self.env['mail.message'].search([
            ('model', '=', 'crm.lead'),
            ('res_id', 'in', leads.ids),
            ('subtype_id', '!=', 5)
        ])
        for message in messages:
            tracking_values = self.env['mail.tracking.value'].search([
                ('mail_message_id', '=', message.id),
                ('new_value_char', '=', 'Won'),
                ('old_value_char', '!=', 'sales')
            ])
            if tracking_values:
                lead = self.env['crm.lead'].browse(message.res_id)
                wing_name = lead.wing_id.name or 'No Wing'
                activity_events.append({
                    'lead_id': lead.id,
                    'sales_person': lead.user_id.partner_id.name or '',
                    'supervisor_name': lead.supervisor_id.name.partner_id.name if lead.supervisor_id and lead.supervisor_id.name else '',
                    'wing_manager_name': lead.wing_id.manager_id.partner_id.name if lead.wing_id and lead.wing_id.manager_id else '',
                    'wing_name': wing_name,
                    'event_type': 'Won'
                })

        # 4. Combine events
        unioned_events = lead_events + activity_events

        # 5. Count events
        event_counts = defaultdict(lambda: {
            'wing_name': None,
            'wing_manager_name': None,
            'supervisor_name': None,
            'sales_person': None,
            'prospect': 0,
            'follow_up': 0,
            'won': 0,
            'expired': 0
        })
        for event in unioned_events:
            key = (
                event['wing_name'],
                event['wing_manager_name'],
                event['supervisor_name'],
                event['sales_person']
            )
            event_counts[key]['wing_name'] = event['wing_name']
            event_counts[key]['wing_manager_name'] = event['wing_manager_name']
            event_counts[key]['supervisor_name'] = event['supervisor_name']
            event_counts[key]['sales_person'] = event['sales_person']
            if event['event_type'] == 'Prospect':
                event_counts[key]['prospect'] += 1
            elif event['event_type'] == 'Follow Up':
                event_counts[key]['follow_up'] += 1
            elif event['event_type'] == 'Won':
                event_counts[key]['won'] += 1
            elif event['event_type'] == 'Expired':
                event_counts[key]['expired'] += 1

        # 6. Fetch reservation summary for accessible wings
        reservations = self.env['property.reservation'].search([
            ('crm_lead_id.create_date', '>=', '2025-01-01'),
            ('crm_lead_id.wing_id', 'in', accessible_wings)
        ])
        reservation_counts = defaultdict(lambda: {
            'wing_name': None,
            'wing_manager_name': None,
            'supervisor_name': None,
            'sales_person': None,
            'reservation_count': 0,
            'sold_reservation_count': 0
        })
        for reservation in reservations:
            lead = reservation.crm_lead_id
            wing_name = lead.wing_id.name or 'No Wing'
            key = (
                wing_name,
                lead.wing_id.manager_id.partner_id.name if lead.wing_id and lead.wing_id.manager_id else '',
                lead.supervisor_id.name.partner_id.name if lead.supervisor_id and lead.supervisor_id.name else '',
                lead.user_id.partner_id.name or ''
            )
            reservation_counts[key]['wing_name'] = wing_name
            reservation_counts[key]['wing_manager_name'] = lead.wing_id.manager_id.partner_id.name if lead.wing_id and lead.wing_id.manager_id else ''
            reservation_counts[key]['supervisor_name'] = lead.supervisor_id.name.partner_id.name if lead.supervisor_id and lead.supervisor_id.name else ''
            reservation_counts[key]['sales_person'] = lead.user_id.partner_id.name or ''
            reservation_counts[key]['reservation_count'] += 1
            if reservation.status == 'sold':
                reservation_counts[key]['sold_reservation_count'] += 1

        # 7. Combine event and reservation counts
        result = []
        all_keys = set(event_counts.keys()) | set(reservation_counts.keys())
        for key in all_keys:
            wing_name, wing_manager_name, supervisor_name, sales_person = key
            data_flag = '🟡 Missing wing_name' if wing_name == 'No Wing' and wing_manager_name else '✅ OK'
            record = {
                'wing_name': wing_name,
                'wing_manager_name': wing_manager_name,
                'supervisor_name': supervisor_name,
                'sales_person': sales_person,
                'prospect': event_counts[key]['prospect'] if key in event_counts else 0,
                'follow_up': event_counts[key]['follow_up'] if key in event_counts else 0,
                'won': event_counts[key]['won'] if key in event_counts else 0,
                'expired': event_counts[key]['expired'] if key in event_counts else 0,
                'reservation_count': reservation_counts[key]['reservation_count'] if key in reservation_counts else 0,
                'sold_reservation_count': reservation_counts[key]['sold_reservation_count'] if key in reservation_counts else 0,
                'data_flag': data_flag
            }
            result.append(record)

        # 8. Sort results with None handling
        def safe_str(value):
            return value or ''  # Convert None to empty string for sorting

        result.sort(key=lambda x: (
            x['data_flag'] != '✅ OK',
            safe_str(x['wing_name']),
            safe_str(x['supervisor_name']),
            safe_str(x['sales_person'])
        ))
        for i in range (20):
            print(result)
        
        print(result)

        return result