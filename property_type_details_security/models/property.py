# -*- coding: utf-8 -*-
from odoo import models, fields, api

class PropertyInheritSecurity(models.Model):
    _inherit = 'property.property'

    is_sales_person_only = fields.Boolean(
        compute='_compute_is_sales_person_only',
        help="Technical field: readonly for sales person, supervisor, sales manager, and wing manager"
    )

    def _user_has_property_details_readonly(self):
        user = self.env.user

        # Roles that keep full edit access (also inherit sales_person indirectly)
        elevated_groups = (
            'temer_structure.access_property_crm_admin_group',
            'temer_structure.access_property_stock_manager_group',
            'temer_structure.access_property_reservation_manager_group',
            'temer_structure.access_property_contract_admin_group',
            'temer_structure.access_property_super_admin_group',
            'temer_structure.access_property_managment_group',
            'temer_structure.access_property_dev_admin_group1',
            'temer_structure.access_property_system_admin_group',
            'advanced_property_management.group_property_manager',
            'base.group_system',
        )
        if any(user.has_group(group) for group in elevated_groups):
            return False

        # Readonly only for CRM sales hierarchy roles
        sales_readonly_groups = (
            'temer_structure.access_property_wing_manager_group',
            'temer_structure.access_property_sales_team_manager_group',
            'temer_structure.access_property_sales_supervisor_group',
            'temer_structure.access_property_sales_person_group',
        )
        return any(user.has_group(group) for group in sales_readonly_groups)

    @api.depends_context('uid')
    def _compute_is_sales_person_only(self):
        for rec in self:
            rec.is_sales_person_only = rec._user_has_property_details_readonly()

    @api.model_create_multi
    def create(self, vals_list):
        protected_fields = [
            'property_type_bedroom', 'property_type_bathroom', 
            'property_type_has_maid_room', 'property_type_no_kitchen', 
            'property_type_gross_area', 'property_type_net_area', 
            'property_type_floor_plan', 'property_type_floor_plan_filename',
            'unit_price', 'override_price_m2', 'price',
            'manual_unit_price', 'use_manual_sale_price',
            'rate_per_m2', 'commercial_amount', 'commercial_rate_range_id',
            'unit_number', 'gross_area', 'net_area', 'usage', 'finishing',
            'commercial_gross_range_id', 'commercial_location'
        ]
        
        if self._user_has_property_details_readonly():
            for vals in vals_list:
                for field in protected_fields:
                    if field in vals:
                        vals.pop(field)
                        
        return super().create(vals_list)

    def write(self, vals):
        protected_fields = [
            'property_type_bedroom', 'property_type_bathroom', 
            'property_type_has_maid_room', 'property_type_no_kitchen', 
            'property_type_gross_area', 'property_type_net_area', 
            'property_type_floor_plan', 'property_type_floor_plan_filename',
            'unit_price', 'override_price_m2', 'price',
            'manual_unit_price', 'use_manual_sale_price',
            'rate_per_m2', 'commercial_amount', 'commercial_rate_range_id',
            'unit_number', 'gross_area', 'net_area', 'usage', 'finishing',
            'commercial_gross_range_id', 'commercial_location'
        ]
        
        if self._user_has_property_details_readonly():
            for field in protected_fields:
                if field in vals:
                    vals.pop(field)
                    
        return super().write(vals)
