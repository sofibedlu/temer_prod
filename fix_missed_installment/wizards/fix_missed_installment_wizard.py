from odoo import models, fields, api, _
from odoo.exceptions import UserError


class FixMissedInstallmentWizard(models.TransientModel):
    _name = "fix.missed.installment.wizard"
    _description = "Fix Missed Installment — Standalone Wizard"

   
    log_id = fields.Many2one(
        "installment.update.log",
        string="Log Entry",
        help="Select a log entry — site, old and new installment fill automatically.",
    )

  
    site_id = fields.Many2one(
        "property.site",
        string="Site / Project",
        required=True,
    )
    old_installment = fields.Char(string="Old Installment Name", required=True)
    new_installment = fields.Char(string="New Installment Name", required=True)

   
    payment_line_count = fields.Integer(
        string="Property Payment Lines Found", readonly=True,
    )
    collection_count = fields.Integer(
        string="Collection Installments Found", readonly=True,
    )

   
    @api.onchange("log_id")
    def _onchange_log_id(self):
        if not self.log_id:
            return
        self.site_id         = self.log_id.site_id
        self.old_installment = self.log_id.old_installment
        self.new_installment = self.log_id.new_installment

        # collection.order.site_id is stored — direct search, no join
        col_orders = self.env["collection.order"].search([
            ("site_id", "=", self.log_id.site_id.id),
        ])
        # collection.installments matching the old name under those orders
        col_recs = self.env["collection.installment"].search([
            ("collection_id", "in", col_orders.ids),
            ("name", "=", self.log_id.old_installment),
        ])
        self.collection_count = len(col_recs)

        # sale_id is a direct stored field on collection.order
        sale_ids = col_orders.mapped("sale_id").ids
        self.payment_line_count = self.env["property.payment.line"].search_count([
            ("sale_id", "in", sale_ids),
            ("payment_term_id.name", "=", self.log_id.old_installment),
        ])

   
    def action_fix_installments(self):
        self.ensure_one()
        if not self.site_id:
            raise UserError(_("Please select a Site / Project."))
        if not (self.old_installment or "").strip():
            raise UserError(_("Old Installment name is required."))
        if not (self.new_installment or "").strip():
            raise UserError(_("New Installment name is required."))
        if self.old_installment.strip() == self.new_installment.strip():
            raise UserError(_("Old and New installment names are identical — nothing to do."))

        collection_orders = self.env["collection.order"].search([
            ("site_id", "=", self.site_id.id),
        ])

        if not collection_orders:
            raise UserError(
                _("No collection orders found for site '%s'.") % self.site_id.name
            )

     
        sale_ids = collection_orders.mapped("sale_id").ids

        sales = self.env["property.sale"].browse(sale_ids)
        term_ids = sales.mapped("property_payment_term").ids

        new_term_line = self.env["property.payment.term.line"].search([
            ("name", "=", self.new_installment),
            ("payment_term_id", "in", term_ids),
        ], limit=1)

        if not new_term_line:
            raise UserError(_(
                "Could not find a payment term line named '%s' in the "
                "payment structures used by site '%s'.\n"
                "Please check the payment term configuration."
            ) % (self.new_installment, self.site_id.name))

        
        col_recs = self.env["collection.installment"].search([
            ("collection_id", "in", collection_orders.ids),
            ("name", "=", self.old_installment),
        ])
        col_count = len(col_recs)
        
        col_recs.write({
            "name": self.new_installment,
            "payment_term_line_id": new_term_line.id,
        })

      
        payment_lines = self.env["property.payment.line"].search([
            ("sale_id", "in", sale_ids),
            ("payment_term_id.name", "=", self.old_installment),
        ])
        pl_count = len(payment_lines)
        payment_lines.write({"payment_term_id": new_term_line.id})

        
        self.env["installment.update.log"].create({
            "site_id":           self.site_id.id,
            "old_installment":   self.old_installment,
            "new_installment":   self.new_installment,
            "collection_count":  col_count,
            "sale_line_count":   pl_count,
            "legacy_line_count": 0,
            "performed_by":      self.env.user.id,
        })

        return {
            "type": "ir.actions.client",
            "tag":  "display_notification",
            "params": {
                "title":   _("Fix Applied"),
                "message": _(
                    "Site: %s\n"
                    "  Term line resolved: '%s' (id=%d)\n"
                    "  %d collection installments updated\n"
                    "  %d property payment lines updated"
                ) % (
                    self.site_id.name,
                    new_term_line.name,
                    new_term_line.id,
                    col_count,
                    pl_count,
                ),
                "type":   "success",
                "sticky": False,
            },
        }
