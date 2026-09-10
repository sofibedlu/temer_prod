import logging
import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.addons.crm_quota_lead_distribution.models.lead_afromessage_sms import (
    send_sms_afromessage,
)

_logger = logging.getLogger(__name__)


class CollectionOrder(models.Model):
    _inherit = 'collection.order'

    collection_reservation_count = fields.Integer(
        string='Collection Reservations',
        compute='_compute_collection_reservation_count',
    )

    def _get_collection_reservations(self):
        self.ensure_one()
        requests = self.env['collection.reservation.request'].sudo().search([
            ('collection_id', '=', self.id),
            ('reservation_id', '!=', False),
        ])
        return requests.mapped('reservation_id')

    def _compute_collection_reservation_count(self):
        for order in self:
            if not self.env.user.has_group(
                'collection_reservation.group_collection_reservation_user'
            ) and not self.env.user.has_group(
                'collection_reservation.group_collection_reservation_checker'
            ) and not self.env.user.has_group(
                'collection_reservation.group_collection_reservation_approver'
            ):
                order.collection_reservation_count = 0
                continue
            order.collection_reservation_count = len(
                order._get_collection_reservations()
            )

    def _get_collection_reservation_request_context(self):
        self.ensure_one()
        context = {
            'default_collection_id': self.id,
            'default_partner_id': self.partner_id.id,
            'default_site_id': self.site_id.id,
        }
        if self.property_id and self.property_id.state == 'available':
            context['default_property_id'] = self.property_id.id
        sale = self.sale_id
        if sale and 'sales_person' in sale._fields and sale.sales_person:
            context['default_supervisor_id'] = sale.sales_person.id
        return context

    def action_open_collection_reservation_request(self):
        self.ensure_one()
        if not self.env.user.has_group(
            'collection_reservation.group_collection_reservation_user'
        ):
            raise ValidationError(
                _('Only collection reservation users can create requests.')
            )
        return {
            'name': _('Collection Reservation'),
            'type': 'ir.actions.act_window',
            'res_model': 'collection.reservation.request',
            'view_mode': 'form',
            'views': [(
                self.env.ref(
                    'collection_reservation.view_collection_reservation_request_form_create'
                ).id,
                'form',
            )],
            'target': 'new',
            'context': self._get_collection_reservation_request_context(),
        }

    def action_view_collection_reservations(self):
        self.ensure_one()
        reservations = self._get_collection_reservations()
        if not reservations:
            raise ValidationError(_('No collection reservation has been created yet.'))
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Reservation'),
            'res_model': 'property.reservation',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', reservations.ids)],
            'target': 'current',
        }
        if len(reservations) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': reservations.id,
            })
        return action


class PropertyReservationConfiguration(models.Model):
    _inherit = 'property.reservation.configuration'

    reservation_type = fields.Selection(
        selection_add=[('collection', 'Collection')],
        ondelete={'collection': 'set default'},
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reservation_type') == 'collection':
                vals.update(self._collection_reservation_type_vals(vals))
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('reservation_type') == 'collection':
            vals = dict(vals)
            vals.update(self._collection_reservation_type_vals(vals))
            return super().write(vals)
        if 'reservation_type' not in vals:
            collection_records = self.filtered(
                lambda rec: rec.reservation_type == 'collection'
            )
            other_records = self - collection_records
            result = True
            if other_records:
                result = super(
                    PropertyReservationConfiguration,
                    other_records,
                ).write(vals)
            if collection_records:
                collection_vals = dict(vals)
                collection_vals.update(
                    self._collection_reservation_type_vals(collection_vals)
                )
                result = super(
                    PropertyReservationConfiguration,
                    collection_records,
                ).write(collection_vals) and result
            return result
        return super().write(vals)

    def _collection_reservation_type_vals(self, vals):
        result = {
            'payment_type': vals.get('payment_type') or 'fixed',
            'amount': 0.0,
            'is_payment_required': False,
        }
        if 'duration' not in vals:
            result['duration'] = 0
        if 'duration_in' not in vals:
            result['duration_in'] = 'days'
        return result

    @api.constrains('amount', 'duration', 'is_payment_required', 'reservation_type')
    def _validate_amounts(self):
        for rec in self:
            if rec.reservation_type == 'collection':
                if rec.is_payment_required:
                    raise ValidationError(
                        _('Collection reservation type cannot require payment.')
                    )
                continue
            if rec.amount <= 0 and rec.is_payment_required:
                raise ValidationError(_('Amount must be positive and not zero'))
            if rec.duration <= 0:
                raise ValidationError(_('Duration must be positive and not zero'))


class PropertyReservation(models.Model):
    _inherit = 'property.reservation'

    is_collection_reservation = fields.Boolean(
        string='Collection Reservation',
        default=False,
        copy=False,
        index=True,
    )
    collection_reservation_request_id = fields.Many2one(
        'collection.reservation.request',
        string='Collection Reservation Request',
        copy=False,
    )

    @api.depends('is_collection_reservation')
    def _compute_show_payment_tab(self):
        super()._compute_show_payment_tab()
        for rec in self:
            if rec.is_collection_reservation:
                rec.show_payment_tab = True

    def get_expire_date(self, reservation_type_id):
        reservation_type = self.env['property.reservation.configuration'].browse(
            reservation_type_id
        )
        if reservation_type.reservation_type == 'collection':
            return False
        return super().get_expire_date(reservation_type_id)


class CollectionReservationRequest(models.Model):
    _name = 'collection.reservation.request'
    _description = 'Collection Reservation Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(
        string='Reference',
        required=True,
        readonly=True,
        default='New',
        copy=False,
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('checked', 'Checked'),
            ('approved', 'Approved'),
        ],
        string='Status',
        default='draft',
        readonly=True,
        tracking=True,
    )
    date = fields.Datetime(
        string='Date',
        default=fields.Datetime.now,
        readonly=True,
    )
    collection_id = fields.Many2one(
        'collection.order',
        string='Collection Order',
        required=True,
        readonly=True,
    )
    site_id = fields.Many2one(
        'property.site',
        string='Site',
        required=True,
        tracking=True,
    )
    property_id = fields.Many2one(
        'property.property',
        string='Property',
        required=True,
        domain="[('site', '=', site_id), ('state', '=', 'available')]",
        tracking=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        tracking=True,
    )
    reservation_type_id = fields.Many2one(
        'property.reservation.configuration',
        string='Reservation Type',
        required=True,
        domain=[('is_used_use', '!=', True)],
        default=lambda self: self._default_collection_reservation_type_id(),
        tracking=True,
    )
    end_date = fields.Datetime(
        string='End Time',
        tracking=True,
        help='If set, this value becomes the reservation end date.',
    )
    supervisor_id = fields.Many2one(
        'res.users',
        string='Salesperson',
        readonly=True,
        tracking=True,
    )
    checked_by_id = fields.Many2one(
        'res.users',
        string='Checked By',
        readonly=True,
        copy=False,
    )
    checked_date = fields.Datetime(
        string='Checked On',
        readonly=True,
        copy=False,
    )
    approved_by_id = fields.Many2one(
        'res.users',
        string='Approved By',
        readonly=True,
        copy=False,
    )
    approved_date = fields.Datetime(
        string='Approved On',
        readonly=True,
        copy=False,
    )
    reservation_id = fields.Many2one(
        'property.reservation',
        string='Reservation',
        readonly=True,
        copy=False,
    )
    reservation_count = fields.Integer(
        string='Reservation Count',
        compute='_compute_reservation_count',
    )
    note = fields.Text(string='Note')

    @api.model
    def _get_vals_from_collection_order(self, collection):
        vals = {
            'collection_id': collection.id,
            'partner_id': collection.partner_id.id,
            'site_id': collection.site_id.id,
        }
        if (
            collection.property_id
            and collection.property_id.state == 'available'
        ):
            vals['property_id'] = collection.property_id.id
        sale = collection.sale_id
        if sale and 'sales_person' in sale._fields and sale.sales_person:
            vals['supervisor_id'] = sale.sales_person.id
        return vals

    def _get_salesperson_from_collection_order(self):
        self.ensure_one()
        collection = self.collection_id
        if not collection or not collection.sale_id:
            return False
        sale = collection.sale_id
        if 'sales_person' in sale._fields and sale.sales_person:
            return sale.sales_person
        return False

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.user.has_group(
            'collection_reservation.group_collection_reservation_user'
        ):
            raise ValidationError(
                _('Only collection reservation users can create requests.')
            )
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code(
                        'collection.reservation.request'
                    )
                    or 'New'
                )
            collection_id = vals.get(
                'collection_id',
                self.env.context.get('default_collection_id'),
            )
            if not collection_id:
                raise ValidationError(
                    _('Collection reservation requests must be created from a collection order.')
                )
            collection = self.env['collection.order'].browse(collection_id)
            if not collection.exists():
                raise ValidationError(_('The linked collection order does not exist.'))
            for key, value in self._get_vals_from_collection_order(collection).items():
                vals.setdefault(key, value)
        records = super().create(vals_list)
        for record in records:
            record._log_collection_reservation_event(_('Collection reservation request created'))
            record._notify_checkers_new_request()
        return records

    @api.model
    def _default_collection_reservation_type_id(self):
        reservation_type = self.env.ref(
            'collection_reservation.property_reservation_collection',
            raise_if_not_found=False,
        )
        return reservation_type.id if reservation_type else False

    def _compute_reservation_count(self):
        for request in self:
            request.reservation_count = 1 if request.reservation_id else 0

    def _format_collection_reservation_log_details(self):
        self.ensure_one()
        details = [
            _('Request: %s') % self.name,
            _('Customer: %s') % (self.partner_id.display_name or ''),
            _('Property: %s') % (self.property_id.display_name or ''),
        ]
        if self.collection_id:
            details.append(
                _('Collection Order: %s') % self.collection_id.display_name
            )
        return '\n'.join(details)

    def _log_collection_reservation_event(self, title):
        self.ensure_one()
        body = '%s\n%s' % (title, self._format_collection_reservation_log_details())
        self.message_post(body=body)
        if self.collection_id:
            self.collection_id.message_post(body=body)

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        collection_id = self.env.context.get('default_collection_id')
        if not collection_id:
            return vals
        collection = self.env['collection.order'].browse(collection_id)
        if collection.exists():
            vals.update(self._get_vals_from_collection_order(collection))
        return vals

    @api.onchange('site_id')
    def _onchange_site_id(self):
        if self.property_id and self.property_id.site != self.site_id:
            self.property_id = False

    @api.onchange('property_id')
    def _onchange_property_id(self):
        if self.property_id:
            self.site_id = self.property_id.site

    @api.constrains('end_date')
    def _check_end_date(self):
        for request in self:
            if request.end_date and request.end_date <= fields.Datetime.now():
                raise ValidationError(_('End time must be in the future.'))

    def _validate_can_create_reservation(self):
        self.ensure_one()
        if self.reservation_id:
            raise ValidationError(_('A reservation was already created.'))
        if not self.property_id:
            raise ValidationError(_('Please select a property.'))
        if self.property_id.state != 'available':
            raise ValidationError(
                _('Only available properties can be reserved. Please select an available property.')
            )
        if not self.reservation_type_id:
            raise ValidationError(_('Please select a reservation type.'))

    def _reserve_direct(self, reservation):
        if reservation.property_id.state != 'available':
            raise ValidationError(
                _('Cannot reserve. Property %s is in %s state.') % (
                    reservation.property_id.name,
                    reservation.property_id.state,
                )
            )
        reservation.property_id.sudo().write({'state': 'reserved'})
        reservation.sudo().write({'status': 'reserved'})
        if 'crm_lead_id' in reservation._fields and reservation.crm_lead_id:
            reservation.crm_lead_id.action_set_reserved()

    def _open_reservation_action(self, reservation):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reservation'),
            'res_model': 'property.reservation',
            'view_mode': 'form',
            'res_id': reservation.id,
            'target': 'current',
        }

    @api.model
    def _normalize_sms_number(self, raw):
        if not raw:
            return None
        value = str(raw).strip()
        if not value or '@' in value:
            return None
        digits = re.sub(r'\D', '', value)
        if len(digits) < 9:
            return None
        if digits.startswith('251') and len(digits) > 9:
            digits = digits[3:]
        if digits.startswith('0') and len(digits) > 9:
            digits = digits[1:]
        return digits if len(digits) >= 9 else None

    def _get_checker_users(self):
        group = self.env.ref(
            'collection_reservation.group_collection_reservation_checker',
            raise_if_not_found=False,
        )
        if not group:
            return self.env['res.users']
        return group.users.filtered(lambda user: user.active)

    def _checker_sms_message(self):
        self.ensure_one()
        if self.collection_id:
            return _(
                'New collection reservation is created for customer %(customer)s. '
                'Collection Order: %(collection)s. Property: %(property)s. '
                'Request %(request)s waits your check.'
            ) % {
                'customer': self.partner_id.display_name or '-',
                'collection': self.collection_id.display_name or '-',
                'property': self.property_id.display_name or '-',
                'request': self.name,
            }
        return _(
            'New collection reservation is created for customer %(customer)s. '
            'Property: %(property)s. Request %(request)s waits your check.'
        ) % {
            'customer': self.partner_id.display_name or '-',
            'property': self.property_id.display_name or '-',
            'request': self.name,
        }

    def _notify_checkers_new_request(self):
        self.ensure_one()
        message = self._checker_sms_message()
        for checker in self._get_checker_users():
            mobile = self._normalize_sms_number(checker.login)
            if not mobile:
                _logger.info(
                    'Collection reservation: skip SMS for checker %s (no valid login phone)',
                    checker.display_name,
                )
                continue
            success, result = send_sms_afromessage(mobile, message, env=self.env)
            if success:
                _logger.info(
                    'Collection reservation: SMS sent to checker %s (%s)',
                    checker.display_name,
                    mobile,
                )
            else:
                _logger.warning(
                    'Collection reservation: SMS failed for checker %s (%s): %s',
                    checker.display_name,
                    mobile,
                    result,
                )

    def _create_reservation(self):
        self.ensure_one()
        self._validate_can_create_reservation()
        salesperson = self._get_salesperson_from_collection_order()
        if not salesperson:
            raise ValidationError(
                _('The collection order sale has no salesperson assigned.')
            )
        reservation = self.env['property.reservation'].sudo().create({
            'property_id': self.property_id.id,
            'partner_id': self.partner_id.id,
            'reservation_type_id': self.reservation_type_id.id,
            'salesperson_ids': salesperson.id,
            'is_collection_reservation': True,
            'collection_reservation_request_id': self.id,
        })
        if self.end_date:
            reservation.sudo().write({'expire_date': self.end_date})
        self._reserve_direct(reservation)
        self.write({'reservation_id': reservation.id})
        reservation.message_post(
            body='%s\n%s' % (
                _('Collection reservation created'),
                self._format_collection_reservation_log_details(),
            ),
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
        )
        return reservation

    def action_check(self):
        self.ensure_one()
        if not self.env.user.has_group(
            'collection_reservation.group_collection_reservation_checker'
        ):
            raise ValidationError(_('Only collection reservation checkers can check.'))
        if self.state != 'draft':
            raise ValidationError(_('Only draft requests can be checked.'))
        reservation = self._create_reservation()
        self.write({
            'state': 'checked',
            'checked_by_id': self.env.user.id,
            'checked_date': fields.Datetime.now(),
        })
        self._log_collection_reservation_event(
            _('Collection reservation request checked by %s') % self.env.user.display_name
        )
        return self._open_reservation_action(reservation)

    def action_approve(self):
        self.ensure_one()
        if not self.env.user.has_group(
            'collection_reservation.group_collection_reservation_approver'
        ):
            raise ValidationError(_('Only collection reservation approvers can approve.'))
        if self.state != 'checked':
            raise ValidationError(_('Only checked requests can be approved.'))
        if not self.reservation_id:
            raise ValidationError(_('No reservation has been created yet.'))
        self.write({
            'state': 'approved',
            'approved_by_id': self.env.user.id,
            'approved_date': fields.Datetime.now(),
        })
        self._log_collection_reservation_event(
            _('Collection reservation approved by %s') % self.env.user.display_name
        )
        return True

    def action_view_reservation(self):
        self.ensure_one()
        if not self.reservation_id:
            raise ValidationError(_('No reservation has been created yet.'))
        return self._open_reservation_action(self.reservation_id)
