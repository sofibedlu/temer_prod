from odoo import models, fields

class PropertyOrgUnit(models.Model):
    _name = 'property.org.unit'
    _description = 'Organizational Unit (Branch)'
    _order = 'name'

    name = fields.Char(string="Branch / Unit Name", required=True)
    code = fields.Char(string="Code")
    active = fields.Boolean(default=True)

    assignment_ids = fields.Many2many(
        'property.org.assignment',
        'property_org_assignment_unit_rel',
        'org_unit_id',                      
        'assignment_id',                    
        string="Assignments"
    )