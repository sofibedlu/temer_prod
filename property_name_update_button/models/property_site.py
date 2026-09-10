# -*- coding: utf-8 -*-
from odoo import models


class PropertySitePaymentSync(models.Model):
    _inherit = 'property.site'

    def write(self, vals):
        result = super().write(vals)
        if 'payment_structure_id' in vals:
            for site in self:
                properties = self.env['property.property'].search([
                    ('site', '=', site.id),
                    ('is_multi', '=', False),
                ])
                if properties:
                    properties.sudo().write({
                        'payment_structure_id': site.payment_structure_id.id or False,
                    })
        return result
