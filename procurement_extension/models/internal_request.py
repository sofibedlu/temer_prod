from odoo import models, fields, api, _

class InternalRequest(models.Model):
    _inherit = 'internal.request'

    responsible_department_id = fields.Many2one('hr.department', required=False)

    def action_approve(self):
        for record in self:
            record.state = 'approved'
            record.approved_by_id = self.env.user.id # This is the current user approving it
            
            # Group lines by Responsible Department
            grouped_lines = {}
            for line in record.line_ids:
                dept_id = line.responsible_department_id.id
                if not dept_id:
                    # Fallback
                    dept_id = record.department_id.id 
                
                if dept_id not in grouped_lines:
                    grouped_lines[dept_id] = []
                grouped_lines[dept_id].append(line)
            
            # Create a separate Department Request for each department group
            for dept_id, lines in grouped_lines.items():
                dept_vals = {
                    'origin': record.name,
                    'priority': record.priority,
                    'expected_date': record.expected_date,
                    'department_id': dept_id,
                    'state': 'requested',              
                    'requestor_id': self.env.user.id,
                    
                    'line_ids': [(0, 0, {
                        'product_id': l.product_id.id,
                        'quantity': l.quantity,
                        'product_uom_id': l.product_uom_id.id,
                        'purpose': l.purpose,
                    }) for l in lines]
                }
                self.env['department.request'].sudo().create(dept_vals)


class InternalRequestLine(models.Model):
    _inherit = 'internal.request.line'

    responsible_department_id = fields.Many2one(
        'hr.department', 
        string='Responsible Dept.', 
        required=True,
        help="The department responsible for reviewing and specifying this product (e.g. IT for Laptops)."
    )