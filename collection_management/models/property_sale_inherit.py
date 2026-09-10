from odoo import models, fields, api
from dateutil.relativedelta import relativedelta

class PropertySale(models.Model):
    _inherit = 'property.sale'

    collection_order_id = fields.Many2one('collection.order', string='Collection Order', readonly=True, copy=False)

    def action_confirm(self):
        """
        Collection Order creation moved to the 'Approve' stage.
        keep super call to maintain other confirm logic.
        """
        return super(PropertySale, self).action_confirm()

    def _create_collection_order(self):
        """
        Logic to generate the Collection Order and Installments.
        """
        self.ensure_one()
        CollectionOrder = self.env['collection.order']
        CollectionInstallment = self.env['collection.installment']
        collection_vals = {
            'sale_id': self.id,
            'state': 'active',
        }
        collection = CollectionOrder.create(collection_vals)
        self.collection_order_id = collection.id

        for line in self.payment_installment_line_ids:
            
            template_line = line.payment_term_id 
            amount = 0.0
            if hasattr(line, 'expected_amount') and line.expected_amount > 0:
                amount = line.expected_amount
            elif line.expected > 0:
                price = self.new_sale_price if self.new_sale_price else self.sale_price
                amount = price * (line.expected / 100.0)

            due_date = False
            is_progress = False
            is_explicit_time_based = False
            
            # check for the schedule type
            if hasattr(self, 'payment_schedule_type') and self.payment_schedule_type == 'time':
                is_explicit_time_based = True
            
            if is_explicit_time_based and hasattr(line, 'due_date') and line.due_date:
                due_date = line.due_date
                is_progress = False
            elif getattr(self, 'payment_schedule_type', False) == 'progress':
                due_date = False
                is_progress = True
            else:
                # fallback to old template logic (Standard Payment Terms)
                if template_line:
                    if hasattr(template_line, 'cash_collection') and template_line.cash_collection == 'by_site':
                        is_progress = True
                        due_date = False
                    else:
                        days = getattr(template_line, 'due_date_term', 0)
                        if days > 0:
                            contract_date = self.order_date or fields.Date.today()
                            due_date = contract_date + relativedelta(days=days)
                        else:
                            due_date = False
            # Create the Collection Installment
            installment_vals = {
                'collection_id': collection.id,
                'name': template_line.name or 'Installment', 
                'amount_total': amount,
                'due_date': due_date,
                'is_progress_based': is_progress,
                'payment_term_line_id': template_line.id,
                'sequence': line.sequence,

            }
            installment = CollectionInstallment.create(installment_vals)

            if line.paid_amount > 0:
                self.env['collection.installment.payment'].create({
                    'installment_id': installment.id,
                    'amount': line.paid_amount,
                    'payment_date': fields.Date.today(), 
                    'status': 'paid', 
                    'reference': 'Transferred from Property Sale',
                    'journal_type': 'bank', 
                })

        return collection