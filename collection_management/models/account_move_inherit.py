from odoo import models, fields, _
from odoo.exceptions import UserError

class AccountMove(models.Model):
    _inherit = 'account.move'
    fs_number = fields.Char(string='FS Number', copy=False, tracking=True)
    is_collection_invoice = fields.Boolean(string='Is Collection Invoice', default=False, copy=False)
    collection_payment_ids = fields.One2many(
        'collection.installment.payment', 
        'invoice_id', 
        string='Collection Payments'
    )

    def action_post(self):
        """ Enforce FS Number requirement before posting for collection invoices. """
        for move in self:
            if move.is_collection_invoice and not move.fs_number:
                raise UserError(_("You cannot confirm this invoice. Please enter the 'FS Number' (Fiscal Receipt) as it is a Collection Invoice."))
        return super(AccountMove, self).action_post()