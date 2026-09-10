import logging

from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class ContractArchive(models.Model):
    _inherit = "contract.archive"

    @api.model_create_multi
    def create(self, vals_list):
        """
        Log creation of a contract archive to the sale record.
        """
        records = super(ContractArchive, self).create(vals_list)
        for rec in records:
            if rec.sale_id:
                _logger.info("Contract Archive created for Sale: %s", rec.sale_id.name)
                rec.sale_id.message_post(body=_("A new Contract Archive was created for this sale."))
        return records

    def action_set_signed(self):
        """
        Log signing of the contract archive.
        """
        self.ensure_one()
        _logger.info("Setting contract archive to signed: %s", self.name)
        msg = _("Contract Archive status set to Signed.")
        self.message_post(body=msg)
        if self.sale_id:
            self.sale_id.message_post(body=msg)
        return super(ContractArchive, self).action_set_signed()

    def action_set_void(self):
        """
        Log voiding of the contract archive.
        """
        self.ensure_one()
        _logger.info("Setting contract archive to void: %s", self.name)
        msg = _("Contract Archive status set to Void.")
        self.message_post(body=msg)
        if self.sale_id:
            self.sale_id.message_post(body=msg)
        return super(ContractArchive, self).action_set_void()

    def write(self, vals):        
        """
        Log manual edits to the rendered HTML.
        """
        res = super(ContractArchive, self).write(vals)
        if 'rendered_html' in vals:
            for rec in self:
                _logger.info("Contract Archive HTML edited: %s", rec.name)
                msg = _("Contract Archive HTML content was edited.")
                rec.message_post(body=msg)
                if rec.sale_id:
                    rec.sale_id.message_post(body=msg)
        return res


class ContractArchiveLine(models.Model):
    _inherit = "contract.archive.line"

    def write(self, vals):
        """
        Log manual edits to the archive article content.
        """
        res = super(ContractArchiveLine, self).write(vals)
        if 'content' in vals or 'main_title' in vals:
            for rec in self:
                _logger.info("Contract Archive Article edited: %s", rec.main_title)
                msg = _("Archive Article '%s' was edited.") % rec.main_title
                for archive in rec.contract_ids:
                    archive.message_post(body=msg)
                    if archive.sale_id:
                        archive.sale_id.message_post(body=msg)
        return res
