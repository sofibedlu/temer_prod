from odoo import api, fields, models, _
from odoo.exceptions import UserError

class PropertySiteConstructionProgress(models.Model):
    _inherit = "property.site.construction.progress"

    state = fields.Selection(
        selection_add=[('denied', 'Denied')],
        ondelete={'denied': 'set default'}
    )

    installment_ids = fields.One2many(
        comodel_name="collection.installment",
        inverse_name="progress_entry_id",
        string="Updated Installments",
        readonly=True,
        help="Installments whose due dates were adjusted upon completion of this progress."
    )

    def action_deny(self):
        for rec in self:
            if rec.state != 'checked':
                raise UserError(_("Only 'Checked' progress entries can be denied."))
            rec.state = 'denied'
            rec.message_post(body=_("Construction Progress has been Denied."))

    def _process_completion(self):
        """ 
        update: Validate config existence.
        """
        ShiftCfg = self.env["collection.progress.shift.config"]
        
        for rec in self:
            if not rec.site_id:
                raise UserError(_("Please set Site on the progress entry before completing."))

            cfg = ShiftCfg.search([("site_id", "=", rec.site_id.id), ("active", "=", True)], limit=1)
            if not cfg:
                raise UserError(
                    _("Missing Due Date Shift Configuration!\n"
                      "Please configure the 'Collection Progress Shift Config' for the site '%s' "
                      "before approving this progress.") % rec.site_id.display_name
                )

        return super()._process_completion()