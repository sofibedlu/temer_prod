from odoo import fields, models

class HrAttendancePeriod(models.Model):
    _name = 'hr.attendance.period'
    _description = 'HR Attendance Period'
    _order = 'start_date desc'

    name = fields.Char(string='Description', required=True)
    start_date = fields.Datetime(string='Start Date', required=True)
    end_date = fields.Datetime(string='End Date', required=True)