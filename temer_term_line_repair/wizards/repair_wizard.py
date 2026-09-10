from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class TermLineRepairWizard(models.TransientModel):
    _name = 'term.line.repair.wizard'
    _description = 'Wizard to Repair Null Payment Term Lines'

    total_count = fields.Integer(string="Total Records to Fix", readonly=True)
    line_ids = fields.One2many('term.line.repair.wizard.line', 'wizard_id', string="Lines to Repair")

    @api.model
    def default_get(self, fields_list):
        res = super(TermLineRepairWizard, self).default_get(fields_list)
        term_line_obj = self.env['property.payment.term.line']
        payment_line_obj = self.env['property.payment.line']

        # 1. Get all broken
        broken_term_lines = term_line_obj.search([('payment_term_id', '=', False)])
        broken_ids = broken_term_lines.ids
        
        if not broken_ids:
            return res

        # 2. Bulk fetch ALL payment lines linked to these broken IDs in ONE query
        all_linked_pl = payment_line_obj.search([('payment_term_id', 'in', broken_ids)])
        
        # 3. Group them in memory using a dictionary {term_line_id: [list_of_payment_lines]}
        pl_by_term = {}
        for pl in all_linked_pl:
            pl_by_term.setdefault(pl.payment_term_id.id, []).append(pl)

        lines_data = []
        for term_id in broken_ids:
            linked_lines = pl_by_term.get(term_id, [])
            if not linked_lines:
                continue

            sales = [line.sale_id for line in linked_lines if line.sale_id]
            # Use set() to get unique values quickly
            unique_sales = list(set(sales))
            target_terms = list(set([s.property_payment_term for s in unique_sales if s.property_payment_term]))
            
            sale_names = ", ".join([s.name for s in unique_sales])
            term_names = ", ".join([t.name for t in target_terms])

            if target_terms:
                lines_data.append((0, 0, {
                    'term_line_id': term_id,
                    'sale_details': sale_names or "No Sales",
                    'suggested_term_details': term_names or "Unknown",
                    'target_term_ids': ','.join(map(str, [t.id for t in target_terms])),
                    'is_conflict': len(target_terms) > 1,
                }))
        
        res['line_ids'] = lines_data
        res['total_count'] = len(lines_data)
        return res

    def action_repair_term_lines(self):
        fixed_count = 0
        duplicate_count = 0
        
        term_line_obj = self.env['property.payment.term.line']
        payment_line_obj = self.env['property.payment.line']

        broken_term_lines = term_line_obj.search([('payment_term_id', '=', False)])
        
        for term_line in broken_term_lines:
            linked_payment_lines = payment_line_obj.search([('payment_term_id', '=', term_line.id)])
            if not linked_payment_lines:
                continue

            sales = linked_payment_lines.mapped('sale_id')
            suggested_terms = sales.mapped('property_payment_term').filtered(lambda t: t)
            
            if not suggested_terms:
                continue

            real_term_line_id = term_line.id
            is_conflict = len(suggested_terms) > 1

            if not is_conflict:
                target_term_id = suggested_terms[0].id
                self.env.cr.execute("""
                    UPDATE property_payment_term_line
                    SET payment_term_id = %s, percentage = 0.0, amount = 0.0
                    WHERE id = %s
                """, (target_term_id, real_term_line_id))
                fixed_count += 1
                
            else:
                term_pl_map = {}
                for pl in linked_payment_lines:
                    sale_term_id = pl.sale_id.property_payment_term.id
                    if sale_term_id:
                        if sale_term_id not in term_pl_map:
                            term_pl_map[sale_term_id] = []
                        term_pl_map[sale_term_id].append(pl)
                
                is_first = True
                for t_id, p_lines in term_pl_map.items():
                    if is_first:
                        # fix the original object in place
                        self.env.cr.execute("""
                            UPDATE property_payment_term_line
                            SET payment_term_id = %s, percentage = 0.0, amount = 0.0
                            WHERE id = %s
                        """, (t_id, real_term_line_id))
                        fixed_count += 1
                        is_first = False
                    else:
                        # duplicate the row
                        new_term_line = term_line.sudo().copy({
                            'payment_term_id': t_id,
                            'percentage': 0.0,
                            'amount': 0.0
                        })
                        duplicate_count += 1
                        
                        # direct SQL Update redirecting the schedule lines
                        pl_ids = tuple(pl.id for pl in p_lines)
                        if pl_ids:
                            self.env.cr.execute("""
                                UPDATE property_payment_line
                                SET payment_term_id = %s
                                WHERE id IN %s
                            """, (new_term_line.id, pl_ids))
        
        # Commit the transaction
        #self.env.cr.commit()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Data Repair Complete (SQL Mode)',
                'message': f'Successfully hard-coded {fixed_count} updates and {duplicate_count} copies to the database.',
                'sticky': False,
                'type': 'success',
            }
        }


class TermLineRepairWizardLine(models.TransientModel):
    _name = 'term.line.repair.wizard.line'
    _description = 'Wizard Line Preview'

    wizard_id = fields.Many2one('term.line.repair.wizard')
    term_line_id = fields.Many2one('property.payment.term.line', string="Broken Term Line", readonly=True)
    sale_details = fields.Char(string="Associated Sales", readonly=True)
    suggested_term_details = fields.Char(string="Suggested Parent Terms", readonly=True)
    target_term_ids = fields.Char()
    is_conflict = fields.Boolean("Conflict?", readonly=True)