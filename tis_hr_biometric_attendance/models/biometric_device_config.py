# -*- coding: utf-8 -*-
import pytz
from datetime import datetime
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.addons.base.models.res_partner import _tz_get
from ..zk.base import ZK

class BiometricDeviceConfig(models.Model):
    _name = 'biometric.config'
    _description = 'biometric config'

    name = fields.Char(string='Name', required=True)
    device_ip = fields.Char(string='Device IP', required=True)
    port = fields.Integer(string='Port', required=True)
    is_password_set = fields.Boolean(string='Is Password Set', default=False)
    device_password = fields.Char(string='Device Password')
    time_zone = fields.Selection(_tz_get, string='Timezone', default=lambda self: self.env.user.tz or 'GMT')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, readonly=True)
    used_for = fields.Selection([('check_in', 'Check In'), ('check_out', 'Check Out'), ('both', 'Both')],
                                default='check_in', string='Used for', required=True)
    carrier_xlsx_document = fields.Char()

    @api.onchange('is_password_set')
    def on_is_password_set_change(self):
        if not self.is_password_set:
            self.device_password = False

    def test_device_connection(self):
        ip = self.device_ip
        port = self.port
        password = int(self.device_password) if self.device_password else 0
        zk = ZK(ip, port, password=password)
        try:
            conn = zk.connect()
            if conn:
                zk.disable_device()
                zk.enable_device()
                raise UserError(_("Connection Success"))
            else:
                raise ValidationError(_("Connection Failed"))
        except Exception as e:
            raise UserError(_("%s", e))

    def sync_employees(self):
        uid = 0
        user_id = 0
        uid_list = []
        user_id_list = []
        zk = ZK(self.device_ip, self.port, password=self.device_password or 0)
        try:
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
                    
                employees = self.env['hr.employee'].search([])
                for employee in employees:
                    biometric_device = self.env['biometric.attendance.devices'].search([
                        ('employee_id', '=', employee.id), ('device_id', '=', self.id)
                    ])
                    if not biometric_device:
                        uid += 1
                        user_id += 1
                        self.env['biometric.attendance.devices'].create({
                            'employee_id': employee.id,
                            'biometric_attendance_id': str(user_id),
                            'device_id': self.id,
                        })
                        zk.set_user(uid, employee.name, 0, '', '', str(user_id))
                return {
                    'name': 'Success Message',
                    'type': 'ir.actions.act_window',
                    'res_model': 'employee.sync.wizard',
                    'view_mode': 'form',
                    'target': 'new'
                }
            else:
                raise ValidationError(_("Connection Failed"))
        except Exception as e:
            raise UserError(_("%s", e))

    def download_attendance_log(self):
        attend_obj = self.env['attendance.log']
        zk = ZK(self.device_ip, self.port, password=self.device_password or 0)
        try:
            conn = zk.connect()
            if conn:
                attendances = zk.get_attendance()
                if attendances:
                    local_tz = pytz.timezone(self.time_zone or 'GMT')
                    for attendance in attendances:
                        atten_time = attendance.timestamp
                        local_dt = local_tz.localize(atten_time, is_dst=None)
                        utc_dt = local_dt.astimezone(pytz.utc).replace(tzinfo=None)
                        
                        attendance_status = str(attendance.punch) if attendance.punch in [0, 1, 2] else '2'
                        
                        employees = self.env['biometric.attendance.devices'].search([
                            ('biometric_attendance_id', '=', str(attendance.user_id)), 
                            ('device_id', '=', self.id)
                        ])
                        
                        if len(employees) > 1:
                            raise UserError(_("Two Users have same Biometric User ID: %s", ", ".join(employees.mapped('employee_id.name'))))
                            
                        if employees:
                            existing_log = attend_obj.search([
                                ('employee_id', '=', employees.employee_id.id), 
                                ('punching_time', '=', utc_dt)
                            ])
                            
                            vals = {
                                'employee_id': employees.employee_id.id,
                                'punching_time': utc_dt,
                                'status': attendance_status,
                                'device': str(self.name),
                                'company_id': self.company_id.id,
                                'is_calculated': any(log.is_calculated for log in existing_log) if existing_log else False
                            }
                            
                            if existing_log:
                                existing_log.write(vals)
                            else:
                                attend_obj.create(vals)
                                
                return {
                    'name': 'Success Message',
                    'type': 'ir.actions.act_window',
                    'res_model': 'success.wizard',
                    'view_mode': 'form',
                    'target': 'new'
                }
            else:
                raise ValidationError(_("Connection failed"))
        except Exception as e:
            raise UserError(_("%s", e))

    @api.model
    def download_attendance_log_new(self):
        devices = self.search([])
        for device in devices:
            try:
                device.download_attendance_log()
            except Exception as e:
                import logging
                _logger = logging.getLogger(__name__)
                _logger.error(f"Failed to download attendance for device {device.name}: {e}")