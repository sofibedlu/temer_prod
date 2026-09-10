# -*- coding: utf-8 -*-
"""Settings for Wing Distribution – AfroMessage SMS config."""

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    wing_afromessage_from = fields.Char(
        "AfroMessage Identifier ID",
        config_parameter="wing.afromessage.from",
        help="Identifier ID from AfroMessage dashboard (list of identifiers). Leave empty to use account default. Use short code (e.g. 6033) only if that works for your account.",
    )
    wing_afromessage_sender = fields.Char(
        "AfroMessage Sender Name",
        config_parameter="wing.afromessage.sender",
        help="Sender name must be requested and approved. Use 'AfroMessage' for beta/default. Use 'Temer Properties' if approved.",
    )
