from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ContractTemplate(models.Model):
    _inherit = 'contract.template'

    site_id = fields.Many2one(
        'property.site',
        string='Site',
        tracking=True,
    )
    developer_id = fields.Many2one(required=True)

    use_property_type_sequences = fields.Boolean(
        string="Use Property Type Sequences",
        help="If enabled, different sequences can be assigned for Residential and Commercial properties."
    )
    residential_sequence_id = fields.Many2one(
        'ir.sequence',
        string="Residential Sequence"
    )
    commercial_sequence_id = fields.Many2one(
        'ir.sequence',
        string="Commercial Sequence"
    )

    office_sequence_id = fields.Many2one(
        'ir.sequence',
        string="Office Sequence"
    )

    @api.constrains('site_id')
    def _check_unique_site_id(self):
        for rec in self:
            if not rec.site_id:
                continue

            dup = self.search([
                ('site_id', '=', rec.site_id.id),
                ('id', '!=', rec.id),
            ], limit=1)
            
            if dup:
                raise ValidationError(_(
                    "A Contract Template already exists for site '%s'."
                ) % rec.site_id.display_name)

    @api.constrains('developer_id', 'use_property_type_sequences', 'residential_sequence_id', 'commercial_sequence_id', 'office_sequence_id')
    def _check_developer_sequence_config(self):
        for template in self:
            if template.use_property_type_sequences:
                if not template.residential_sequence_id or not template.commercial_sequence_id or not template.office_sequence_id:
                    raise ValidationError(_(
                        "Please configure Residential, Commercial, and Office sequences on template '%s' when 'Use Property Type Sequences' is enabled."
                    ) % template.display_name)
                continue

            if not template.developer_id:
                continue

            seq = template.developer_id.sequence
            if not seq:
                raise ValidationError(_(
                    "The selected Developer '%s' does not have a Sequence configured.\n"
                    "Please go to Site Developers configuration and assign a Sequence."
                ) % template.developer_id.name)