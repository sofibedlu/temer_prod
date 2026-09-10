from odoo import api, SUPERUSER_ID

def init_locations(cr):
    env = api.Environment(cr, SUPERUSER_ID, {})
    sites = env['property.site'].search([])
    for site in sites:
        existing = env['support.location'].search([('site_id', '=', site.id)], limit=1)
        if not existing:
            env['support.location'].create({
                'name': site.name,
                'type': 'site',
                'site_id': site.id,
            })
    
    offices = env['support.office.location'].search([])
    for office in offices:
        existing = env['support.location'].search([('office_id', '=', office.id)], limit=1)
        if not existing:
            env['support.location'].create({
                'name': office.name,
                'type': 'office',
                'office_id': office.id,
            })
