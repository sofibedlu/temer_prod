from odoo import api, fields, models, _
from odoo.exceptions import UserError

class RebarProductionRequest(models.Model):
    _name = 'rebar.production.request'
    _description = 'Rebar Production Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(
        string='Request Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    project_id = fields.Many2one(
        comodel_name='project.project',
        string='Project',
        required=True,
        tracking=True
    )
    site_id = fields.Many2one(
        comodel_name='rebar.site',
        string='Site',
        required=True,
        tracking=True
    )
    department_id = fields.Many2one(
        comodel_name='rebar.department',
        string='Department',
        tracking=True
    )
    requested_by_id = fields.Many2one(
        comodel_name='res.users',
        string='Requested By',
        default=lambda self: self.env.user,
        required=True,
        tracking=True
    )
    request_date = fields.Date(
        string='Request Date',
        default=fields.Date.context_today,
        required=True,
        tracking=True
    )
    required_date = fields.Date(
        string='Expected / Required Date',
        required=True,
        tracking=True
    )
    priority = fields.Selection(
        [('0', 'Low'), ('1', 'Normal'), ('2', 'High'), ('3', 'Urgent')],
        string='Priority',
        default='1',
        tracking=True
    )

    # Drawing Information Section
    drawing_number = fields.Char(string='Drawing Number', tracking=True)
    drawing_version = fields.Char(string='Drawing Version', tracking=True)

    # Rich Text & Attachments
    description = fields.Html(string='Work / Technical Instructions')
    attachment_ids = fields.Many2many(
        comodel_name='ir.attachment',
        relation='rebar_production_request_ir_attachments_rel',
        column1='request_id',
        column2='attachment_id',
        string='Drawings & Attachments'
    )

    # Status Workflow
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('requested', 'Requested'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
        copy=False
    )

    # Lines
    line_ids = fields.One2many(
        comodel_name='rebar.production.request.line',
        inverse_name='request_id',
        string='Rebar Specifications',
        copy=True
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('rebar.production.request') or _('New')
        return super().create(vals_list)

    # Workflow Actions
    def action_submit(self):
        for record in self:
            if not record.line_ids:
                raise UserError(_("You cannot submit a request without any Rebar Specification Lines."))
            record.write({'state': 'requested'})
            record.message_post(body=_("Production Request has been submitted for approval."))

    def action_approve(self):
        for record in self:
            record.write({'state': 'approved'})
            record.message_post(body=_("Production Request has been Approved."))
            # Future Hook: Create Engineering Review or trigger Manufacturing Order here.

    def action_reject(self):
        for record in self:
            record.write({'state': 'rejected'})
            record.message_post(body=_("Production Request has been Rejected."))

    def action_reset_to_draft(self):
        for record in self:
            record.write({'state': 'draft'})