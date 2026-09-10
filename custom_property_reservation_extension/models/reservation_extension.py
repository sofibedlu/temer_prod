# -*- coding: utf-8 -*-
##############################################################################
#    Ahadubit Technologies
#    Copyright (C) 2024-TODAY Ahadubit Technologies(<https://ahadubit.com>).
#    Author: Ahadubit Technologies (<https://ahadubit.com>)
##############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class PropertyReservationExtend(models.Model):
    _name = 'property.reservation.extend.history'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Property Reservation Extension History'
    _rec_name = 'reservation_id'
    _order = 'create_date desc'

    reservation_id = fields.Many2one(
        'property.reservation',
        string="Reservation",
        required=True,
        tracking=True
    )
    reservation_id1 = fields.Many2one(
        'property.reservation',
        string="Reservation",
        tracking=True
    )
    status = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', tracking=True)
    extension_date = fields.Datetime(
        string="Requested Extension Date",
        required=True,
        tracking=True
    )
    old_end_date = fields.Datetime(
        string="Old End Date",
        related="reservation_id.expire_date",
        tracking=True,
        readonly=True
    )
    request_letter_file = fields.Binary(
        string="Request Letter",
        tracking=True,
        required=True
    )
    remark = fields.Text(string="Remark",required=True, tracking=True)

    @api.onchange('extension_date')
    def _check_extension_date(self):
        for record in self:
            if record.extension_date and record.extension_date <= fields.Datetime.now():
                raise ValidationError(_("Extension date must be in the future."))

    @api.model
    def create(self, vals):
        """Create extension request and update reservation status."""
        reservation = self.env['property.reservation'].browse(vals['reservation_id'])

        if not reservation:
            raise ValidationError(_("Invalid reservation reference"))
            
        if reservation.status not in ['reserved']:
            raise ValidationError(_("Can only extend active reservations"))
            
        reservation.sudo().write({'extension_status': 'pending'})
        vals.update({
            'status': 'pending',
            'old_end_date': reservation.expire_date
        })
        return super().create(vals)

    def approve_extension(self):
        for rec in self:
            rec.reservation_id.sudo().write({
                'expire_date':rec.extension_date,
                'extension_status':'approved',
            })
            rec.status='approved'

    def reject_extension(self):
        """Reject the extension request."""
        self.ensure_one()
        if self.status != 'pending':
            raise ValidationError(_("Can only reject pending requests"))
            
        self.reservation_id.sudo().write({'extension_status': 'rejected'})
        self.status = 'rejected'

    def extension_request_detail(self):
        """Show extension request details."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Extension Request'),
            'res_model': self._name,
            'view_mode': 'form,tree',
            'target': 'current',
            'res_id': self.id,
        }