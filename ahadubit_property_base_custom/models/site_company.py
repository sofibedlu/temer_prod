# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SiteCompany(models.Model):
    _name = 'site.company'
    _description = 'Site Company'
    _rec_name = 'display_name'
    _order = 'name asc'

    name = fields.Char(string="Company Name", required=True)
    abbreviation = fields.Char(string="Abbreviation", required=True)

    # Add a computed field for display
    display_name = fields.Char(
        string="Display Name",
        compute='_compute_display_name',
        store=True
    )

    @api.depends('name', 'abbreviation')
    def _compute_display_name(self):
        for company in self:
            if company.abbreviation:
                company.display_name = f"[{company.abbreviation}] {company.name}"
            else:
                company.display_name = company.name

    _sql_constraints = [
        ('unique_name', 'unique(name)', 'The company name must be unique.'),
        ('unique_abbreviation', 'unique(abbreviation)', 'The abbreviation must be unique.'),
    ]

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """Search by both name and abbreviation"""
        if args is None:
            args = []

        # Search by both name and abbreviation
        domain = ['|', ('name', operator, name), ('abbreviation', operator, name)]

        # Add any additional args
        domain = args + domain

        # Search with the domain
        records = self.search(domain, limit=limit)

        # Return results
        return records.name_get()

