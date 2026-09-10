from . import models


def post_init_hook(env):
    """After this module upgrades, mark temer_assigned_sales for upgrade too
    so its CSV can reference the new groups we just created."""
    assigned = env['ir.module.module'].search([
        ('name', '=', 'temer_assigned_sales'),
        ('state', '=', 'installed'),
    ], limit=1)
    if assigned:
        assigned.write({'state': 'to upgrade'})
