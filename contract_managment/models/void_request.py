from odoo import models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class PropertyContractVoidRequest(models.Model):
    _inherit = 'property.contract.void.request'

    def action_approve(self):
        # Ensures the method is only called on a single record
        self.ensure_one()
        
        # Call the original method
        res = super().action_approve()

        # Validation: check for required relations
        if not self.sale_id or not self.property_id:
            _logger.info("Void Request %s missing sale or property link. Skipping contract archive update.", self.name)
            return res

        # Find the latest contract archive for this property
        contract_rec = self.env["contract.archive"].search(
            [("property_name", "=", self.property_id.name)],
            order="id desc", # 'id desc' is usually more performant than 'create_date'
            limit=1
        )

        if not contract_rec:
            raise UserError(
                _("Could not find a Contract Archive for Property %s.") % self.property_id.name
            )

        # Execute the void status update
        if hasattr(contract_rec, "action_set_void"):
            contract_rec.action_set_void()
        else:
            _logger.warning("Contract %s (ID: %s) has no method 'action_set_void'", contract_rec.name, contract_rec.id)
            return res

        # Post the notification on the Sale Order
        self.sale_id.message_post(
            body=_(
                "Contract Archive '%s' (Latest) status updated to Void via Void Request %s."
            ) % (contract_rec.name, self.name)
        )

        return res