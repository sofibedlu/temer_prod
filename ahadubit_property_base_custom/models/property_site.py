# -*- coding: utf-8 -*-
from odoo import models, fields, api


class PropertySite(models.Model):
    _inherit = 'property.site'

    project_number = fields.Char(
        string="Project Number",
        required=False,
        tracking=True,
        help="Unique project identifier/number"
    )
    company_abbreviation = fields.Char(
        string="Company Abbreviation",
        related='company_id.abbreviation',
        store=True,
        readonly=True,
        help="Abbreviation of the selected company"
    )
    company_id = fields.Many2one('site.company', string="Company", required=False, tracking=True)
    company_display_name = fields.Char(
        string="Company Display Name",
        compute='_compute_company_display_name',
        store=True
    )

    @api.depends('company_id')
    def _compute_company_display_name(self):
        for site in self:
            if site.company_id:
                site.company_display_name = f"[{site.company_id.abbreviation}] {site.company_id.name}"
            else:
                site.company_display_name = False

    @api.onchange('company_id')
    def _onchange_company_id(self):
        """Update the abbreviation when company is changed"""
        if self.company_id and self.company_id.abbreviation:
            self.company_abbreviation = self.company_id.abbreviation
        else:
            self.company_abbreviation = False

