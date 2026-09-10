# -*- coding: utf-8 -*-
##############################################################################
#    Property Lock / Unlock - Temer CRM integration
##############################################################################

from odoo import models


class TemerLead(models.Model):
    _inherit = 'temer.lead'

    def action_reserve(self):
        """Override to exclude locked properties from reservation property domain."""
        action = super().action_reserve()
        if action and action.get('context'):
            ctx = action['context']
            domain = ctx.get('default_property_id_domain', '[]')
            if isinstance(domain, str) and "is_locked" not in domain:
                domain = domain.rstrip(']')
                if not domain.endswith(','):
                    domain += ','
                domain += "('is_locked', '=', False)]"
                ctx = dict(ctx, default_property_id_domain=domain)
                action['context'] = ctx
        return action
