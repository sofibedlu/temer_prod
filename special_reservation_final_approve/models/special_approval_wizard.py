# -*- coding: utf-8 -*-
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from markupsafe import Markup
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class SpecialApprovalWizard(models.Model):
    _inherit = 'special.approval.wizard'

    # Multiple attachments — linked to reservation so they persist across wizard sessions
    attachment_ids = fields.Many2many(
        'ir.attachment',
        related='reservation_id.special_attachment_ids',
        string='Attachments',
        readonly=False,
    )

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _get_admin_users(self):
        """Return all admin (superuser) users."""
        return self.env['res.users'].sudo().search([
            ('active', '=', True),
            ('share', '=', False),
            ('groups_id', 'in', [self.env.ref('base.group_system').id]),
        ])

    def _get_ceo_users(self):
        """Return all users in the special_reservation.group_ceo group."""
        try:
            group = self.env.ref('special_reservation.group_ceo')
            return group.users.filtered(lambda u: u.active)
        except Exception:
            return self.env['res.users'].sudo().browse()

    def _get_sales_hierarchy(self, salesperson_user):
        """
        Given a salesperson res.users record, return a dict with:
          supervisor_user  – res.users of their supervisor (or empty recordset)
          sales_manager    – res.users of the sales manager  (or empty recordset)
          wing_manager     – res.users of the wing manager   (or empty recordset)
        """
        empty = self.env['res.users'].sudo().browse()
        if not salesperson_user:
            return {'supervisor_user': empty, 'sales_manager': empty, 'wing_manager': empty}

        mapping = self.env['property.salesperson.mapping'].sudo().search(
            [('user_id', '=', salesperson_user.id)], limit=1
        )
        if not mapping:
            return {'supervisor_user': empty, 'sales_manager': empty, 'wing_manager': empty}

        supervisor_rec = mapping.supervisor_id
        supervisor_user = supervisor_rec.name if supervisor_rec else empty

        team = supervisor_rec.sales_team_id if supervisor_rec else False
        sales_manager = team.manager_id if team else empty

        wing = team.wing_id if team else False
        wing_manager = wing.manager_id if wing else empty

        return {
            'supervisor_user': supervisor_user,
            'sales_manager': sales_manager,
            'wing_manager': wing_manager,
        }

    def _notify_users(self, users, subject, body):
        """
        Send inbox/push notification to specific users via message_notify.
        This triggers the Odoo inbox bell and FCM push — without broadcasting
        to all followers via message_post.
        """
        users = users.sudo().filtered(lambda u: u.active and u.partner_id)
        reservation = self.reservation_id
        if not users or not reservation:
            return

        partner_ids = users.mapped('partner_id').ids

        try:
            reservation.sudo().message_notify(
                partner_ids=partner_ids,
                subject=subject,
                body=Markup('<p>%s</p>') % body,
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
            )
        except Exception as e:
            _logger.error('_notify_users: failed: %s', e)


    # -------------------------------------------------------------------------
    # Override: action_submit → set request_letter + notify all supervisors
    # -------------------------------------------------------------------------

    def action_submit(self):
        # Set request_letter on reservation from attachment before calling super
        # This prevents the "Invalid fields: Request Letter" view validation error
        if self.reservation_id and not self.reservation_id.request_letter:
            # Try attachment_ids (new multi-attachment field) first
            if self.reservation_id.special_attachment_ids:
                first_attach = self.reservation_id.special_attachment_ids[0]
                self.reservation_id.sudo().write({'request_letter': first_attach.datas})
            elif self.attachment:
                self.reservation_id.sudo().write({'request_letter': self.attachment})

        res = super().action_submit()
        try:
            reservation = self.reservation_id
            salesperson = reservation.salesperson_ids
            hierarchy = self._get_sales_hierarchy(salesperson)
            supervisor_user = hierarchy['supervisor_user']

            property_name = reservation.property_id.name or ''
            salesperson_name = salesperson.name if salesperson else ''
            subject = _('New Special Reservation Request')
            body = _('Special reservation %s needs supervisor approval.') % property_name

            if supervisor_user:
                self._notify_users(supervisor_user, subject, body)
            # Admin sees all notifications
            admin_users = self._get_admin_users()
            if admin_users:
                self._notify_users(admin_users, subject, body)
        except Exception as e:
            _logger.warning('Submit notification failed: %s', e)
        return res

    # -------------------------------------------------------------------------
    # Override: action_supervisor_approve → notify salesperson + hierarchy
    # -------------------------------------------------------------------------

    def action_supervisor_approve(self):
        res = super().action_supervisor_approve()
        try:
            reservation = self.reservation_id
            salesperson = reservation.salesperson_ids
            hierarchy = self._get_sales_hierarchy(salesperson)
            property_name = reservation.property_id.name or ''
            subject = _('Special Reservation: Supervisor Approved')
            body = _('Special reservation for %s approved by supervisor.') % property_name

            recipients = self.env['res.users'].sudo().browse()
            if salesperson:
                recipients |= salesperson
            if hierarchy['supervisor_user']:
                recipients |= hierarchy['supervisor_user']
            if hierarchy['sales_manager']:
                recipients |= hierarchy['sales_manager']
            if hierarchy['wing_manager']:
                recipients |= hierarchy['wing_manager']

            self._notify_users(recipients, subject, body)
            # Admin sees all notifications
            admin_users = self._get_admin_users()
            if admin_users:
                self._notify_users(admin_users, subject, body)
        except Exception as e:
            _logger.warning('Supervisor approve notification failed: %s', e)
        return res

    # -------------------------------------------------------------------------
    # Override: action_manager_approve → notify ALL CEO group users
    # -------------------------------------------------------------------------

    def action_manager_approve(self):
        res = super().action_manager_approve()
        try:
            reservation = self.reservation_id
            property_name = reservation.property_id.name or ''
            salesperson = reservation.salesperson_ids
            salesperson_name = salesperson.name if salesperson else ''

            ceo_users = self._get_ceo_users()
            subject = _('Special Reservation Needs Your Final Approval')
            body = _('Special reservation %s needs your final approval.') % property_name
            if ceo_users:
                self._notify_users(ceo_users, subject, body)
            # Admin sees all notifications
            admin_users = self._get_admin_users()
            if admin_users:
                self._notify_users(admin_users, subject, body)
        except Exception as e:
            _logger.warning('Manager approve notification failed: %s', e)
        return res

    # -------------------------------------------------------------------------
    # Override: action_final_approve → full logic + notify hierarchy
    # -------------------------------------------------------------------------

    def action_final_approve(self):
        """
        Full override of action_final_approve:
        1. Config name = "{property_name}/{salesperson_name}"
        2. is_payment_required based on amount > 0
        3. expire_date recalculated from duration
        4. Notify salesperson + supervisor + sales manager + wing manager
        """
        self.ensure_one()
        reservation = self.reservation_id

        property_name = reservation.property_id.name or ''
        salesperson_name = reservation.salesperson_ids.name if reservation.salesperson_ids else ''
        config_name = f"{property_name}/{salesperson_name}"

        amount = self.amount or 0.0
        is_payment_required = amount > 0

        config = self.env['property.reservation.configuration'].create({
            'name': config_name,
            'reservation_type': 'special',
            'payment_type': 'fixed',
            'amount': amount,
            'duration_in': self.duration_in or 'days',
            'duration': self.duration or 0,
            'is_payment_required': is_payment_required,
            'one_time_use': True,
            'is_used_use': False,
            'used_by_id': reservation.salesperson_ids.id if reservation.salesperson_ids else False,
        })

        vals = {'state': 'approved', 'reservation_type_id': config.id}
        # Ensure request_letter is set to avoid view validation errors
        if not reservation.request_letter:
            if reservation.special_attachment_ids:
                vals['request_letter'] = reservation.special_attachment_ids[0].datas
            elif self.attachment:
                vals['request_letter'] = self.attachment
        for f in ['manager_response', 'manager_response_recording',
                  'manager_response_recording_filename', 'manager_attachment',
                  'supervisor_signature', 'supervisor_signature_date',
                  'manager_signature', 'manager_signature_date',
                  'ceo_signature', 'ceo_signature_date']:
            v = getattr(self, f, None)
            if v:
                vals[f] = v
        reservation.write(vals)

        # Recalculate expire_date from duration
        duration = self.duration or 0
        duration_in = self.duration_in or 'days'
        if duration > 0:
            base_dt = fields.Datetime.to_datetime(reservation.expire_date or fields.Datetime.now())
            if duration_in == 'minutes':
                new_expire = base_dt + timedelta(minutes=duration)
            elif duration_in == 'hours':
                new_expire = base_dt + timedelta(hours=duration)
            elif duration_in == 'days':
                new_expire = base_dt + timedelta(days=duration)
            elif duration_in == 'weeks':
                new_expire = base_dt + timedelta(weeks=duration)
            elif duration_in == 'months':
                new_expire = base_dt + relativedelta(months=duration)
            else:
                new_expire = base_dt
            reservation.write({'expire_date': fields.Datetime.to_string(new_expire)})

        # Notify salesperson + full hierarchy
        try:
            salesperson = reservation.salesperson_ids
            hierarchy = self._get_sales_hierarchy(salesperson)
            subject = _('Special Reservation Finally Approved')
            body = _('Special reservation %s is approved.') % property_name

            recipients = self.env['res.users'].sudo().browse()
            if salesperson:
                recipients |= salesperson
            if hierarchy['supervisor_user']:
                recipients |= hierarchy['supervisor_user']
            if hierarchy['sales_manager']:
                recipients |= hierarchy['sales_manager']
            if hierarchy['wing_manager']:
                recipients |= hierarchy['wing_manager']

            self._notify_users(recipients, subject, body)
            # Admin sees all notifications
            admin_users = self._get_admin_users()
            if admin_users:
                self._notify_users(admin_users, subject, body)
        except Exception as e:
            _logger.warning('Final approve notification failed: %s', e)
