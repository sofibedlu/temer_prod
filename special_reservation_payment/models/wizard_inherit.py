# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class PropertyReservationPaymentFix(models.Model):
    """
    Fix the pre-existing ensure_one bug in ahadubit_property_reservation's write method.
    Original line: `elif self.payment_status in [...]` crashes on multi-record write
    because self.payment_status calls ensure_one() on a recordset.

    Also adds is_wizard_temp to tag lines that were added through the Special Approval
    Wizard but not yet submitted.  On wizard open these are cleaned up so stale lines
    from a previous failed/abandoned session don't carry over.  On Submit they are
    cleared (is_wizard_temp = False) to make them permanent.
    """
    _inherit = 'property.reservation.payment'

    is_wizard_temp = fields.Boolean(
        string='Wizard Temp',
        default=False,
    )

    @api.model
    def create(self, vals):
        if self.env.context.get('default_is_wizard_temp') or \
                self.env.context.get('from_special_wizard'):
            vals.setdefault('is_wizard_temp', True)
            vals['is_new_line'] = False
        return super().create(vals)

    def unlink(self):
        if self.env.context.get('special_wizard_cleanup'):
            disallowed = self.filtered(lambda r: not r.is_wizard_temp)
            if disallowed:
                raise ValidationError(_(
                    "Cannot remove payment lines that are already saved in "
                    "Receipt Dashboard."
                ))
            return models.Model.unlink(self)
        return super().unlink()

    def write(self, vals):
        if 'is_verifed' in vals and vals['is_verifed']:
            vals['payment_status'] = 'approved'
            return super().write(vals)

        # Fix: the base write() does `elif self.payment_status in [...]` which crashes
        # on multi-record sets. We replicate the logic correctly per-record.
        if 'is_verifed' in vals or 'payment_status' in vals:
            # Only split when the problematic fields are involved
            canceled_draft = self.filtered(lambda r: r.payment_status in ['canceled', 'draft'])
            others = self - canceled_draft
            if canceled_draft:
                super(PropertyReservationPaymentFix, canceled_draft).write(
                    dict(vals, payment_status='requested', is_verifed=False)
                )
            if others:
                return super(PropertyReservationPaymentFix, others).write(vals)
            return True

        # For all other field writes (is_new_line, ref_number, etc.) — call super directly
        # without splitting, since the base write() only has the bug when is_verifed/payment_status
        # triggers the elif branch. We bypass the base write() entirely and call the grandparent.
        # Actually we must call super() to get mail tracking etc., but we need to avoid the bug.
        # Solution: write per-record to avoid the ensure_one crash in the elif branch.
        result = True
        for rec in self:
            result = super(PropertyReservationPaymentFix, rec).write(vals)
        return result


class SpecialWizardTempPaymentLine(models.TransientModel):
    """
    Temporary payment lines stored in the wizard session only.
    Committed to property.reservation.payment on Submit/Approve.
    """
    _name = 'special.wizard.temp.payment.line'
    _description = 'Special Wizard Temporary Payment Line'

    wizard_id = fields.Many2one(
        'special.approval.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade',
    )
    bank_id = fields.Many2one('bank.configuration', string='Bank', required=True)
    document_type_id = fields.Many2one('bank.document.type', string='Document Type', required=True)
    ref_number = fields.Char(string='Reference Number', required=True)
    transaction_date = fields.Date(
        string='Transaction Date',
        required=True,
        default=fields.Date.today,
    )
    amount = fields.Float(string='Amount', required=True)
    payment_receipt = fields.Binary(string='Payment Receipt', required=True)
    payment_receipt_filename = fields.Char(string='Receipt Filename')


class SpecialApprovalWizardPayment(models.Model):
    _inherit = 'special.approval.wizard'

    # Direct proxy to the reservation's real payment lines.
    # Writing here creates/deletes property.reservation.payment records immediately,
    # so lines survive wizard close/reopen (they live on the reservation, not the wizard).
    payment_line_ids = fields.One2many(
        related='reservation_id.payment_line_ids',
        readonly=False,
        string='Payment Lines',
    )

    def write(self, vals):
        # Draft wizard sessions must use temp_payment_line_ids only.
        # Related payment_line_ids writes create real reservation lines and
        # trigger receipt_dashboard immediately — block that before submit.
        vals = dict(vals)
        if 'payment_line_ids' in vals:
            for cmd in (vals.get('payment_line_ids') or []):
                if isinstance(cmd, (list, tuple)) and cmd and cmd[0] == 2:
                    raise ValidationError(_(
                        "You cannot delete payment lines that are already saved "
                        "in Receipt Dashboard.\n"
                        "Please fix the amount or contact your supervisor."
                    ))
            if all(
                (rec.reservation_id and rec.reservation_id.state == 'draft')
                for rec in self
            ):
                vals.pop('payment_line_ids')
            else:
                patched = []
                for cmd in (vals.get('payment_line_ids') or []):
                    if isinstance(cmd, (list, tuple)) and len(cmd) == 3 and cmd[0] == 0:
                        line_vals = dict(cmd[2])
                        line_vals['is_wizard_temp'] = True
                        patched.append((0, 0, line_vals))
                    else:
                        patched.append(cmd)
                vals['payment_line_ids'] = patched

        result = super().write(vals)
        return result

    def web_save(self, vals, specification, next_id=None):
        """Save and submit in one step — same behavior as the Submit button."""
        if self:
            self.write(vals)
            record = self
        else:
            record = self.create(vals)
        if record.state == 'draft':
            record._finalize_and_submit()
        if next_id:
            record = record.browse(next_id)
        return record.with_context(bin_size=True).web_read(specification)

    show_add_payment = fields.Boolean(
        compute='_compute_show_add_payment',
        store=False,
    )

    wizard_payment_total = fields.Float(
        string='Payment Total',
        compute='_compute_wizard_payment_total',
        store=False,
    )

    # ── kept for backward-compat (supervisor/CEO verified toggle, ref_edit) ──
    existing_payment_line_ids = fields.One2many(
        'property.reservation.payment',
        compute='_compute_existing_payment_lines',
        inverse='_inverse_existing_payment_lines',
        string='Committed Payment Lines',
        readonly=False,
    )

    has_committed_lines = fields.Boolean(
        compute='_compute_existing_payment_lines',
        store=False,
    )

    show_committed_payment_lines = fields.Boolean(
        compute='_compute_show_committed_payment_lines',
        store=False,
    )

    # kept for backward-compat — not shown in the view anymore
    temp_payment_line_ids = fields.One2many(
        'special.wizard.temp.payment.line',
        'wizard_id',
        string='Temp Payment Lines',
    )

    @api.model
    def create(self, vals):
        rec = super().create(vals)
        if rec.reservation_id:
            rec._cleanup_abandoned_payment_lines()
            if rec.reservation_id.state != 'draft':
                rec._confirm_reservation_payment_lines()
        return rec

    def _confirm_reservation_payment_lines(self):
        """Submitted special-approval lines must not show the Confirm button."""
        self.ensure_one()
        if not self.reservation_id:
            return
        new_lines = self.reservation_id.payment_line_ids.filtered('is_new_line')
        if new_lines:
            new_lines.sudo().write({'is_new_line': False})

    def _cleanup_abandoned_payment_lines(self):
        """Remove only abandoned wizard-temp lines, keep committed receipt lines."""
        self.ensure_one()
        reservation = self.reservation_id
        if not reservation:
            return

        Payment = self.env['property.reservation.payment'].sudo()
        ReceiptRecord = self.env['receipt.approval.record'].sudo()

        stale = Payment.search([
            ('reservation_id', '=', reservation.id),
            ('is_wizard_temp', '=', True),
        ])
        if stale:
            receipts = ReceiptRecord.search([
                ('payment_line_id', 'in', stale.ids),
                ('state', '=', 'draft'),
            ])
            if receipts:
                receipts.unlink()
            stale.with_context(special_wizard_cleanup=True).unlink()

    def action_clear_temp_payment_lines(self):
        """Allow salesperson to clear draft payment lines added by mistake."""
        self.ensure_one()
        self.temp_payment_line_ids.unlink()
        return True

    @api.depends('reservation_id', 'reservation_id.payment_line_ids')
    def _compute_existing_payment_lines(self):
        for rec in self:
            lines = rec.reservation_id.payment_line_ids if rec.reservation_id else \
                self.env['property.reservation.payment']
            rec.existing_payment_line_ids = lines
            rec.has_committed_lines = bool(lines)

    def _inverse_existing_payment_lines(self):
        pass

    @api.depends('state', 'reservation_id.payment_line_ids', 'temp_payment_line_ids')
    def _compute_show_committed_payment_lines(self):
        for rec in self:
            rec.show_committed_payment_lines = (
                rec.state != 'draft'
                or bool(rec.reservation_id.payment_line_ids)
            )

    @api.depends('amount')
    def _compute_show_add_payment(self):
        for rec in self:
            rec.show_add_payment = (rec.amount or 0.0) > 0.0

    @api.depends('amount', 'temp_payment_line_ids.amount', 'state',
                 'reservation_id.payment_line_ids.amount')
    def _compute_wizard_payment_total(self):
        for rec in self:
            temp_total = sum(rec.temp_payment_line_ids.mapped('amount'))
            committed_total = (
                sum(rec.reservation_id.payment_line_ids.mapped('amount'))
                if rec.reservation_id else 0.0
            )
            # Sum temp + committed so duplicate/old lines are visible in the total.
            rec.wizard_payment_total = temp_total + committed_total

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _commit_temp_lines(self):
        """
        Commit temp lines to property.reservation.payment and create draft
        receipt.approval.record entries (same as receipt_dashboard write hook does).
        We create payment lines directly (not via reservation.write) to avoid
        triggering the ensure_one bug in the base write method, so we manually
        replicate the receipt_dashboard write hook behavior here.
        """
        self.ensure_one()
        reservation = self.reservation_id
        ReceiptRecord = self.env['receipt.approval.record'].sudo()

        for line in self.temp_payment_line_ids:
            payment = self.env['property.reservation.payment'].sudo().create({
                'reservation_id': reservation.id,
                'bank_id': line.bank_id.id,
                'document_type_id': line.document_type_id.id,
                'ref_number': line.ref_number,
                'transaction_date': line.transaction_date,
                'amount': line.amount,
                'payment_receipt': line.payment_receipt,
                'payment_status': 'requested',
            })

            # Force is_new_line=False — base create() sets it True when reservation
            # status is not draft, which shows the Confirm button.
            # Write via ORM (bypasses our write() override since is_new_line is not
            # in the problematic elif branch) to update both DB and ORM cache.
            payment.sudo().write({'is_new_line': False})

            # Create draft receipt record — mirrors receipt_dashboard write hook exactly
            existing = ReceiptRecord.search(
                [('payment_line_id', '=', payment.id)], limit=1
            )
            if not existing:
                receipt_rec = ReceiptRecord.create({
                    'reservation_id': reservation.id,
                    'payment_line_id': payment.id,
                    'amount': payment.amount,
                    'state': 'draft',
                })
                receipt_rec._compute_payment_receipt()
                receipt_rec._compute_payment_receipt_filename()
                receipt_rec.invalidate_recordset(['payment_receipt', 'receipt_display'])

                # Post chatter log on reservation (same as receipt_dashboard write hook)
                reservation.message_post(
                    body=_(
                        "New payment line added. Draft receipt approval record created.\n"
                        "Reference: %s\n"
                        "Amount: %s\n"
                        "Pending approval in Receipt Dashboard."
                    ) % (payment.ref_number or 'N/A', payment.amount),
                    message_type='comment',
                    subtype_xmlid='mail.mt_comment',
                )
                # Schedule activity (same as receipt_dashboard write hook)
                reservation.activity_schedule(
                    activity_type_id=self.env.ref('mail.mail_activity_data_todo').id,
                    summary=_('Receipt Approval Required'),
                    note=_(
                        'A new payment line (Ref: %s, Amount: %s) was added. '
                        'Please review and approve in the Receipt Dashboard.'
                    ) % (payment.ref_number or 'N/A', payment.amount),
                    user_id=self.env.user.id,
                )

        self.temp_payment_line_ids.unlink()

    def _validate_temp_payment_lines(self, amount):
        """Validate draft wizard temp lines sum to the requested amount."""
        temp_lines = self.temp_payment_line_ids
        if not temp_lines:
            raise ValidationError(_(
                "Please add payment before proceeding.\n"
                "Amount is %.2f — add payment lines matching this amount."
            ) % amount)
        temp_total = sum(temp_lines.mapped('amount'))
        if abs(temp_total - amount) > 0.01:
            raise ValidationError(_(
                "Payment total (%.2f) does not match the requested amount (%.2f).\n"
                "Adjust your payment lines."
            ) % (temp_total, amount))

    def _validate_reservation_payment_lines(self, amount):
        """Validate committed reservation payment lines sum to amount."""
        if not self.reservation_id:
            raise ValidationError(_(
                "Please add payment before proceeding.\n"
                "Amount is %.2f — add payment lines matching this amount."
            ) % amount)
        lines = self.reservation_id.payment_line_ids
        if not lines:
            raise ValidationError(_(
                "Please add payment before proceeding.\n"
                "Amount is %.2f — add payment lines matching this amount."
            ) % amount)
        total = sum(lines.mapped('amount'))
        if abs(total - amount) > 0.01:
            raise ValidationError(_(
                "Payment total (%.2f) does not match the requested amount (%.2f).\n"
                "Adjust your payment lines."
            ) % (total, amount))

    def _validate_payment_amount(self, amount):
        """Validate that is_wizard_temp lines added in this session sum to amount."""
        if not self.reservation_id:
            raise ValidationError(_(
                "Please add payment before proceeding.\n"
                "Amount is %.2f — add payment lines matching this amount."
            ) % amount)
        # Use a fresh DB search instead of self.reservation_id.payment_line_ids
        # to avoid stale ORM cache.  In Odoo 17 the web_save (auto-save) and the
        # button action share the same server request: the related-field write that
        # creates new payment lines has already run, but the cached recordset on
        # self.reservation_id may still reflect the pre-write snapshot.
        temp_lines = self.env['property.reservation.payment'].sudo().search([
            ('reservation_id', '=', self.reservation_id.id),
            ('is_wizard_temp', '=', True),
        ])
        temp_total = sum(temp_lines.mapped('amount'))

        if not temp_lines:
            raise ValidationError(_(
                "Please add payment before proceeding.\n"
                "Amount is %.2f — add payment lines matching this amount."
            ) % amount)
        if abs(temp_total - amount) > 0.01:
            raise ValidationError(_(
                "Payment total (%.2f) does not match the requested amount (%.2f).\n"
                "Adjust your payment lines."
            ) % (temp_total, amount))

    def _validate_all_verified(self):
        """
        Block Supervisor Approve / Final Approve if any payment line is not verified.
        The supervisor verifies lines by toggling is_verifed ON in the payment table.
        This check only runs when the approve button is clicked — not on Save.
        """
        if not self.reservation_id:
            return
        lines = self.reservation_id.payment_line_ids
        if not lines:
            return  # No lines — nothing to verify (amount=0 case handled upstream)
        unverified = lines.filtered(lambda l: not l.is_verifed)
        if unverified:
            refs = ', '.join(r for r in unverified.mapped('ref_number') if r) or _('(no reference)')
            raise ValidationError(_(
                "Cannot approve: %d payment line(s) are not verified yet.\n\n"
                "Unverified references: %s\n\n"
                "Please toggle the Verified switch ON for each payment line before approving."
            ) % (len(unverified), refs))

    # ------------------------------------------------------------------
    # Add Payment Line — explicit action so mobile/phone users get a
    # proper dialog instead of navigating away to a tree list.
    # ------------------------------------------------------------------
    def action_add_payment_line(self):
        """Open temp payment line form — nothing is committed until Submit."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Add Payment',
            'res_model': 'special.wizard.temp.payment.line',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_wizard_id': self.id,
            },
        }

    def _create_receipt_records_for_lines(self, payment_lines):
        """Create draft receipt.approval.record for newly committed payment lines.

        The receipt_dashboard write hook now skips is_wizard_temp lines to avoid
        creating receipts for abandoned wizard sessions.  We therefore must create
        the receipt records here, at the moment the wizard is successfully submitted
        and the lines are made permanent.
        """
        ReceiptRecord = self.env['receipt.approval.record'].sudo()
        reservation = self.reservation_id
        for line in payment_lines:
            existing = ReceiptRecord.search([
                ('payment_line_id', '=', line.id),
                ('reservation_id', '=', reservation.id),
            ], limit=1)
            if existing:
                continue
            record = ReceiptRecord.create({
                'reservation_id': reservation.id,
                'payment_line_id': line.id,
                'amount': line.amount,
                'state': 'draft',
            })
            record._compute_payment_receipt()
            record._compute_payment_receipt_filename()
            record.invalidate_recordset(['payment_receipt', 'receipt_display'])
            reservation.message_post(
                body=_(
                    'New payment line added. Draft receipt approval record created.\n'
                    'Reference: %s\n'
                    'Amount: %s\n'
                    'Pending approval in Receipt Dashboard.'
                ) % (line.ref_number or 'N/A', line.amount),
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
            )
            reservation.activity_schedule(
                activity_type_id=self.env.ref('mail.mail_activity_data_todo').id,
                summary=_('Receipt Approval Required'),
                note=_(
                    'A new payment line (Ref: %s, Amount: %s) was added. '
                    'Please review and approve in the Receipt Dashboard.'
                ) % (line.ref_number or 'N/A', line.amount),
                user_id=self.env.user.id,
            )

    # ------------------------------------------------------------------
    # Shared Save / Submit flow
    # ------------------------------------------------------------------

    def _ensure_request_letter(self):
        if self.reservation_id and not self.reservation_id.request_letter:
            if self.reservation_id.special_attachment_ids:
                self.reservation_id.sudo().write({
                    'request_letter': self.reservation_id.special_attachment_ids[0].datas
                })
            elif self.attachment:
                self.reservation_id.sudo().write({'request_letter': self.attachment})

    def _commit_payment_lines(self):
        """Validate and commit payment lines; create receipt records on submit."""
        self.ensure_one()
        amount = self.amount or 0.0
        if amount <= 0:
            return
        committed = self.reservation_id.payment_line_ids if self.reservation_id else \
            self.env['property.reservation.payment']
        if committed and self.temp_payment_line_ids:
            raise ValidationError(_(
                "This reservation already has payment lines saved in Receipt Dashboard.\n"
                "Payment total on reservation (%.2f) must match amount (%.2f).\n"
                "You cannot add new lines on top — contact your supervisor to fix duplicate lines."
            ) % (sum(committed.mapped('amount')), amount))
        if committed:
            # Lines already saved on reservation / Receipt Dashboard.
            self._validate_reservation_payment_lines(amount)
            self._confirm_reservation_payment_lines()
            self._create_receipt_records_for_lines(committed)
            return
        if self.temp_payment_line_ids:
            self._validate_temp_payment_lines(amount)
            self._commit_temp_lines()
            return
        # Legacy fallback for is_wizard_temp lines on reservation.
        self._validate_payment_amount(amount)
        if self.reservation_id:
            temp_lines = self.env['property.reservation.payment'].sudo().search([
                ('reservation_id', '=', self.reservation_id.id),
                ('is_wizard_temp', '=', True),
            ])
            temp_lines.write({'is_wizard_temp': False, 'is_new_line': False})
            self._create_receipt_records_for_lines(temp_lines)

    def _finalize_and_submit(self):
        """Full submit flow used by both Save and Submit."""
        self.ensure_one()
        if self.state != 'draft':
            return True
        self._commit_payment_lines()
        self._confirm_reservation_payment_lines()
        self._ensure_request_letter()
        return super(SpecialApprovalWizardPayment, self).action_submit()

    # ------------------------------------------------------------------
    # Override action_submit
    # ------------------------------------------------------------------
    def action_submit(self):
        self.ensure_one()
        return self._finalize_and_submit()

    # ------------------------------------------------------------------
    # Override action_manager_approve (Supervisor Approve button)
    # ------------------------------------------------------------------
    def action_manager_approve(self):
        self.ensure_one()
        amount = self.amount or 0.0
        if amount > 0:
            self._validate_all_verified()
        return super().action_manager_approve()

    # ------------------------------------------------------------------
    # Override action_final_approve (CEO Final Approve)
    # ------------------------------------------------------------------
    def action_final_approve(self):
        self.ensure_one()
        amount = self.amount or 0.0

        if amount > 0:
            self._validate_all_verified()
            # Commit any remaining temp lines (edge case: CEO added lines)
            if self.temp_payment_line_ids:
                self._validate_temp_payment_lines(amount)
                self._commit_temp_lines()

        # Ensure request_letter is set to avoid "Invalid fields: Request Letter" view error.
        # The view has required="is_special" on request_letter. If no attachment exists,
        # set a placeholder binary so the constraint is satisfied.
        if self.reservation_id and not self.reservation_id.request_letter:
            if self.reservation_id.special_attachment_ids:
                self.reservation_id.sudo().write({
                    'request_letter': self.reservation_id.special_attachment_ids[0].datas
                })
            elif self.attachment:
                self.reservation_id.sudo().write({'request_letter': self.attachment})
            elif self.attachment_ids:
                first = self.attachment_ids[0]
                self.reservation_id.sudo().write({'request_letter': first.datas})

        # Run parent — creates config, sets state=approved, recalculates expire_date, notifies
        # Receipt records remain as draft in receipt_dashboard for normal approval flow
        return super().action_final_approve()
