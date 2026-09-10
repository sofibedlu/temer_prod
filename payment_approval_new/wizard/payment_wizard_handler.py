# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PaymentWizardHandler(models.TransientModel):
    """Handler for payment wizard - creates payment approval records"""
    _inherit = 'property.payment.register.wizard'

    attachment = fields.Binary(string='Attachment')
    attachment_filename = fields.Char(string='Attachment Filename')

    def _validate_amount_and_discount(self):
        """Mirror core collection validations (amount + discount) without touching that module."""
        self.ensure_one()

        installment = self.installment_id
        if not installment:
            return

        # 1) Block when installment is already in pending state
        #    (inline pay is hidden; wizard should respect the same rule)
        if getattr(installment, "state", False) == "pending":
            raise UserError(
                _("You cannot register a new payment while this installment is in Pending approval.")
            )

        # 2) Amount must be positive and cannot exceed residual
        residual = installment.amount_residual or 0.0
        if self.amount <= 0:
            raise UserError(_("Payment amount must be greater than zero."))
        if residual and self.amount > residual:
            raise UserError(
                _(
                    "You cannot pay %(amount)s. The remaining amount for this installment is only %(residual)s."
                )
                % {"amount": self.amount, "residual": residual}
            )

        # 3) Discount percentage limit (same logic as original wizard)
        if getattr(self, "apply_discount", False) and self.discount_percentage > 0:
            # Use the same config model as collection_management without importing its helpers
            config = (
                self.env["collection.discount.config"].sudo().search([], limit=1)
            )
            max_percent = (
                config.max_manual_discount_percentage if config else 10.0
            )
            if self.discount_percentage > max_percent:
                raise UserError(
                    _(
                        "You cannot apply a discount of %(disc)s%%. "
                        "The maximum allowed is %(max)s%%."
                    )
                    % {
                        "disc": self.discount_percentage,
                        "max": max_percent,
                    }
                )

    def action_confirm_payment(self):
        """Override to create payment approval record instead of invoice."""
        # Apply the same business rules as the collection wizard (amount + discount + pending state)
        self._validate_amount_and_discount()

        # Create payment approval record instead of immediate invoice creation
        # Use sudo() to bypass Payment Dashboard group requirement when creating from collection module
        approval_record = self.env["payment.approval.record"].sudo().create(
            {
                "installment_id": self.installment_id.id,
                "amount": self.amount,
                "payment_date": self.payment_date,
                "journal_type": self.journal_type,
                "bank_id": self.bank_id.id if self.bank_id else False,
                "document_type_id": self.document_type_id.id
                if self.document_type_id
                else False,
                "payment_receipt": self.payment_receipt,
                "reference": self.reference_number or self.reference or "",
                "reference_number": self.reference_number or self.reference or "",
                "apply_discount": self.apply_discount,
                "discount_percentage": self.discount_percentage
                if self.apply_discount
                else 0.0,
                "discount_amount": self.discount_amount
                if self.apply_discount
                else 0.0,
                "attachment": self.attachment,
                "attachment_filename": self.attachment_filename,
                "state": "draft",
            }
        )

        # Post success message
        message = _(
            "Payment record created successfully! Amount: %s. "
            "Please check Payment Approval > Incoming Payment to approve."
        ) % approval_record.amount
        approval_record.message_post(body=message)

        return {"type": "ir.actions.act_window_close"}
