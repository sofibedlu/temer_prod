from odoo import models, fields, api

class PropertyLegacySaleLine(models.Model):
    _inherit = 'property.legacy.sale.line'

    due_date = fields.Date(string="Due Date", default=fields.Date.today)

    @api.onchange('paid_amount', 'amount')
    def _onchange_paid_status_clear_date(self):
        """Clear due date if the line is fully paid"""
        for rec in self:
            if rec.amount > 0 and rec.paid_amount >= rec.amount:
                 rec.due_date = False

class PropertyLegacySale(models.Model):
    _inherit = 'property.legacy.sale'

    payment_schedule_type = fields.Selection(
        [('progress', 'Progress Based'), ('time', 'Time Based')],
        string="Payment Schedule Type",
        default='progress',
        required=True
    )

    def action_open_generator(self):
        """Open the wizard to generate lines"""
        return {
            'name': 'Generate Payment Schedule',
            'type': 'ir.actions.act_window',
            'res_model': 'property.legacy.schedule.generator',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_legacy_sale_id': self.id}
        }
    
    def action_approve(self):
        """On approve, sync due_date from legacy lines to created sale's payment lines"""
        res = super().action_approve()

        for legacy in self:
            sale = legacy.created_sale_id
            if not sale:
                continue

            if legacy.payment_schedule_type:
                sale.sudo().write({'payment_schedule_type': legacy.payment_schedule_type})

            payment_lines = legacy.env['property.payment.line'].search(
                [('sale_id', '=', sale.id), ('legacy_created', '=', True)],
                order='id asc'
            )
            legacy_lines = legacy.installment_ids.sorted(lambda l: l.id)
            for i, pay_line in enumerate(payment_lines):
                if i < len(legacy_lines):
                    pay_line.sudo().write({'due_date': legacy_lines[i].due_date})

            collection = sale.collection_order_id
            if collection:
                for pay_line in payment_lines:
                    if not pay_line.due_date or not pay_line.payment_term_id:
                        continue
                    inst = collection.installment_ids.filtered(
                        lambda x: x.payment_term_line_id and x.payment_term_line_id.id == pay_line.payment_term_id.id
                    )
                    if inst:
                        inst.sudo().write({'due_date': pay_line.due_date})

        return res