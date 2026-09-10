import logging
from odoo import models, _

_logger = logging.getLogger(__name__)


class PropertySale(models.Model):
    _inherit = "property.sale"

    def action_print_contract(self):
        """
        Inherit action_print_contract to add a log message.
        """
        _logger.info("Printing contract for Sale: %s", self.name)
        self.message_post(body=_("Contract Preview started"))
        return super(PropertySale, self).action_print_contract()
