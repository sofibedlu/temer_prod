from odoo import fields, models

class RebarSite(models.Model):
    _name = 'rebar.site'
    _description = 'Rebar Construction Site Definition'

    name = fields.Char(string='Site Name', required=True, index=True)
    # Refers to site.company from module ahadubit_property_base_custom
    site_company_id = fields.Many2one(
        comodel_name='site.company',
        string='Site Company',
        required=True,
        ondelete='restrict'
    )
    code = fields.Char(string='Site Code')
    active = fields.Boolean(default=True)