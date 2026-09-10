import pytz
import logging
from odoo import api, fields, models
from odoo.addons.tis_hr_biometric_attendance.zk.base import ZK
#from odoo.addons.tis_hr_biometric_attendance.zk.mock import ZK

_logger = logging.getLogger(__name__)

class AttendanceLogAnalysis(models.Model):
    _name = 'attendance.log.analysis'
    _description = 'Raw Attendance Log (Source of Truth)'
    _order = 'timestamp desc'

    bio_id = fields.Char(string='Biometric ID', required=True, index=True)
    machine_id = fields.Many2one('biometric.config', string='Machine/Device', required=True, index=True)
    timestamp = fields.Datetime(string='Timestamp', required=True, index=True)
    read_by = fields.Many2one('res.users', string='Read By', required=True)
    is_locked = fields.Boolean(string='Is Locked', default=False)
    is_archived = fields.Boolean(string='Is Archived', default=False)

    @api.model
    def _cron_fetch_raw_logs(self):
        """ Automated Cronjob to fetch logs after the last_read_time """
        machines = self.env['biometric.config'].search([])
        bot_user = self.env.ref('base.user_root')

        for machine in machines:
            try:
                # Get last read time
                last_read_record = self.env['attendance.last.read'].search([('machine_id', '=', machine.id)], limit=1)
                last_read_time = last_read_record.last_read_time if last_read_record else False

                zk = ZK(machine.device_ip, machine.port, password=machine.device_password or 0)
                conn = zk.connect()
                if conn:
                    attendances = zk.get_attendance()
                    if attendances:
                        local_tz = pytz.timezone(machine.time_zone or 'GMT')
                        max_timestamp = last_read_time

                        logs_to_create = []
                        for attendance in attendances:
                            # Parse device local time to UTC
                            local_dt = local_tz.localize(attendance.timestamp, is_dst=None)
                            utc_dt = local_dt.astimezone(pytz.utc).replace(tzinfo=None)

                            # Filter only new records
                            if not last_read_time or utc_dt > last_read_time:
                                logs_to_create.append({
                                    'bio_id': str(attendance.user_id),
                                    'machine_id': machine.id,
                                    'timestamp': utc_dt,
                                    'read_by': bot_user.id,
                                })
                                # Track highest timestamp
                                if not max_timestamp or utc_dt > max_timestamp:
                                    max_timestamp = utc_dt

                        # Batch Insert
                        if logs_to_create:
                            self.create(logs_to_create)

                        # Update Last Read tracking
                        if max_timestamp:
                            if last_read_record:
                                last_read_record.write({'last_read_time': max_timestamp})
                            else:
                                self.env['attendance.last.read'].create({
                                    'machine_id': machine.id,
                                    'last_read_time': max_timestamp
                                })
                    zk.disconnect()
            except Exception as e:
                _logger.error(f"Cron Raw Fetch Failed for Machine {machine.name}: {e}")