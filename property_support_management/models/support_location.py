from odoo import models, fields

class SupportLocation(models.Model):
    _name = 'support.location'
    _description = 'Union Location (Site/Office)'
    _order = 'type, name'

    name = fields.Char(string='Location Name', required=True)
    type = fields.Selection([
        ('site', 'Site'),
        ('office', 'Office')
    ], string='Type', required=True)

    site_id = fields.Many2one('property.site', string='Site Reference')
    office_id = fields.Many2one('support.office.location', string='Office Reference')

    def name_get(self):
        result = []
        for rec in self:
            label = '[Site]' if rec.type == 'site' else '[Office]'
            result.append((rec.id, f"{label} {rec.name}"))
        return result

    def _auto_init(self):
        res = super()._auto_init()
        # Sync existing property.site records into support.location on install/upgrade
        cr = self._cr
        cr.execute("""
            INSERT INTO support_location (name, type, site_id, create_date, write_date, create_uid, write_uid)
            SELECT s.name, 'site', s.id, NOW(), NOW(), 1, 1
            FROM property_site s
            WHERE NOT EXISTS (
                SELECT 1 FROM support_location sl WHERE sl.site_id = s.id
            )
        """)
        return res
