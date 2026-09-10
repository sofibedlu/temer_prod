from odoo import models, fields

class PropertyOrgAssignment(models.Model):
    _name = 'property.org.assignment'
    _description = 'User Branch Assignment'
    _rec_name = 'user_id'

    user_id = fields.Many2one('res.users', string="User", required=True, ondelete='cascade')
    
    org_unit_ids = fields.Many2many(
        'property.org.unit', 
        'property_org_assignment_unit_rel',
        'assignment_id',                    
        'org_unit_id',                      
        string="Assigned Branches", 
        required=True
    )

    _sql_constraints = [
        ('unique_user', 'unique(user_id)', 'This user already has a branch assignment record!')
    ]