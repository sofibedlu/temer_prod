# -*- coding: utf-8 -*-
from datetime import datetime, time

from odoo.osv import expression


ACTIVITY_TYPE_MAP = {
    'call': 'Call',
    'office_visit': 'Office Visit',
    'site_visit': 'Site Visit',
    'sms': 'SMS',
    'email': 'Email',
}


def parse_date_range(fields, date_from=None, date_to=None):
    date_from_obj = fields.Date.from_string(date_from) if date_from else None
    date_to_obj = fields.Date.from_string(date_to) if date_to else None
    return date_from_obj, date_to_obj


def create_date_domain(date_from_obj=None, date_to_obj=None):
    domain = []
    if date_from_obj:
        domain.append(('create_date', '>=', datetime.combine(date_from_obj, time.min)))
    if date_to_obj:
        domain.append(('create_date', '<=', datetime.combine(date_to_obj, time.max)))
    return domain


def sum_grouped_metrics(grouped_data):
    totals = {
        'prospect': 0,
        'follow_up': {},
        'reservation': 0,
        'sold': 0,
    }
    for group in grouped_data:
        for salesperson in group.get('salespersons', []):
            totals['prospect'] += salesperson.get('prospect', 0)
            totals['reservation'] += salesperson.get('reservation', 0)
            totals['sold'] += salesperson.get('sold', 0)
            follow_up = salesperson.get('follow_up', {})
            if isinstance(follow_up, dict):
                for activity_type, count in follow_up.items():
                    totals['follow_up'][activity_type] = (
                        totals['follow_up'].get(activity_type, 0) + count
                    )
    return totals


class ActivityReportMetrics:
    """Shared metrics loader for supervisor / team activity sales reports."""

    def __init__(self, env, date_from_obj=None, date_to_obj=None):
        self.env = env
        self.date_from_obj = date_from_obj
        self.date_to_obj = date_to_obj
        self.create_date_domain = create_date_domain(date_from_obj, date_to_obj)

    @staticmethod
    def empty():
        return {
            'prospect': 0,
            'follow_up': {},
            'reservation': 0,
            'sold': 0,
        }

    def for_users(self, user_ids):
        user_ids = list({user_id for user_id in user_ids if user_id})
        metrics = {user_id: self.empty() for user_id in user_ids}
        if not user_ids:
            return metrics

        self._load_prospects(metrics, user_ids)
        self._load_followups(metrics, user_ids)
        self._load_reservations(metrics, user_ids)
        self._load_sold_reservations(metrics, user_ids)
        return metrics

    def metric_for(self, metrics, user_id):
        return metrics.get(user_id) or self.empty()

    def sold_reservation_domain(self, user_ids):
        """Sold reservations for drill-down / listing.

        Includes:
        - status=sold and salesperson_ids in users
        - status=sold on a merged parent where a user's salesperson_id
          is set on child.property
        """
        if isinstance(user_ids, int):
            user_ids = [user_ids]
        domain = [('status', '=', 'sold')]
        domain.extend(self.create_date_domain)

        parts = [('salesperson_ids', 'in', user_ids)]
        if 'child.property' in self.env and 'salesperson_id' in self.env['child.property']._fields:
            children = self.env['child.property'].sudo().search([
                ('salesperson_id', 'in', user_ids),
            ])
            parent_ids = children.mapped('parent_property_id').ids
            if parent_ids:
                parts = expression.OR([
                    parts,
                    [('property_id', 'in', parent_ids)],
                ])
        return expression.AND([domain, parts])

    def _load_prospects(self, metrics, user_ids):
        Lead = self.env['temer.lead'].sudo()
        groups = Lead.read_group(
            [('user_id', 'in', user_ids)] + self.create_date_domain,
            ['user_id'],
            ['user_id'],
        )
        for group in groups:
            user = group.get('user_id')
            if user:
                metrics[user[0]]['prospect'] = group['user_id_count']

    def _load_followups(self, metrics, user_ids):
        if 'temer.lead.followup' not in self.env:
            return

        Lead = self.env['temer.lead'].sudo()
        leads = Lead.search_read(
            [('user_id', 'in', user_ids)],
            ['user_id'],
        )
        lead_user = {
            lead['id']: lead['user_id'][0]
            for lead in leads
            if lead.get('user_id')
        }
        if not lead_user:
            return

        followup_domain = [('lead_id', 'in', list(lead_user))]
        if self.date_from_obj:
            followup_domain.append(('activity_date', '>=', self.date_from_obj))
        if self.date_to_obj:
            followup_domain.append(('activity_date', '<=', datetime.combine(self.date_to_obj, time.max)))

        groups = self.env['temer.lead.followup'].sudo().read_group(
            followup_domain,
            ['lead_id', 'activity_type'],
            ['lead_id', 'activity_type'],
            lazy=False,
        )
        for group in groups:
            lead = group.get('lead_id')
            if not lead:
                continue
            user_id = lead_user.get(lead[0])
            if not user_id:
                continue
            activity_type = ACTIVITY_TYPE_MAP.get(
                group.get('activity_type'),
                group.get('activity_type') or 'Other',
            )
            follow_up = metrics[user_id]['follow_up']
            follow_up[activity_type] = follow_up.get(activity_type, 0) + group['__count']

    def _load_reservations(self, metrics, user_ids):
        Lead = self.env['temer.lead'].sudo()
        reservation_domain = [('user_id', 'in', user_ids), ('state', '=', 'reservation')]

        if 'temer.lead.stage.history' in self.env:
            history_domain = [('to_stage', '=', 'reservation')]
            if self.date_from_obj:
                history_domain.append(('transition_date', '>=', self.date_from_obj))
            if self.date_to_obj:
                history_domain.append(('transition_date', '<=', datetime.combine(self.date_to_obj, time.max)))

            reservation_history = self.env['temer.lead.stage.history'].sudo().search(history_domain)
            reservation_lead_ids = list(set(reservation_history.mapped('lead_id.id')))
            if not reservation_lead_ids:
                return
            reservation_domain.append(('id', 'in', reservation_lead_ids))
        else:
            reservation_domain.extend(self.create_date_domain)

        groups = Lead.read_group(reservation_domain, ['user_id'], ['user_id'])
        for group in groups:
            user = group.get('user_id')
            if user:
                metrics[user[0]]['reservation'] = group['user_id_count']

    def _load_sold_reservations(self, metrics, user_ids):
        """Sold credit from property.reservation / child.property.salesperson_id.

        Normal property:
          +1 to reservation.salesperson_ids

        Merged property (has child.property):
          +1 per child to child.salesperson_id
          (fallback: sold reservation salesperson if child still empty)

        On sold, merge fills empty children with the sold reservation salesperson,
        so both units count for that person until child.salesperson_id is changed.
        """
        if 'property.reservation' not in self.env:
            return

        Reservation = self.env['property.reservation'].sudo()
        sold_reservations = Reservation.search(self.sold_reservation_domain(user_ids))
        if not sold_reservations:
            return

        children_by_parent = {}
        if 'child.property' in self.env:
            children = self.env['child.property'].sudo().search([
                ('parent_property_id', 'in', sold_reservations.mapped('property_id').ids),
            ])
            for child in children:
                children_by_parent.setdefault(
                    child.parent_property_id.id,
                    self.env['child.property'],
                )
                children_by_parent[child.parent_property_id.id] |= child

        processed_merged_parents = set()

        for reservation in sold_reservations:
            children = children_by_parent.get(reservation.property_id.id)
            if not children:
                salesperson = reservation.salesperson_ids
                if salesperson and salesperson.id in metrics:
                    metrics[salesperson.id]['sold'] += 1
                continue

            parent_id = reservation.property_id.id
            if parent_id in processed_merged_parents:
                continue
            processed_merged_parents.add(parent_id)

            for child in children:
                salesperson = child.salesperson_id or reservation.salesperson_ids
                if salesperson and salesperson.id in metrics:
                    metrics[salesperson.id]['sold'] += 1
