# -*- coding: utf-8 -*-
from odoo import models, fields, api


class PropertySite(models.Model):
    _inherit = 'property.site'

    # Fix city domain to explicitly reference the site's country_id
    # The domain was ambiguous - now it's clear it refers to the site's country_id
    city_id = fields.Many2one(
        'property.site.city', 
        string="City", 
        required=True,
        domain="[('country_id', '=', country_id)]", 
        tracking=True
    )
    
    # Fix subcity domain to explicitly reference the site's city_id
    sub_city_id = fields.Many2one(
        'property.site.subcity', 
        string="Sub City", 
        domain="[('city_id', '=', city_id)]",
        required=True, 
        tracking=True
    )
