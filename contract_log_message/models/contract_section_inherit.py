import logging
from odoo import models, api, _

_logger = logging.getLogger(__name__)


class ContractSection(models.Model):
    _inherit = "contract.section"

    @api.model_create_multi
    def create(self, vals_list):
        """
        Log creation of a contract section to the chatter.
        """
        records = super(ContractSection, self).create(vals_list)
        for rec in records:
            _logger.info("Contract Section template created: %s", rec.name)
            rec.message_post(body=_("Contract Section template was created."))
        return records

    def write(self, vals):
        """
        Log manual edits to the contract section to the chatter.
        """
        res = super(ContractSection, self).write(vals)
        for rec in self:
            _logger.info("Contract Section template updated: %s", rec.name)
            rec.message_post(body=_("Contract Section template was updated."))
        return res


class ContractArticleInherit(models.Model):
    _name = "contract.section.article"
    _inherit = ["contract.section.article", "mail.thread", "mail.activity.mixin"]

    @api.model_create_multi
    def create(self, vals_list):
        """
        Log creation of a contract article to the chatter.
        """
        records = super(ContractArticleInherit, self).create(vals_list)
        for rec in records:
            _logger.info("Contract Article template created: %s", rec.main_title)
            rec.message_post(body=_("Contract Article template '%s' was created.") % rec.main_title)
        return records

    def write(self, vals):
        """
        Log manual edits to the contract article to the chatter.
        """
        res = super(ContractArticleInherit, self).write(vals)
        for rec in self:
            _logger.info("Contract Article template updated: %s", rec.main_title)
            rec.message_post(body=_("Contract Article template '%s' was updated.") % rec.main_title)
        return res
