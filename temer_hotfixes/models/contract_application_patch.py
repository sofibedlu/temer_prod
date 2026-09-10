from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

try:
    from ethioqen.calendar_conversion import convert_gregorian_to_ethiopian
except ImportError:
    convert_gregorian_to_ethiopian = None
    _logger.warning("The 'ethioqen' library is missing. Please install it.")

class ContractApplication(models.Model):
    _inherit = 'contract.application'

    contract_date_char = fields.Char(default=lambda self: self._get_default_ethiopian_date())

    def _get_default_ethiopian_date(self):
        """
        Set default Ethiopian date for contract date.
        """
        if not convert_gregorian_to_ethiopian:
            return ""
            
        today = fields.Date.context_today(self)
        
        try:
            eth_year, eth_month, eth_day = convert_gregorian_to_ethiopian(today.year, today.month, today.day)
            
            # Format as DD/MM/YYYY
            return f"{eth_day:02d}/{eth_month:02d}/{eth_year}"
        except Exception as e:
            _logger.error("Failed to convert default contract date: %s", str(e))
            return ""