from odoo.exceptions import ValidationError, UserError
import logging
from datetime import datetime, timedelta
from odoo import api, fields, models, _
_logger = logging.getLogger(__name__)


class PropertySiteConstructionProgress(models.Model):
    _name = 'property.site.construction.progress'
    _description = 'Construction Progress Tracking'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = 'date desc'

    name = fields.Char(string="Reference", required=True, readonly=True,
                       default=lambda self: self.env['ir.sequence'].next_by_code('property.site.construction.progress'))
    site_id = fields.Many2one('property.site', string="Construction Site", required=True)
    date = fields.Date(string="Progress Date", required=True, default=fields.Date.today)
    progress_percentage = fields.Float(string="Progress (%)", required=False, digits=(5, 2))
    description = fields.Text(string="Progress Details")
    responsible_id = fields.Many2one('res.users', string="Responsible", default=lambda self: self.env.user)
    image = fields.Binary(string="Progress Photo")
    payment_term_id = fields.Many2one(
        related='site_id.payment_structure_id',
        string="Payment Term",
        readonly=True
    )
    payment_term_line_id = fields.Many2one('property.payment.term.line',
        string="Payment Term Line",domain="[('payment_term_id', '=', payment_term_id)]"
    )
    property_ids = fields.Many2many(
        'property.property',
        compute='_compute_related_properties',
        string="Related Properties",
        store=False
    )

    def _compute_related_properties(self):
        for progress in self:
            properties = self.env['property.property'].search([
                ('site', '=', progress.site_id.id),
                ('payment_structure_id', '=', progress.payment_term_id.id)
            ])
            progress.property_ids = properties



    @api.onchange('site_id')
    def _onchange_site_id(self):
        res = {}
        if self.site_id:
            res['domain'] = {
                'payment_term_line_id': [
                    ('payment_term_id', '=', self.site_id.payment_structure_id.id)
                ]
            }
            self.payment_term_id = self.site_id.payment_structure_id.id

        return res

    @api.onchange('payment_term_id')
    def _onchange_site_id(self):
        if self.payment_term_id:
            return {
                'domain': {
                    'payment_term_line_id': [
                        ('payment_term_id', '=', self.site_id.payment_structure_id.id)
                    ]
                }
            }
        return {}

    @api.constrains('progress_percentage')
    def _check_progress_percentage(self):
        for record in self:
            if record.progress_percentage < 0 or record.progress_percentage > 100:
                raise ValidationError("Progress percentage must be between 0% and 100%")


class PropertySite(models.Model):
    _inherit = 'property.site'

    construction_progress_ids = fields.One2many(
        'property.site.construction.progress',
        'site_id',
        string="Construction Progress History", domain="[('payment_term_id', '=', payment_structure_id)]"
    )
    current_progress = fields.Float(
        string="Current Progress (%)",
        compute='_compute_current_progress',
        store=True,
        digits=(5, 2))

    last_progress_date = fields.Date(
        string="Last Progress Update",
        compute='_compute_current_progress',
        store=True)

    @api.depends('construction_progress_ids', 'construction_progress_ids.progress_percentage','construction_progress_ids.date')
    def _compute_current_progress(self):
        for site in self:
            if site.construction_progress_ids:
                latest = max(site.construction_progress_ids, key=lambda x: x.date)
                site.current_progress = latest.progress_percentage
                site.last_progress_date = latest.date
            else:
                site.current_progress = 0.0
                site.last_progress_date = False



