# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID


def post_init_hook(env):
    """
    Create the ir.rule programmatically so we can use a proper Python
    domain_force expression that references env at runtime (not parse time).
    """
    model = env['ir.model'].search([('model', '=', 'property.reservation')], limit=1)
    group = env.ref('special_reservation.group_supervisor', raise_if_not_found=False)
    if not model or not group:
        return

    rule_xmlid = 'special_reservation_supervisor_filter.rule_supervisor_sees_own_salespersons_reservations'

    # Remove existing rule if re-installing
    existing = env.ref(rule_xmlid, raise_if_not_found=False)
    if existing:
        existing.unlink()

    # domain_force: at runtime, 'user' is the logged-in user.
    # We find the property.sales.supervisor record(s) where name == user,
    # then get all mapped salesperson user ids, and filter reservations by that.
    domain = (
        "[('salesperson_ids', 'in', "
        "env['property.salesperson.mapping'].search("
        "[('supervisor_id.name', '=', user.id)]).mapped('user_id').ids)]"
    )

    rule = env['ir.rule'].create({
        'name': 'Special Reservation: Supervisor sees only own salespersons',
        'model_id': model.id,
        'domain_force': domain,
        'perm_read': True,
        'perm_write': True,
        'perm_create': False,
        'perm_unlink': False,
        'groups': [(4, group.id)],
    })

    # Bind the xmlid so it can be referenced/uninstalled cleanly
    env['ir.model.data'].create({
        'name': 'rule_supervisor_sees_own_salespersons_reservations',
        'module': 'special_reservation_supervisor_filter',
        'model': 'ir.rule',
        'res_id': rule.id,
        'noupdate': True,
    })
