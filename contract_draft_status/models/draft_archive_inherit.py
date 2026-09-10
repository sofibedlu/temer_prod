# -*- coding: utf-8 -*-
from odoo import models, fields


class DraftContractArchiveStatus(models.Model):
    _inherit = "draft.contract.archive"

    draft_status = fields.Selection(
        [
            ("draft", "Draft"),
            ("saved", "Saved to Archive"),
        ],
        string="Draft Status",
        default="draft",
        tracking=True,
        help="Draft: content is still being edited. Saved: content has been saved to the contract archive."
    )
