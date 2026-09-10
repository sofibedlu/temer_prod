from odoo import _, api, fields, models
from odoo.exceptions import UserError
from markupsafe import Markup


class PropertyPaymentExtensionWizardLine(models.TransientModel):
    _name = 'property.payment.extension.wizard.line'
    _description = 'Payment Extension Wizard Line'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    wizard_id = fields.Many2one(
        'property.payment.extension.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade',
    )
    collection_id = fields.Many2one(
        'collection.order',
        string='Collection',
        related='wizard_id.collection_id',
        readonly=True,
    )
    installment_id = fields.Many2one(
        'collection.installment',
        string='Installment',
        required=True,
        domain="[('id', 'in', available_installment_ids)]",
    )
    available_installment_ids = fields.Many2many(
        'collection.installment',
        compute='_compute_available_installment_ids',
    )
    current_date = fields.Date(string='Current Due Date', readonly=True)
    new_date = fields.Date(string='New Extended Date', required=True)

    @api.depends('wizard_id.collection_id', 'wizard_id.line_ids.installment_id', 'installment_id')
    def _compute_available_installment_ids(self):
        Installment = self.env['collection.installment']
        for line in self:
            if not line.collection_id:
                line.available_installment_ids = Installment
                continue

            selected_installments = (
                line.wizard_id.line_ids - line
            ).mapped('installment_id')
            line.available_installment_ids = Installment.search([
                ('collection_id', '=', line.collection_id.id),
                ('state', '!=', 'paid'),
                ('id', 'not in', selected_installments.ids),
            ])

    @api.onchange('installment_id')
    def _onchange_installment_id(self):
        for line in self:
            if line.installment_id:
                line.current_date = line.installment_id.extended_date or line.installment_id.due_date
            else:
                line.current_date = False
        return {'domain': {'installment_id': [('id', 'in', self.available_installment_ids.ids)]}}


class PropertyPaymentExtensionWizard(models.TransientModel):
    _inherit = 'property.payment.extension.wizard'

    installment_id = fields.Many2one(
        'collection.installment',
        string='Select Installment',
        required=False,
        domain="[('collection_id','=',collection_id), ('state','!=','paid')]",
    )
    new_date = fields.Date(string='New Extended Date', required=False)
    line_ids = fields.One2many(
        'property.payment.extension.wizard.line',
        'wizard_id',
        string='Installments',
    )
    selected_installment_ids = fields.Many2many(
        'collection.installment',
        compute='_compute_selected_installment_ids',
    )

    @api.depends('line_ids.installment_id')
    def _compute_selected_installment_ids(self):
        for wizard in self:
            wizard.selected_installment_ids = wizard.line_ids.mapped('installment_id')

    def action_confirm_extension(self):
        self.ensure_one()

        if not self.line_ids:
            if not self.installment_id or not self.new_date:
                raise UserError(_('Please add at least one installment with a requested date.'))
            return super().action_confirm_extension()

        seen_installments = set()
        request_lines = []
        message_lines = []

        for line in self.line_ids:
            if not line.installment_id or not line.new_date:
                raise UserError(_('Each extension line must have an installment and a requested date.'))
            if line.installment_id.id in seen_installments:
                raise UserError(_('You cannot request the same installment more than once in one extension.'))
            seen_installments.add(line.installment_id.id)

            current_date = line.current_date or line.installment_id.extended_date or line.installment_id.due_date
            request_lines.append((0, 0, {
                'sequence': line.sequence,
                'installment_id': line.installment_id.id,
                'current_date': current_date,
                'new_date': line.new_date,
                'reason': self.reason,
            }))
            message_lines.append(
                Markup("<b>%s</b>: %s -> %s") % (line.installment_id.name, current_date, line.new_date)
            )

        first_line = self.line_ids[0]
        request = self.env['collection.payment.extension.request'].sudo().create({
            'collection_id': self.collection_id.id,
            'installment_id': first_line.installment_id.id,
            'current_date': first_line.current_date or first_line.installment_id.extended_date or first_line.installment_id.due_date,
            'new_date': first_line.new_date,
            'reason': self.reason,
            'attachment_ids': [(6, 0, self.attachment_ids.ids)],
            'line_ids': request_lines,
            'state': 'pending',
        })

        for attachment in self.attachment_ids:
            attachment.write({
                'res_model': 'collection.payment.extension.request',
                'res_id': request.id,
            })

        body = Markup(
            "<b>Payment Extension Request Submitted</b> for reference <b>%s</b><br/>%s<br/>Reason: %s"
        ) % (
            request.name,
            Markup("<br/>").join(message_lines),
            self.reason,
        )
        self.collection_id.sudo().message_post(body=body)

        return {'type': 'ir.actions.act_window_close'}
