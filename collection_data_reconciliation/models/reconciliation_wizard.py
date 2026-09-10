from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_compare

class CollectionReconWizard(models.TransientModel):
    _name = 'collection.recon.wizard'
    _description = 'Collection Data Reconciliation Wizard'

    collection_id = fields.Many2one('collection.order', string="Collection Order", readonly=True)
    sale_id = fields.Many2one('property.sale', string="Property Sale", readonly=True)
    
    sync_direction = fields.Selection([
        ('collection_to_sale', 'Make Property Sale match Collection Order'),
        ('sale_to_collection', 'Make Collection Order match Property Sale')
    ], string="Synchronization Direction", default='collection_to_sale', required=True)

    update_hardcoded_names = fields.Boolean(string="Fix Typos in Collection Names", default=True)
    
    update_expected_amounts = fields.Boolean(
        string="Sync Expected / Total Amounts", 
        default=False,
    )
    update_paid_amounts = fields.Boolean(
        string="Sync Paid Amounts", 
        default=False
    )

    has_length_mismatch = fields.Boolean(string="Length Mismatch", readonly=True)
    preview_line_ids = fields.One2many('collection.recon.line', 'wizard_id', string="Preview Lines")

    @api.model
    def default_get(self, fields_list):
        res = super(CollectionReconWizard, self).default_get(fields_list)
        active_id = self.env.context.get('active_id')
        if not active_id:
            return res

        collection = self.env['collection.order'].browse(active_id)
        sale = collection.sale_id
        
        if not sale:
            raise UserError(_("No linked Property Sale found for this Collection Order."))

        res['collection_id'] = collection.id
        res['sale_id'] = sale.id

        sale_lines = sale.payment_installment_line_ids.sorted(key=lambda l: (l.sequence, l.id))
        coll_lines = collection.installment_ids.sorted(key=lambda l: (l.sequence, l.id))

        if len(sale_lines) != len(coll_lines):
            res['has_length_mismatch'] = True

        preview_vals = []
        for i, (s_line, c_line) in enumerate(zip(sale_lines, coll_lines), start=1):
            is_mismatch = s_line.payment_term_id.id != c_line.payment_term_line_id.id
            
            is_expected_mismatch = float_compare(s_line.expected_amount, c_line.amount_total, precision_digits=2) != 0
            is_paid_mismatch = float_compare(s_line.paid_amount, c_line.amount_paid, precision_digits=2) != 0

            preview_vals.append((0, 0, {
                'sequence_idx': i,
                'sale_line_id': s_line.id,
                'coll_line_id': c_line.id,
                
                'sale_term_db_id': s_line.payment_term_id.id,
                'sale_term_id': s_line.payment_term_id.id,
                'coll_term_db_id': c_line.payment_term_line_id.id,
                'coll_term_id': c_line.payment_term_line_id.id,
                'hardcoded_name': c_line.name,
                'is_mismatch': is_mismatch,

                'sale_expected': s_line.expected_amount,
                'coll_expected': c_line.amount_total,
                'is_expected_mismatch': is_expected_mismatch,
                
                'sale_paid': s_line.paid_amount,
                'coll_paid': c_line.amount_paid,
                'is_paid_mismatch': is_paid_mismatch,
                
                'sale_remaining': getattr(s_line, 'remaining', 0.0),
                'coll_remaining': c_line.amount_residual,
            }))

        res['preview_line_ids'] = preview_vals
        return res

    def action_confirm(self):
        mismatches_fixed = 0
        names_fixed = 0
        expected_fixed = 0
        paid_fixed = 0

        for line in self.preview_line_ids:
            # Fix Term IDs
            if line.is_mismatch:
                if self.sync_direction == 'collection_to_sale':
                    line.sale_line_id.write({'payment_term_id': line.coll_term_id.id})
                else:
                    line.coll_line_id.write({'payment_term_line_id': line.sale_term_id.id})
                mismatches_fixed += 1

            # Fix Hardcoded Names
            if self.update_hardcoded_names:
                target_term = line.coll_term_id if self.sync_direction == 'collection_to_sale' else line.sale_term_id
                correct_name = target_term.name if target_term else False
                if correct_name and line.coll_line_id.name != correct_name:
                    line.coll_line_id.write({'name': correct_name})
                    names_fixed += 1

            # Sync Expected/Total Amounts
            if self.update_expected_amounts and line.is_expected_mismatch:
                if self.sync_direction == 'collection_to_sale':
                    line.sale_line_id.write({'expected_amount': line.coll_expected})
                else:
                    line.coll_line_id.write({'amount_total': line.sale_expected})
                expected_fixed += 1

            # Sync Paid Amounts
            if self.update_paid_amounts and line.is_paid_mismatch:
                if self.sync_direction == 'collection_to_sale':
                    line.sale_line_id.write({'paid_amount': line.coll_paid})
                else:
                    line.coll_line_id.sudo().write({'amount_paid': line.sale_paid})
                paid_fixed += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Reconciliation Complete',
                'message': f"Synced {mismatches_fixed} Terms, {names_fixed} Names, {expected_fixed} Expected Amounts, and {paid_fixed} Paid Amounts.",
                'type': 'success',
                'sticky': True,
            }
        }


class CollectionReconLine(models.TransientModel):
    _name = 'collection.recon.line'
    _description = 'Collection Recon Preview Line'

    wizard_id = fields.Many2one('collection.recon.wizard', ondelete='cascade')
    sequence_idx = fields.Integer(string="#")
    
    sale_line_id = fields.Many2one('property.payment.line', string="Sale Line")
    coll_line_id = fields.Many2one('collection.installment', string="Collection Line")
    
    sale_term_db_id = fields.Integer(string="Sale Term ID")
    sale_term_id = fields.Many2one('property.payment.term.line', string="Sale Master Term")
    
    coll_term_db_id = fields.Integer(string="Coll Term ID")
    coll_term_id = fields.Many2one('property.payment.term.line', string="Coll Master Term")
    
    hardcoded_name = fields.Char(string="Coll Hardcoded Text")
    is_mismatch = fields.Boolean(string="Mismatch?")

    sale_expected = fields.Float(string="Sale Expected")
    coll_expected = fields.Float(string="Coll Expected (Total)")
    is_expected_mismatch = fields.Boolean(string="Expected Mismatch")

    sale_paid = fields.Float(string="Sale Paid")
    coll_paid = fields.Float(string="Coll Paid")
    is_paid_mismatch = fields.Boolean(string="Paid Mismatch")

    sale_remaining = fields.Float(string="Sale Remaining")
    coll_remaining = fields.Float(string="Coll Remaining")