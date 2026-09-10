from odoo import models, api
from odoo.exceptions import ValidationError
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api

class PropertyReservationHistory(models.Model):
    _inherit = 'property.reservation'

    is_special_reservation = fields.Boolean(
        string="Is Special Reservation",
        default=False,
        # ir reservation_type_id == regular it should be false
        
        help="Check if this is a special reservation."
    )
    make_special_reservation = fields.Boolean(
        string="Make Special Reservation",
        default=False,
        help="Check to make this reservation a special reservation."
    )


    
    audio_filename = fields.Char(string="Audio Filename")
    audio_file = fields.Binary(string="Audio File")

    manager_response_recording = fields.Binary(string="Manager Voice Response")
    manager_response_recording_filename = fields.Char(string="Manager Response Filename")
    manager_attachment = fields.Binary(string="Manager Attachment")
    


    state = fields.Selection([
    ('draft', 'Draft'),
    ('submitted', 'Submitted'),
    ('supervisor', 'Supervisor Approval'),
    ('manager', 'Manager Approval'),
    ('ceo', 'CEO Approval'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
    ('sent', 'Sent'),  # If you still need it for legacy reasons
], string="State", default="draft", tracking=True)

    special_reason = fields.Text(string="Special Reason")
    special_amount = fields.Float(string="Special Amount")
    special_duration = fields.Integer(string="Special Duration (months)")
    special_voice_recording = fields.Binary(string="Special Voice Recording")
    special_attachment = fields.Binary(string="Special Attachment")


    manager_response = fields.Text("Manager Response")
    # manager_response_recording = fields.Binary("Manager Voice Response")
    # manager_attachment = fields.Binary("Manager Attachment")

    # Signature fields for approval workflow
    supervisor_signature = fields.Binary(string="Supervisor Signature")
    supervisor_signature_date = fields.Datetime(string="Supervisor Signature Date")
    manager_signature = fields.Binary(string="Manager Signature")
    manager_signature_date = fields.Datetime(string="Manager Signature Date")
    ceo_signature = fields.Binary(string="CEO Signature")
    ceo_signature_date = fields.Datetime(string="CEO Signature Date")

    # @api.onchange('reservation_type_id')
    # def _onchange_reservation_type_id(self):
    #     if self.reservation_type_id == 'regular':
    #         self.is_special_reservation = False


    is_special_reservation_invisible = fields.Boolean(
    compute="_compute_is_special_reservation_invisible",
    string="Hide Special Reservation Field",
    store=False
)

    @api.depends('reservation_type_id')
    def _compute_is_special_reservation_invisible(self):
        for rec in self:
            rec.is_special_reservation_invisible = (
                rec.reservation_type_id and rec.reservation_type_id.reservation_type == 'regular'
            )

    @api.model
    def get_supervisor_salespersons(self):
        user = self.env.user
        records = self.search([('supervisor_id', '=', user.id)])
        return records
    

    @api.onchange('reservation_type_id')
    def _onchange_reservation_type_id(self):
        if self.reservation_type_id and self.reservation_type_id.reservation_type == 'regular':
            self.is_special_reservation = False

    @api.onchange('is_special_reservation')
    def _onchange_is_special_reservation(self):
        if self.is_special_reservation:
            quick_type = self.env['property.reservation.configuration'].search([('reservation_type', '=', 'quick')], limit=1)
            if quick_type:
                self.reservation_type_id = quick_type.id


    def action_view_special_approval(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Special Approval Form',
            'res_model': 'special.approval.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_reservation_id': self.id,
                'default_reason': self.special_reason,
                'default_manager_response': self.manager_response,
                'default_amount': self.special_amount,
                'default_duration': self.special_duration,
                'default_voice_recording': self.special_voice_recording,
                'default_manager_response_recording': self.manager_response_recording,
                'default_attachment': self.special_attachment,
            }
        }




class SpecialApprovalWizard(models.Model):


    _name = 'special.approval.wizard'
    _description = 'Special Reservation Approval Request'

    reservation_id = fields.Many2one('property.reservation', string="Reservation", required=True)
    reason = fields.Text(string="Reason for Special Request", required=True)
    amount = fields.Float(string="Amount")
    duration = fields.Integer(string="Duration (months)")
    # h
    duration_in = fields.Selection([
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
    ], string='Duration In', default='days')
    voice_recording = fields.Binary(string="Voice Recording")


    audio_file = fields.Binary(related='reservation_id.audio_file', string="Audio File", readonly=False)
    audio_filename = fields.Char(related='reservation_id.audio_filename', string="Audio Filename", readonly=False)
    manager_response_recording = fields.Binary(
    related='reservation_id.manager_response_recording',
    string="Manager Voice Response",
    readonly=False
)
    manager_response_recording_filename = fields.Char(related='reservation_id.manager_response_recording_filename', string="Manager Response Filename", readonly=False)
    manager_attachment = fields.Binary(
    related='reservation_id.manager_attachment',
    string="Manager Attachment",
    readonly=False
)

    attachment = fields.Binary(string="Attachment")

    # manager_response = fields.Text(string="Manager Response")
    manager_response = fields.Text(related='reservation_id.manager_response', string="Manager Response", readonly=False)
    # manager_response_recording = fields.Binary(string="Manager Voice Response")
    manager_attachment = fields.Binary(string="Manager Attachment")

 
    date = fields.Datetime(string="Date", default=fields.Datetime.now)
    phone = fields.Char(string="Phone")
    requester_name = fields.Char(string="Requested By", readonly=True)
    requester_signature = fields.Binary(string="Requested By Signature")

    # manager_signature = fields.Binary(string="Manager Signature")
    manager_approval_date = fields.Datetime(string="Manager Approval Date")

    supervisor_signature = fields.Binary(related='reservation_id.supervisor_signature', string="Supervisor Signature")
    supervisor_signature_date = fields.Datetime(related='reservation_id.supervisor_signature_date', string="Supervisor Signature Date")
    manager_signature = fields.Binary(related='reservation_id.manager_signature', string="Manager Signature", )
    manager_signature_date = fields.Datetime(related='reservation_id.manager_signature_date', string="Manager Signature Date")
    ceo_signature = fields.Binary(related='reservation_id.ceo_signature', string="CEO Signature", )
    ceo_signature_date = fields.Datetime(related='reservation_id.ceo_signature_date', string="CEO Signature Date")



    reservation_salespersons = fields.Char(string="Requested By", compute="_compute_reservation_salespersons", store=False)

    def _compute_reservation_salespersons(self):
        for wizard in self:
            if wizard.reservation_id and wizard.reservation_id.salesperson_ids:
                names = ', '.join(wizard.reservation_id.salesperson_ids.mapped('name'))
                wizard.reservation_salespersons = names
            else:
                wizard.reservation_salespersons = ''

    state_new = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('supervisor', 'Supervisor Approval'),
        ('manager', 'Manager Approval'),
        ('ceo', 'CEO Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string="State", default="draft")

    state = fields.Selection(related='reservation_id.state', string="Status", readonly=True)

    def action_submit(self):
        self.write({'state_new': 'submitted'})
        if self.reservation_id:
            self.reservation_id.write({
                'state': 'submitted',
                'special_reason': self.reason,
                'special_amount': self.amount,
                'special_duration': self.duration,
                # 'special_voice_recording': self.voice_recording,
                'special_attachment': self.attachment,
                'audio_file': self.audio_file,              # <-- add this line
                'audio_filename': self.audio_filename,      # <-- add this line
            })

            print("AUDIO FILE:", self.audio_file)
        return {'type': 'ir.actions.act_window_close'}

    def action_supervisor_approve(self):
        self.write({'state_new': 'supervisor'})
        if self.reservation_id:
            vals = {
                'state': 'supervisor',
                'special_reason': self.reason,
                'special_amount': self.amount,
                'special_duration': self.duration,
                'special_voice_recording': self.voice_recording,
                'special_attachment': self.attachment,
                'manager_response': self.manager_response,
            }
  
            self.reservation_id.write(vals)
        return {'type': 'ir.actions.act_window_close'}



    def action_manager_approve(self):
        if self.reservation_id:
            vals = {
                'state': 'ceo',
                'manager_response': self.manager_response,
                'manager_response_recording': self.manager_response_recording,
                'manager_attachment': self.manager_attachment,
                'supervisor_signature': self.supervisor_signature,
                'supervisor_signature_date': self.supervisor_signature_date,
                'manager_signature': self.manager_signature,
                'manager_signature_date': self.manager_signature_date,
                'ceo_signature': self.ceo_signature,
                'ceo_signature_date': self.ceo_signature_date,
            }
            self.reservation_id.write({k: v for k, v in vals.items() if v})
            self.write({'state_new': 'ceo'})
        return {'type': 'ir.actions.act_window_close'}



    def action_return_to_draft(self):
        if self.reservation_id:
            self.reservation_id.write({'state': 'draft'})
            self.state_new = 'draft'

        return {'type': 'ir.actions.act_window_close'}

    def action_reject(self):
        if self.reservation_id:
            self.reservation_id.write({'state': 'rejected'})
            self.state = 'rejected'
        return {'type': 'ir.actions.act_window_close'}

    # def action_reject(self):
    #     if self.reservation_id:
    #         # Set the reservation's status and state
    #         self.reservation_id.write({'status': 'canceled', 'state': 'rejected'})
    #         self.state = 'rejected'
    #         # Set the related property to available
    #         if self.reservation_id.property_id:
    #             self.reservation_id.property_id.sudo().write({'state': 'available'})
    #     return {'type': 'ir.actions.act_window_close'}

    # def action_reject(self):
    #     if self.reservation_id:
    #         # Call the cancel_reservation method if it exists
    #         if hasattr(self.reservation_id, 'action_cancel_reservation'):
    #             self.reservation_id.cancel_reservation()
    #         else:
    #             self.reservation_id.write({'state': 'rejected'})
    #         self.state = 'rejected'
    #     return {'type': 'ir.actions.act_window_close'}







    def action_final_approve(self):
        if not self.amount or self.amount == 0:
            self.amount = 1
        if self.reservation_id and self.reservation_id.status != 'reserved':
            raise ValidationError(_("You can only finalize approval if the reservation status is 'reserved'. The current status is '%s'.") % (self.reservation_id.status or 'N/A'))
        config = self.env['property.reservation.configuration'].create({
            'name': f"Special Approval for {self.reservation_id.property_id.name or 'Reservation'}",
            'reservation_type': 'special',
            'amount': self.amount,
            'duration': self.duration,
            'is_payment_required': True,
            'one_time_use': True,
            'is_used_use': False,
            'used_by_id': self.reservation_id.salesperson_ids.id if self.reservation_id.salesperson_ids else False,
            'payment_type': 'fixed',
            'duration_in': self.duration_in,  # Use the selected unit
        })
        if self.reservation_id:
            vals = {
                'state': 'approved',
                'reservation_type_id': config.id,
                'manager_response': self.manager_response,
                'manager_response_recording': self.manager_response_recording,
                'manager_attachment': self.manager_attachment,
                'supervisor_signature': self.supervisor_signature,
                'supervisor_signature_date': self.supervisor_signature_date,
                'manager_signature': self.manager_signature,
                'manager_signature_date': self.manager_signature_date,
                'ceo_signature': self.ceo_signature,
                'ceo_signature_date': self.ceo_signature_date,
                'manager_response_recording': self.manager_response_recording,
                'manager_response_recording_filename': self.manager_response_recording_filename,
                'manager_attachment': self.manager_attachment,
            }
            self.reservation_id.write({k: v for k, v in vals.items() if v})
            # Add duration to expire_date if payment_diff is covered
            if self.amount >= self.reservation_id.payment_diff:
                expire_date = self.reservation_id.expire_date or fields.Datetime.now()
                expire_date_dt = fields.Datetime.to_datetime(expire_date)
                duration = self.duration or 0
                # Add the correct time unit
                if self.duration_in == 'minutes':
                    new_expire_date = expire_date_dt + timedelta(minutes=duration)
                elif self.duration_in == 'hours':
                    new_expire_date = expire_date_dt + timedelta(hours=duration)
                elif self.duration_in == 'days':
                    new_expire_date = expire_date_dt + timedelta(days=duration)
                elif self.duration_in == 'weeks':
                    new_expire_date = expire_date_dt + timedelta(weeks=duration)
                elif self.duration_in == 'months':
                    new_expire_date = expire_date_dt + relativedelta(months=duration)
                else:
                    new_expire_date = expire_date_dt  # fallback, no change
                self.reservation_id.write({'expire_date': fields.Datetime.to_string(new_expire_date)})


    def action_download_pdf(self):
        """
        Download the PDF for the current wizard record using a QWeb report.
        """
        self.ensure_one()
        report = self.env['ir.actions.report']._get_report_from_name('special_reservation.report_special_approval_wizard_pdf')
        print ("Report Action:", report)
        return report.report_action(self)

class ApprovedSpecialReservation(models.Model):
    _name = 'approved.special.reservation'
    _description = 'Approved Special Reservation'

    reservation_id = fields.Many2one('property.reservation', string="Reservation", required=True)
    reason = fields.Text(string="Reason")
    amount = fields.Float(string="Amount")
    duration = fields.Integer(string="Duration (months)")
    voice_recording = fields.Binary(string="Voice Recording")
    attachment = fields.Binary(string="Attachment")


from odoo import models, fields, api



from odoo import models, fields, api

class PropertyReservationHistory(models.Model):
    _inherit = 'property.reservation'

    def action_request_special_approval(self):
        # Set reservation as reserved and property as reserved
        self.write({'status': 'reserved'})
        if self.property_id:
            self.property_id.sudo().write({'state': 'reserved'})
        self.make_special_reservation = True
        return {
            'type': 'ir.actions.act_window',
            'name': 'Request Special Approval',
            'res_model': 'special.approval.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_reservation_id': self.id,
                'default_requester_name': self.env.user.name,
            }
        }


