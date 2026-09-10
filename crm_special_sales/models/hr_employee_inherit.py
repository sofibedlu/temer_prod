# -*- coding: utf-8 -*-
from odoo import models, api


class TemerLeadSudoCompute(models.Model):
    _inherit = 'temer.lead'

    @api.depends('user_id')
    @api.onchange('user_id')
    def _compute_sales_structure(self):
        """Run with sudo so users without Property Sales groups don't get
        AccessError on property.salesperson.mapping / property.sales.supervisor."""
        return super(TemerLeadSudoCompute, self.sudo())._compute_sales_structure()
