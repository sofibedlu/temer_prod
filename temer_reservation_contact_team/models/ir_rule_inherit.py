# -*- coding: utf-8 -*-
import logging
from odoo import models, _
from odoo.exceptions import AccessError

_logger = logging.getLogger(__name__)


class IrRule(models.Model):
    _inherit = "ir.rule"

    def _make_access_error(self, operation, records):
        _logger.info(
            'Access Denied by record rules for operation: %s on record ids: %r, uid: %s, model: %s',
            operation, records.ids[:6], self._uid, records._name,
        )
        self = self.with_context(self.env.user.context_get())
        model = records._name
        description = self.env['ir.model']._get(model).name or model
        msg = _(
            "Access Denied\n\n"
            "You do not have permission to %s this record (%s).\n"
            "Please contact your administrator.",
            operation, description,
        )
        records.invalidate_recordset()
        return AccessError(msg)
