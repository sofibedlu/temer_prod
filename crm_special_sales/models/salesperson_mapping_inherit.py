# -*- coding: utf-8 -*-
from odoo import models
from odoo.exceptions import UserError


def _model_exists(env, model_name):
    return model_name in env.registry


class PropertySalespersonMappingInherit(models.Model):
    _inherit = 'property.salesperson.mapping'

    def check_access_rights(self, operation, raise_exception=True):
        """Allow read access for all users — this model only maps salespersons
        to supervisors for UI domain filtering, no sensitive data."""
        if operation == 'read':
            return True
        return super().check_access_rights(operation, raise_exception=raise_exception)
