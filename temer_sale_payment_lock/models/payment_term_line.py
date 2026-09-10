from odoo import models, fields

class PropertyPaymentTermLine(models.Model):
    _inherit = 'property.payment.term.line'

    # "soft delete" lines that have been historically used
    active = fields.Boolean(default=True, string="Active")

    def unlink(self):
        lines_to_delete = self.env['property.payment.term.line']
        for line in self:
            is_used = self.env['property.payment.line'].search_count([
                ('payment_term_id', '=', line.id)
            ]) > 0
            
            if is_used:
                line.write({
                    'payment_term_id': False,
                    'active': False
                })
            else:
                lines_to_delete += line

        if lines_to_delete:
            return super(PropertyPaymentTermLine, lines_to_delete).unlink()

        return True