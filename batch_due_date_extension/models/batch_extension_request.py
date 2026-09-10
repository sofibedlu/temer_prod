from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date
import logging

_logger = logging.getLogger(__name__)

try:
    from ethioqen.calendar_conversion import convert_gregorian_to_ethiopian, convert_ethiopian_to_gregorian
except ImportError:
    _logger.warning("The 'ethioqen' library is missing.")

class BatchExtensionRequest(models.Model):
    _name = 'batch.extension.request'
    _description = 'Batch Due Date Extension Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    reason = fields.Text(string='Reason for Extension', required=True, tracking=True)
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('checked', 'Checked'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='Status', default='draft', tracking=True)

    line_ids = fields.One2many('batch.extension.request.line', 'request_id', string='Installments')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('batch.extension.request') or _('New')
        return super().create(vals_list)

    def action_check(self):
        self.write({'state': 'checked'})

    def action_approve(self):
        for req in self:
            for line in req.line_ids:
                if line.installment_id and line.new_due_date:
                    line.installment_id.with_context(tracking_disable=False).write({
                        'due_date': line.new_due_date,
                        'extended_date': line.new_due_date
                    })
            req.write({'state': 'approved'})

    def action_reject(self):
        self.write({'state': 'rejected'})


class BatchExtensionRequestLine(models.Model):
    _name = 'batch.extension.request.line'
    _description = 'Batch Extension Request Line'

    request_id = fields.Many2one('batch.extension.request', ondelete='cascade')
    
    collection_id = fields.Many2one('collection.order', string='Collection Order', required=True)
    partner_id = fields.Many2one('res.partner', related='collection_id.partner_id', string='Customer')
    buyers_name = fields.Html(related='collection_id.buyers_name', string='Buyers Name', readonly=True)
    buyers_name_text = fields.Char(related='collection_id.buyers_name_text', string='Buyers Name (Text)', store=True)
    installment_id = fields.Many2one('collection.installment', string='Installment', required=True, domain="[('collection_id', '=', collection_id), ('state', '!=', 'paid')]")
    current_due_date = fields.Date(related='installment_id.due_date', string='Current Due Date', store=True)
    new_due_date = fields.Date(string='New Due Date (GC)', required=True)
    new_due_date_ethiopian = fields.Char(string='New Due Date (EC)', required=True, help="DD/MM/YYYY")

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