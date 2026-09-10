# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class AttendanceLog(models.Model):
    _name = 'attendance.log'
    _description = 'attendance log'
    _order = 'punching_time'
    _rec_name = 'punching_time'

    employee_id = fields.Many2one('hr.employee', string='Employee')
    status = fields.Selection([('0', 'Check In'),
                               ('1', 'Check Out'),
                               ('2', 'Punched')], string='Status')
    punching_time = fields.Datetime('Punching Time')
    is_calculated = fields.Boolean('Calculated', default=False)
    device = fields.Char('Device')
    company_id = fields.Many2one('res.company', string='Company', readonly=True, default=lambda self: self.env.company)

    def unlink(self):
        if any(self.filtered(lambda log: log.is_calculated == True)):
            raise UserError(_('You cannot delete a Record which is already Calculated !!!'))
        return super(AttendanceLog, self).unlink()

class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    in_out_diff = fields.Float('Difference', compute='_compute_in_out_difference')

    @api.depends('check_in', 'check_out')
    def _compute_in_out_difference(self):
        for attendance in self:
            if attendance.check_in and attendance.check_out:
                diff = attendance.check_out - attendance.check_in
                attendance.in_out_diff = diff.total_seconds() / 3600.0
            else:
                attendance.in_out_diff = 0

    def unlink(self):
        for record in self:
            domain = [('employee_id', '=', record.employee_id.id), '|',
                      ('punching_time', '=', record.check_in),
                      ('punching_time', '=', record.check_out)]
            attend_obj = self.env['attendance.log'].search(domain)
            for log in attend_obj:
                log.is_calculated = False
        return super(HrAttendance, self).unlink()