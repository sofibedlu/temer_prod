from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

try:
    from ethiopian_date import EthiopianDateConverter
except ImportError:
    pass

class PropertyPaymentLine(models.Model):
    _inherit = 'property.payment.line'

    ethiopian_due_date = fields.Char(
        string="Eth Due Date", 
        compute="_compute_ethiopian_due_date",
        help="Numeric Ethiopian Date (DD/MM/YYYY)"
    )

    @api.depends('due_date')
    def _compute_ethiopian_due_date(self):
        for rec in self:
            if rec.due_date:
                config = self.env['property.ethiopian.calendar.config']
                eth_year, eth_month, eth_day = config.safe_gregorian_to_ethiopian(rec.due_date)
                
                if eth_year:
                    # Formats as 05/13/2016
                    rec.ethiopian_due_date = f"{eth_day:02d}/{eth_month:02d}/{eth_year}"
                else:
                    rec.ethiopian_due_date = False
            else:
                rec.ethiopian_due_date = False

    # @api.onchange('due_date')
    # def _onchange_due_date_ethiopian_naming(self):
    #     for rec in self:
    #         if rec.sale_id and getattr(rec.sale_id, 'payment_schedule_type', False) == 'time' and rec.due_date:
    #             config = self.env['property.ethiopian.calendar.config'].search([], limit=1)
    #             if not config:
    #                 config = self.env['property.ethiopian.calendar.config'].create({})

    #             amharic_name = config.convert_date_to_amharic(rec.due_date)
    #             term_line = self.env['property.payment.term.line'].search([('name', '=', amharic_name)], limit=1)
                
    #             if not term_line:
    #                 parent_term_id = rec.sale_id.property_payment_term.id if rec.sale_id.property_payment_term else False
    #                 term_line = self.env['property.payment.term.line'].create({
    #                     'name': amharic_name,
    #                     #'payment_term_id': parent_term_id
    #                 })
                
    #             rec.payment_term_id = term_line.id