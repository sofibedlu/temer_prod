from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date
import logging

_logger = logging.getLogger(__name__)

try:
    from ethioqen.calendar_conversion import convert_gregorian_to_ethiopian, convert_ethiopian_to_gregorian
except ImportError:
    _logger.warning("The 'ethioqen' library is missing.")

class BatchExtensionWizard(models.TransientModel):
    _name = 'batch.extension.wizard'
    _description = 'Batch Extension Wizard'

    reason = fields.Text(string='Reason', required=True)
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments') 
    line_ids = fields.One2many('batch.extension.wizard.line', 'wizard_id', string='Lines')

    def action_create_request(self):
        if not self.line_ids:
            raise UserError(_("Please add at least one installment line."))

        request_vals = {
            'reason': self.reason,
            'attachment_ids': [(6, 0, self.attachment_ids.ids)],
            'line_ids': [(0, 0, {
                'collection_id': line.collection_id.id,
                'installment_id': line.installment_id.id,
                'new_due_date': line.new_due_date,
                'new_due_date_ethiopian': line.new_due_date_ethiopian,
            }) for line in self.line_ids]
        }
        
        new_request = self.env['batch.extension.request'].sudo().create(request_vals)
        
        if self.attachment_ids:
            self.attachment_ids.sudo().write({
                'res_model': 'batch.extension.request',
                'res_id': new_request.id
            })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Request Submitted'),
                'message': _('Batch Extension Request %s has been submitted successfully for checking.') % new_request.name,
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

class BatchExtensionWizardLine(models.TransientModel):
    _name = 'batch.extension.wizard.line'
    _description = 'Batch Extension Wizard Line'
    
    wizard_id = fields.Many2one('batch.extension.wizard')   
    collection_id = fields.Many2one('collection.order', string='Collection Order', required=True)
    partner_id = fields.Many2one('res.partner', related='collection_id.partner_id', string='Customer')
    buyers_name = fields.Html(related='collection_id.buyers_name', string='Buyers Name', readonly=True)
    buyers_name_text = fields.Char(related='collection_id.buyers_name_text', string='Buyers Name (Text)')
    installment_id = fields.Many2one('collection.installment', string='Installment', required=True, domain="[('collection_id', '=', collection_id), ('state', '!=', 'paid')]")
    current_due_date = fields.Date(related='installment_id.due_date', string='Current Due Date')
    new_due_date = fields.Date(string='New Due Date (GC)', required=True)
    new_due_date_ethiopian = fields.Char(string='New Due Date (EC)', required=True, help="Format: DD/MM/YYYY")

    @api.onchange('new_due_date')
    def _onchange_gregorian_date(self):
        for rec in self:
            if rec.new_due_date:
                try:
                    y, m, d = convert_gregorian_to_ethiopian(rec.new_due_date.year, rec.new_due_date.month, rec.new_due_date.day)
                    eth_str = f"{d:02d}/{m:02d}/{y}"
                    if rec.new_due_date_ethiopian != eth_str:
                        rec.new_due_date_ethiopian = eth_str
                except Exception:
                    pass

    @api.onchange('new_due_date_ethiopian')
    def _onchange_ethiopian_date(self):
        for rec in self:
            if rec.new_due_date_ethiopian:
                parts = rec.new_due_date_ethiopian.strip().split('/')
                if len(parts) == 3:
                    try:
                        d, m, y = int(parts[0]), int(parts[1]), int(parts[2])
                        gy, gm, gd = convert_ethiopian_to_gregorian(y, m, d)
                        greg_date = date(gy, gm, gd)
                        if rec.new_due_date != greg_date:
                            rec.new_due_date = greg_date
                    except Exception:
                        pass