# -*- coding: utf-8 -*-

from odoo import _, fields, models


class CrmReceptionDuplicateWizard(models.TransientModel):
    _name = "crm.reception.duplicate.wizard"
    _description = "Duplicate Phone Information"

    reception_id = fields.Many2one(
        "crm.reception",
        string="Reception",
        required=True,
        readonly=True,
        ondelete="cascade",
    )
    message = fields.Text(
        string="Message",
        readonly=True,
        help="Duplicate phone registration message from Temer CRM and/or Reception CRM.",
    )
    existing_salesperson_id = fields.Many2one(
        "res.users",
        string="Existing Salesperson",
        readonly=True,
    )
    existing_supervisor_id = fields.Many2one(
        "property.sales.supervisor",
        string="Existing Supervisor",
        readonly=True,
    )
