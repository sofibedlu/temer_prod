from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.addons.tis_hr_biometric_attendance.zk.base import ZK

class BiometricDeviceConfig(models.Model):
    _inherit = 'biometric.config'

    connection_type = fields.Selection([
        ('tcp', 'Local Network (TCP/UDP)'),
        ('adms', 'Cloud ADMS (HTTP Push)')
    ], string="Connection Type", default='tcp', required=True)
    
    serial_number = fields.Char(string="Device Serial Number (SN)", help="Required for ADMS connection.")

    user_count = fields.Integer(string='User Count', compute='_compute_user_count')
    last_read_time = fields.Datetime(string='Last Read Time', compute='_compute_last_read_time')

    def _compute_user_count(self):
        for record in self:
            record.user_count = self.env['attendance.identification'].search_count([
                ('machine_id', '=', record.id)
            ])

    def _compute_last_read_time(self):
        for record in self:
            # Look up the last read time for this specific machine
            last_read = self.env['attendance.last.read'].search([
                ('machine_id', '=', record.id)
            ], limit=1)
            record.last_read_time = last_read.last_read_time if last_read else False

    def action_view_users(self):
        """ Opens the Attendance Identification records for this machine """
        self.ensure_one()
        return {
            'name': _('Machine Users'),
            'type': 'ir.actions.act_window',
            'res_model': 'attendance.identification',
            'view_mode': 'tree,form',
            'domain': [('machine_id', '=', self.id)],
            'context': {'default_machine_id': self.id},
        }

    def test_device_connection(self):
        """ Override to fix the Invalid Operation popup on success """
        self.ensure_one()

        # If ADMS, we can't 'test' the connection via TCP because Odoo acts as the server.
        if self.connection_type == 'adms':
            raise ValidationError(_("ADMS is a 'Push' protocol. You cannot test the connection from Odoo. Check the device screen to see if it is connected to the server."))

        
        ip = self.device_ip
        port = self.port
        password = int(self.device_password) if self.device_password else 0
        zk = ZK(ip, port, password=password)
        
        try:
            conn = zk.connect()
            if conn:

                # If we successfully connect, let's grab the Serial Number and save it automatically!
                try:
                    sn = zk.get_serialnumber()
                    if sn and not self.serial_number:
                        self.serial_number = sn
                except:
                    pass
                
                zk.disable_device()
                zk.enable_device()
                zk.disconnect()
                
                # Return a green success notification
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Connection Successful'),
                        'message': _('Successfully connected to machine: %s', self.name),
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                raise ValidationError(_("Connection Failed. The device did not respond."))
        except Exception as e:
            raise ValidationError(_("Connection Error: %s", e))