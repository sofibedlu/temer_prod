# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import datetime
import base64
import pytz
import math
from dateutil.relativedelta import relativedelta
import xlsxwriter
import io

class AttendanceReportWizard(models.TransientModel):
    _name = 'attendance.report.wizard'
    _description = 'attendance report wizard'

    report_from = fields.Selection([('attend', 'From Attendance'),
                                    ('log', 'From Log')],
                                   string='Report', required=True, default='attend')
    date_from = fields.Datetime('From', required=True, default=fields.Datetime.now)
    date_to = fields.Datetime('To', required=True, default=fields.Datetime.now)
    is_summery_report = fields.Boolean('Is Summery Report')
    report_file = fields.Binary('File', readonly=True)
    report_name = fields.Char(string='File Name')
    is_printed = fields.Boolean('Printed', default=False)

    @api.onchange('report_from')
    def onchange_report(self):
        day = datetime.today().day
        date_from = datetime.today() + relativedelta(day=day - 1, hour=00, minute=00, second=00)
        date_to = datetime.today() + relativedelta(day=day - 1, hour=23, minute=59, second=59)
        self.date_from = date_from
        self.date_to = date_to

    def export_attendance_xlsx(self, fl=None):
        if fl == None:
            fl = ''
        if self.report_from == 'log':
            domain = [('punching_time', '>=', self.date_from),
                      ('punching_time', '<=', self.date_to)]
            attendance_logs = self.env['attendance.log'].search(domain)
            fl = self.print_attendance_logs(attendance_logs)
        elif self.report_from == 'attend':
            domain = ['|',
                      '&', ('check_in', '>=', self.date_from), ('check_out', '<=', self.date_to),
                      '&', '&', ('check_in', '>=', self.date_from), ('check_in', '<=', self.date_to), ('check_out', '=', False)]
            attendances = self.env['hr.attendance'].search(domain)
            fl = self.print_attendance_records(attendances, self.is_summery_report)

        output = base64.b64encode(fl[1])
        ctx = dict(self.env.context)
        ctx.update({'report_file': output})
        ctx.update({'file': fl[0]})
        self.report_name = fl[0]
        self.report_file = output
        self.is_printed = True

        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'attendance.report.wizard',
            'target': 'new',
            'context': ctx,
            'res_id': self.id,
        }

    def action_back(self):
        self.is_printed = False
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'attendance.report.wizard',
            'target': 'new',
        }

    def print_attendance_records(self, attendances, is_summery):
        date1 = self.new_timezone(self.date_from).date()
        date2 = self.new_timezone(self.date_to).date()
        fl = f"Attendance from {date1.strftime('%d-%B-%Y')} to {date2.strftime('%d-%B-%Y')}.xlsx"
        
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Sheet 1')
        worksheet.set_landscape()

        bold = workbook.add_format({'bold': True, 'border': 1, 'align': 'center'})
        font_left = workbook.add_format({'align': 'left', 'border': 1, 'font_size': 12})
        font_center = workbook.add_format({'align': 'center', 'border': 1, 'valign': 'vcenter', 'font_size': 12})
        font_bold_center = workbook.add_format({'align': 'center', 'border': 1, 'valign': 'vcenter', 'font_size': 12, 'bold': True})
        border = workbook.add_format({'border': 1})

        worksheet.set_column('A:E', 20, border)
        worksheet.set_row(0, 20)
        worksheet.merge_range('A1:E1', "Attendance sheet from " + date1.strftime('%d-%m-%Y') + " to " + date2.strftime('%d-%m-%Y'), bold)

        row = 2
        col = 0
        worksheet.merge_range(row, col, row + 1, col + 1, "Name of Employee", font_bold_center)
        worksheet.merge_range(row, col + 2, row + 1, col + 2, "Check In", font_bold_center)
        worksheet.merge_range(row, col + 3, row + 1, col + 3, "Check_out", font_bold_center)
        worksheet.merge_range(row, col + 4, row + 1, col + 4, "Difference", font_bold_center)

        row += 2
        for attendance in attendances:
            emp_name = attendance.employee_id.name if hasattr(attendance, 'employee_id') else attendance.get('employee_id', '')
            worksheet.merge_range(row, col, row, col + 1, emp_name, font_left)
            
            check_in_val = attendance.check_in if hasattr(attendance, 'check_in') else attendance.get('check_in')
            check_out_val = attendance.check_out if hasattr(attendance, 'check_out') else attendance.get('check_out')
            diff_val = attendance.in_out_diff if hasattr(attendance, 'in_out_diff') else attendance.get('in_out_diff', 0)
            
            if check_in_val:
                check_in = self.convert_timezone(check_in_val)
            else:
                check_in = '***No Check In***'
            worksheet.write(row, col + 2, check_in, font_center)
            
            if check_out_val:
                check_out = self.convert_timezone(check_out_val)
            else:
                check_out = '***No Check Out***'
            worksheet.write(row, col + 3, check_out, font_center)

            factor = diff_val < 0 and -1 or 1
            val = abs(diff_val)
            hour, minute = (factor * int(math.floor(val)), int(round((val % 1) * 60)))
            if minute == 60:
                hour += 1
                minute = 0
            diff = f"{hour:02}:{minute:02}"

            worksheet.write(row, col + 4, diff, font_center)
            row += 1

        workbook.close()
        xlsx_data = output.getvalue()
        return [fl, xlsx_data]

    def convert_timezone(self, time):
        user_tz = self.env.user.tz or str(pytz.utc)
        local = pytz.timezone(user_tz)
        return datetime.strftime(pytz.utc.localize(time, is_dst=None).astimezone(local), "%Y-%m-%d %H:%M:%S")

    def new_timezone(self, time):
        user_tz = self.env.user.tz or str(pytz.utc)
        local = pytz.timezone(user_tz)
        return pytz.utc.localize(time, is_dst=None).astimezone(local)

    def print_attendance_logs(self, logs):
        date1 = self.new_timezone(self.date_from).date()
        date2 = self.new_timezone(self.date_to).date()
        fl = f"Attendance Log from {date1.strftime('%d-%B-%Y')} to {date2.strftime('%d-%B-%Y')}.xlsx"
        
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Sheet 1')
        worksheet.set_landscape()

        bold = workbook.add_format({'bold': True, 'border': 1, 'align': 'center'})
        font_left = workbook.add_format({'align': 'left', 'border': 1, 'font_size': 12})
        font_center = workbook.add_format({'align': 'center', 'border': 1, 'valign': 'vcenter', 'font_size': 12})
        font_bold_center = workbook.add_format({'align': 'center', 'border': 1, 'valign': 'vcenter', 'font_size': 12, 'bold': True})
        border = workbook.add_format({'border': 1})

        worksheet.set_column('A:E', 20, border)
        worksheet.set_row(0, 20)
        worksheet.merge_range('A1:E1', "Attendance Log from " + date1.strftime('%d-%m-%Y') + " to " + date2.strftime('%d-%m-%Y'), bold)

        row = 2
        col = 0
        worksheet.merge_range(row, col, row + 1, col + 1, "Name of Employee", font_bold_center)
        worksheet.merge_range(row, col + 2, row + 1, col + 2, "Punching Time", font_bold_center)
        worksheet.merge_range(row, col + 3, row + 1, col + 3, "Status", font_bold_center)
        worksheet.merge_range(row, col + 4, row + 1, col + 4, "Device", font_bold_center)

        row += 2
        for log in logs:
            worksheet.merge_range(row, col, row, col + 1, log.employee_id.name, font_left)
            if log.punching_time:
                punching_time = self.convert_timezone(log.punching_time)
            else:
                punching_time = '***No Status***'
            worksheet.write(row, col + 2, punching_time, font_center)
            if log.status == "0":
                status = 'Check In'
            elif log.status == "1":
                status = 'Check Out'
            else:
                status = 'punched'
            worksheet.write(row, col + 3, status, font_center)
            worksheet.write(row, col + 4, log.device, font_center)
            row += 1

        workbook.close()
        xlsx_data = output.getvalue()
        return [fl, xlsx_data]