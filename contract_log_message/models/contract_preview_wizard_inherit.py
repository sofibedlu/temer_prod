import logging
from odoo import models, _

_logger = logging.getLogger(__name__)


class ContractPreviewWizard(models.TransientModel):
    _inherit = "contract.preview.wizard"

    def action_save_to_archive(self):
        """
        Inherit action_save_to_archive to add a log message to the sale record.
        """
        if self.sale_id:
            _logger.info("Saving contract archive edits for Sale: %s", self.sale_id.name)
            self.sale_id.message_post(body=_("Contract edited and saved to archive."))
        return super(ContractPreviewWizard, self).action_save_to_archive()

    def action_download_docx(self):
        """
        Inherit action_download_docx to add a log message to the sale record.
        """
        if self.sale_id:
            _logger.info("Edited and download contract edits for Sale")
            self.sale_id.message_post(body=_("Contract edited and Download Dox."))
        return super(ContractPreviewWizard, self).action_download_docx()

    def action_print_pdf(self):
        """
        Inherit action_print_pdf to add a log message to the sale record.
        """
        if self.sale_id:
            _logger.info("Saving contract archive edits for Sale: %s", self.sale_id.name)
            self.sale_id.message_post(body=_("Contract edited and Print Pdf."))
        return super(ContractPreviewWizard, self).action_print_pdf()
