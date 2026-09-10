# -*- coding: utf-8 -*-
##############################################################################
#
#    Ahadubit Technologies
#    Copyright (C) 2024-TODAY Ahadubit Technologies(<https://ahadubit.com>).
#    Author: Ahadubit Technologies (<https://ahadubit.com>)
#    you can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    GENERAL PUBLIC LICENSE (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from odoo import api, fields, models
from odoo.fields import Boolean

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    show_address_detail = fields.Boolean("Show Address Detail", default=False)
    allows_site_no = fields.Integer("Allowed number of sites", defualt=2)
    custom_expiration_duration_in = fields.Selection([
        ('hours', 'Hours'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
    ], string='Duration In', default='days', tracking=True)
    
    custom_expiration_duration = fields.Integer(string='Duration', required=True, tracking=True)

    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].set_param('ahadubit_property_base.show_address_detail', self.show_address_detail)
        self.env['ir.config_parameter'].set_param('ahadubit_property_base.allows_site_no', self.allows_site_no)
        self.env['ir.config_parameter'].set_param('ahadubit_property_base.custom_expiration_duration_in', self.custom_expiration_duration_in)
        self.env['ir.config_parameter'].set_param('ahadubit_property_base.custom_expiration_duration', self.custom_expiration_duration)
        return res

    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        show_address_value = self.env['ir.config_parameter'].sudo().get_param('ahadubit_property_base.show_address_detail')
        allows_site_no_value = self.env['ir.config_parameter'].sudo().get_param('ahadubit_property_base.allows_site_no')
        custom_expiration_duration_in_value = self.env['ir.config_parameter'].sudo().get_param('ahadubit_property_base.custom_expiration_duration_in')
        custom_expiration_duration_value = self.env['ir.config_parameter'].sudo().get_param('ahadubit_property_base.custom_expiration_duration')
        res.update(
            show_address_detail=Boolean(show_address_value),
            allows_site_no=int(allows_site_no_value or 0),
            custom_expiration_duration_in=custom_expiration_duration_in_value,
            custom_expiration_duration=custom_expiration_duration_value
        )
        return res





