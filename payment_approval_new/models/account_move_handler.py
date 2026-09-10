# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AccountMoveHandler(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        """Override to enforce fs_number for collection invoices"""
        res = super(AccountMoveHandler, self).action_post()
        
        # For collection invoices, ensure fs_number is set if missing
        for move in self:
            if move.is_collection_invoice and not move.fs_number:
                # Try to get from collection.installment.payment
                payment = self.env['collection.installment.payment'].search([
                    ('invoice_id', '=', move.id)
                ], limit=1)
                
                if payment:
                    if payment.reference_number:
                        move.fs_number = payment.reference_number
                    elif payment.reference:
                        move.fs_number = payment.reference
                    else:
                        move.fs_number = f"LEGACY-{payment.id}"
        
        return res
