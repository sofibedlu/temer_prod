from odoo import fields, models

class AttendanceLastRead(models.Model):
    _name = 'attendance.last.read'
    _description = 'Attendance Last Read Tracking'

    machine_id = fields.Many2one('biometric.config', string='Machine ID', required=True, ondelete='cascade')
    last_read_time = fields.Datetime(string='Last Time Read', required=True)