# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from ..zk.base import ZK
from odoo.exceptions import ValidationError, UserError
import base64
import io
import xlwt

class BiometricDeviceWizard(models.TransientModel):
    _name = 'biometric.device.wizard'
    _description = 'biometric device wizard'

    biometric_id = fields.Many2one('biometric.config', string='Biometric Device', required=True)
    operation_type = fields.Selection([('update', 'Update'), ('scan', 'Scan'), ('remove', 'Remove')], string="Type")

    def confirm_update_with_biometric(self):
        employee_id = self._context.get('active_id')
        employee = self.env['hr.employee'].search([('id', '=', employee_id)])
        biometric_attendance_id = ''
        for line in employee.biometric_device_ids:
            biometric_attendance_id = line.biometric_attendance_id
        zk = ZK(self.biometric_id.device_ip, self.biometric_id.port, password=self.biometric_id.device_password or 0)
        conn = zk.connect()
        if conn:
            users = zk.get_users()
            valid = False
            if users:
                for user in users:
                    if user.user_id == biometric_attendance_id:
                        valid = True
                if valid == True:
                    raise ValidationError("Already in machine")
                else:
                    if biometric_attendance_id:
                        zk.set_user(int(biometric_attendance_id), employee.name, 0, '', '', biometric_attendance_id)
                    else:
                        self.update_employee()
            else:
                if biometric_attendance_id:
                    zk.set_user(int(biometric_attendance_id), employee.name, 0, '', '', biometric_attendance_id)
                else:
                    self.update_employee()
            zk.disconnect()
        else:
            raise ValidationError("Connection failed")

    def update_employee(self):
        uid_list = []
        user_id_list = []
        zk = ZK(self.biometric_id.device_ip, self.biometric_id.port, password=self.biometric_id.device_password or 0)
        conn = zk.connect()
        if conn:
            zk.disable_device()
            zk.enable_device()
            users = zk.get_users()
            if users:
                for user in users:
                    uid_list.append(user.uid)
                    user_id_list.append(int(user.user_id))
                uid_list.sort()
                user_id_list.sort()
            uid = uid_list[-1] if uid_list else 0
            user_id = user_id_list[-1] if user_id_list else 0
            
            employee_id = self._context.get('active_id')
            employee = self.env['hr.employee'].search([('id', '=', employee_id)])
            biometric_device = employee.biometric_device_ids.search(
                [('employee_id', '=', employee.id), ('device_id', '=', self.biometric_id.id)])
            if not biometric_device:
                uid += 1
                user_id += 1
                employee.biometric_device_ids = [(0, 0, {
                    'employee_id': employee.id,
                    'biometric_attendance_id': str(user_id),
                    'device_id': self.biometric_id.id,
                })]
                zk.set_user(uid, employee.name, 0, '', '', str(user_id))
        else:
            raise ValidationError("Connection Failed")

    def confirm_scan_with_biometric(self):
        employee_id = self._context.get('active_id')
        employee = self.env['hr.employee'].search([('id', '=', employee_id)])
        biometric_attendance_id = ''
        for attendance_id in employee.biometric_device_ids:
            biometric_attendance_id = attendance_id.biometric_attendance_id
        zk = ZK(self.biometric_id.device_ip, self.biometric_id.port, password=self.biometric_id.device_password or 0)
        conn = zk.connect()
        if conn:
            users = zk.get_users()
            valid = False
            if users:
                for user in users:
                    if user.user_id == biometric_attendance_id:
                        valid = True
                if valid == True:
                    try:
                        zk.enroll_user(uid=int(biometric_attendance_id), user_id=str(biometric_attendance_id))
                    except Exception as e:
                        raise UserError(_(e))
                    raise ValidationError("Place your finger on the Biometric Device")
                else:
                    raise ValidationError("Not in Machine")
            else:
                raise ValidationError("No Users Log")
        else:
            raise ValidationError("Connection failed")

    def remove_employee_from_biometric(self):
        employee_id = self._context.get('active_id')
        employee = self.env['hr.employee'].search([('id', '=', employee_id)])
        biometric_attendance_id = ''
        for attendance_id in employee.biometric_device_ids:
            biometric_attendance_id = attendance_id.biometric_attendance_id
        zk = ZK(self.biometric_id.device_ip, self.biometric_id.port, password=self.biometric_id.device_password or 0)
        conn = zk.connect()
        if conn:
            users = zk.get_users()
            valid = False
            if users:
                for user in users:
                    if user.user_id == biometric_attendance_id:
                        valid = True
                if valid == True:
                    zk.delete_user(user_id=str(biometric_attendance_id))
                    biometric_device = employee.biometric_device_ids.search(
                        [('biometric_attendance_id', '=', biometric_attendance_id),
                         ('device_id', '=', self.biometric_id.id)])
                    biometric_device.unlink()
                else:
                    raise ValidationError("Not in Machine")
            else:
                raise ValidationError("No Users Log")
        else:
            raise ValidationError("Connection failed")

class SuccessWizard(models.TransientModel):
    _name = 'success.wizard'
    _description = 'success wizard'

    carrier_xlsx_document = fields.Char()
    report_file = fields.Binary('File', readonly=True)
    report_name = fields.Char(string='File Name')
    is_printed = fields.Boolean('Printed', default=False)

    def export_attendance_xlsx(self):
        employee = self.env['hr.attendance'].search([])
        filename = 'Account Report.xls'
        workbook = xlwt.Workbook()
        worksheet = workbook.add_sheet('Account Report')
        title = xlwt.easyxf('font:height 400, bold True, name Arial; align: horiz center, vert center;pattern: pattern solid, fore_colour gray25;')
        sub_title = xlwt.easyxf('font: bold True, name Arial; align: horiz center, vert center')
        sub_title2 = xlwt.easyxf('font:name Arial;align: horiz center, vert center')
        
        worksheet.write_merge(0, 0, 0, 3, " Attendance Sheet", title)
        worksheet.write(1, 0, "Name of Employee", sub_title)
        worksheet.write(1, 1, "Check In", sub_title)
        worksheet.write(1, 2, "Check Out", sub_title)
        worksheet.write(1, 3, "Difference", sub_title)
        
        worksheet.row(0).height = 500
        worksheet.col(0).width = 7000
        worksheet.col(1).width = 8000
        worksheet.col(2).width = 8000
        worksheet.col(3).width = 7000

        row = 3
        for i in employee:
            in_time = i.check_in.strftime("%m/%d/%Y, %H:%M:%S") if i.check_in else ''
            out_time = i.check_out.strftime("%m/%d/%Y, %H:%M:%S") if i.check_out else ''
            worksheet.write(row, 0, i.employee_id.name, sub_title2)
            worksheet.write(row, 1, in_time, sub_title2)
            worksheet.write(row, 2, out_time, sub_title2)
            diff = "{:0.2f}".format(i.in_out_diff) if i.in_out_diff else "0.00"
            worksheet.write(row, 3, diff, sub_title2)
            row += 1

        fp = io.BytesIO()
        workbook.save(fp)
        expire_id = self.env['excel.report'].create({
            'excel_file': base64.b64encode(fp.getvalue()),
            'file_name': filename
        })
        fp.close()
        return {
            'view_mode': 'form',
            'res_id': expire_id.id,
            'res_model': 'excel.report',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

class EmployeeSyncWizard(models.TransientModel):
    _name = 'employee.sync.wizard'
    _description = 'employee sync wizard'