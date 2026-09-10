from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class PropertyPaymentTerm(models.Model):
    _inherit = 'property.payment.term'

    def action_merge_duplicate_lines(self):
        for term in self:
            merge_count = 0
            delete_count = 0
            
            # 1. Group lines by their name
            lines_by_name = {}
            for line in term.payment_line:
                name_key = (line.name or '').strip().lower()
                if not name_key:
                    continue
                lines_by_name.setdefault(name_key, []).append(line)

            for name_key, lines in lines_by_name.items():
                if len(lines) > 1:
                    # Make the line where percentage or amount is NOT zero to be first.
                    # If all are zero or all have values, fallback to the lowest ID.
                    sorted_lines = sorted(lines, key=lambda l: (
                        (l.percentage == 0 and l.amount == 0),
                        l.id
                    ))
                    
                    kept_line = sorted_lines[0]
                    duplicate_lines = sorted_lines[1:]
                    duplicate_ids = tuple(l.id for l in duplicate_lines)
                    
                    if duplicate_ids:
                        # 3. Find all payment schedule lines pointing to duplicates
                        payment_lines = self.env['property.payment.line'].search([
                            ('payment_term_id', 'in', duplicate_ids)
                        ])
                        
                        if payment_lines:
                            payment_line_ids = tuple(payment_lines.ids)
                            self.env.cr.execute("""
                                UPDATE property_payment_line 
                                SET payment_term_id = %s 
                                WHERE id IN %s
                            """, (kept_line.id, payment_line_ids))
                            merge_count += len(payment_lines)

                        # 4. Delete the duplicate term lines
                        self.env.cr.execute("""
                            DELETE FROM property_payment_term_line 
                            WHERE id IN %s
                        """, (duplicate_ids,))
                        delete_count += len(duplicate_ids)
            

            if delete_count > 0:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': f'Cleaned {term.name}',
                        'message': f'Kept original values, merged {merge_count} schedules and removed {delete_count} duplicates.',
                        'sticky': False,
                        'type': 'success',
                    }
                }
        return {'type': 'ir.actions.act_window_close'}