# -*- coding: utf-8 -*-
from odoo import models, api


class PropertyReservation(models.Model):
    _inherit = 'property.reservation'

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None):
        """
        Only restrict to own salespersons when the supervisor is searching
        specifically for special reservation submitted requests
        (i.e. domain contains state = submitted or state = supervisor/ceo).
        Normal reservation views are NOT affected.
        """
        supervisor_group = self.env.ref(
            'special_reservation.group_supervisor',
            raise_if_not_found=False,
        )
        # Skip filter for superuser (uid=1) or users with Settings/Technical access
        is_admin = (
            self.env.user._is_superuser()
            or self.env.user.has_group('base.group_system')
        )
        if not is_admin and supervisor_group and self.env.user in supervisor_group.users:
            # Only apply filter if this is a special-approval-workflow query
            # (domain contains a state filter for the approval flow states)
            approval_states = {'submitted', 'supervisor', 'ceo', 'approved', 'rejected'}
            domain_list = list(domain)
            is_special_query = any(
                isinstance(leaf, (list, tuple))
                and len(leaf) == 3
                and leaf[0] == 'state'
                and (leaf[2] in approval_states or (isinstance(leaf[2], (list, tuple)) and set(leaf[2]) & approval_states))
                for leaf in domain_list
            )
            if is_special_query:
                mappings = self.env['property.salesperson.mapping'].search(
                    [('supervisor_id.name', '=', self.env.uid)]
                )
                salesperson_ids = mappings.mapped('user_id').ids
                domain_list += [('salesperson_ids', 'in', salesperson_ids)]
                return super()._search(domain_list, offset=offset, limit=limit, order=order)

        return super()._search(domain, offset=offset, limit=limit, order=order)
