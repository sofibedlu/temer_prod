from odoo import api, fields, models
from markupsafe import Markup


def _date_to_string(value):
    return fields.Date.to_string(fields.Date.to_date(value)) if value else ''


class CollectionPaymentExtensionRequestLine(models.Model):
    _name = 'collection.payment.extension.request.line'
    _description = 'Payment Extension Request Line'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    request_id = fields.Many2one(
        'collection.payment.extension.request',
        string='Extension Request',
        required=True,
        readonly=True,
        ondelete='cascade',
    )
    collection_id = fields.Many2one(
        'collection.order',
        string='Collection',
        related='request_id.collection_id',
        store=True,
        readonly=True,
    )
    installment_id = fields.Many2one(
        'collection.installment',
        string='Installment',
        required=True,
        readonly=True,
        ondelete='cascade',
    )
    current_date = fields.Date(string='Current Due Date', readonly=True)
    new_date = fields.Date(string='Requested Date', required=True)
    reason = fields.Text(string='Reason', readonly=True)
    state = fields.Selection(related='request_id.state', store=True, readonly=True)

    def write(self, vals):
        old_dates = {}
        if 'new_date' in vals:
            old_dates = {
                line.id: line.new_date
                for line in self
                if line.request_id.state == 'pending'
            }

        result = super().write(vals)

        if 'new_date' in vals:
            for line in self:
                old_date = old_dates.get(line.id)
                if line.id not in old_dates or _date_to_string(old_date) == _date_to_string(line.new_date):
                    continue

                body = Markup(
                    "New Extended Date <b>Changed</b> for <b>%s</b><br/>Old Date: %s<br/>New Date: %s"
                ) % (
                    line.installment_id.display_name,
                    _date_to_string(old_date),
                    _date_to_string(line.new_date),
                )
                line.request_id.message_post(body=body)

        return result


class CollectionPaymentExtensionRequest(models.Model):
    _inherit = 'collection.payment.extension.request'

    line_ids = fields.One2many(
        'collection.payment.extension.request.line',
        'request_id',
        string='Installment Lines',
    )
    new_date = fields.Date(string='Requested Date', required=True)
    installment_count = fields.Integer(compute='_compute_multi_extension_info')
    is_multi_extension = fields.Boolean(compute='_compute_multi_extension_info')
    installment_summary = fields.Text(
        string='Installments',
        compute='_compute_tree_summaries',
    )
    current_date_summary = fields.Text(
        string='Current Due Date',
        compute='_compute_tree_summaries',
    )
    new_date_summary = fields.Text(
        string='Requested Date',
        compute='_compute_tree_summaries',
    )

    @api.depends('line_ids')
    def _compute_multi_extension_info(self):
        for rec in self:
            rec.installment_count = len(rec.line_ids) or 1
            rec.is_multi_extension = bool(rec.line_ids)

    @api.depends(
        'line_ids.installment_id',
        'line_ids.current_date',
        'line_ids.new_date',
        'installment_id',
        'current_date',
        'new_date',
    )
    def _compute_tree_summaries(self):
        for rec in self:
            if rec.line_ids:
                rec.installment_summary = "\n".join(
                    line.installment_id.display_name for line in rec.line_ids
                )
                rec.current_date_summary = "\n".join(
                    fields.Date.to_string(line.current_date) if line.current_date else ''
                    for line in rec.line_ids
                )
                rec.new_date_summary = "\n".join(
                    fields.Date.to_string(line.new_date) if line.new_date else ''
                    for line in rec.line_ids
                )
            else:
                rec.installment_summary = rec.installment_id.display_name or ''
                rec.current_date_summary = fields.Date.to_string(rec.current_date) if rec.current_date else ''
                rec.new_date_summary = fields.Date.to_string(rec.new_date) if rec.new_date else ''

    def write(self, vals):
        old_dates = {}
        if 'new_date' in vals:
            old_dates = {
                rec.id: rec.new_date
                for rec in self
                if not rec.line_ids and rec.state == 'pending'
            }

        result = super().write(vals)

        if 'new_date' in vals:
            for rec in self:
                old_date = old_dates.get(rec.id)
                if rec.id not in old_dates or _date_to_string(old_date) == _date_to_string(rec.new_date):
                    continue

                body = Markup(
                    "New Extended Date <b>Changed</b> for <b>%s</b><br/>Old Date: %s<br/>New Date: %s"
                ) % (
                    rec.installment_id.display_name,
                    _date_to_string(old_date),
                    _date_to_string(rec.new_date),
                )
                rec.message_post(body=body)

        return result

    def action_approve(self):
        legacy_requests = self.filtered(lambda request: not request.line_ids)
        if legacy_requests:
            super(CollectionPaymentExtensionRequest, legacy_requests).action_approve()

        for rec in self - legacy_requests:
            message_lines = []
            for line in rec.line_ids:
                installment = line.installment_id
                old_date = installment.extended_date or installment.due_date
                line_reason = line.reason or rec.reason

                installment.sudo().with_context(due_date_update_source='extension').write({
                    'extended_date': line.new_date,
                    'due_date': line.new_date,
                    'remark': (installment.remark or '') + "\n[Extension Approved] %s -> %s : %s" % (
                        old_date,
                        line.new_date,
                        line_reason,
                    ),
                })

                if hasattr(installment, '_compute_state'):
                    installment.sudo()._compute_state()

                message_lines.append(
                    Markup("<b>%s</b>: %s -> %s") % (installment.name, old_date, line.new_date)
                )

            rec.state = 'approved'
            body = Markup(
                "Payment Extension <b>Approved</b> for reference <b>%s</b><br/>%s<br/>Reason: %s"
            ) % (
                rec.name,
                Markup("<br/>").join(message_lines),
                rec.reason,
            )
            rec.collection_id.sudo().message_post(body=body)

    def perform_rejection(self, reason):
        legacy_requests = self.filtered(lambda request: not request.line_ids)
        if legacy_requests:
            super(CollectionPaymentExtensionRequest, legacy_requests).perform_rejection(reason)

        for req in self - legacy_requests:
            req.write({'state': 'rejected', 'rejection_reason': reason})
            body = Markup(
                "Payment Extension <b>Rejected</b> for reference <b>%s</b><br/>Installments: %s<br/>Reason: %s"
            ) % (
                req.name,
                req.installment_count,
                reason,
            )
            req.collection_id.sudo().message_post(body=body)
