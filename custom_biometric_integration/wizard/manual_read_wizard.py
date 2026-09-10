import pytz
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.addons.tis_hr_biometric_attendance.zk.base import ZK
#from odoo.addons.tis_hr_biometric_attendance.zk.mock import ZK

class ManualReadWizard(models.TransientModel):
    _name = 'manual.read.wizard'
    _description = 'Manual Attendance Read Wizard'

    machine_id = fields.Many2one('biometric.config', string='Machine', required=True)
    hr_period_id = fields.Many2one('hr.attendance.period', string='HR Period', required=True)
    override = fields.Boolean(string='Override Existing Logs', default=False)

    def action_read_manual(self):
        log_model = self.env['attendance.log.analysis']
        period_start = self.hr_period_id.start_date
        period_end = self.hr_period_id.end_date

        # Check existing records in the period
        existing_logs = log_model.search([
            ('machine_id', '=', self.machine_id.id),
            ('timestamp', '>=', period_start),
            ('timestamp', '<=', period_end)
        ])

        if existing_logs:
            if not self.override:
                raise ValidationError(_("Logs already exist for this machine in the selected period. Check 'Override' to replace them."))
            
            # Check for locked or archived records
            if any(log.is_locked or log.is_archived for log in existing_logs):
                raise ValidationError(_("Cannot override! Locked or archived records exist in this HR Period."))
            
            # Safe to unlink (override)
            existing_logs.unlink()

        # Connect and Fetch
        zk = ZK(self.machine_id.device_ip, self.machine_id.port, password=self.machine_id.device_password or 0)
        try:
            conn = zk.connect()
            if not conn:
                raise ValidationError(_("Connection to machine failed."))
            
            attendances = zk.get_attendance()
            if not attendances:
                return {'type': 'ir.actions.act_window_close'}

            local_tz = pytz.timezone(self.machine_id.time_zone or 'GMT')
            logs_to_create = []

            for attendance in attendances:
                local_dt = local_tz.localize(attendance.timestamp, is_dst=None)
                utc_dt = local_dt.astimezone(pytz.utc).replace(tzinfo=None)

                # Filter by Period
                if period_start <= utc_dt <= period_end:
                    logs_to_create.append({
                        'bio_id': str(attendance.user_id),
                        'machine_id': self.machine_id.id,
                        'timestamp': utc_dt,
                        'read_by': self.env.user.id,
                    })

            if logs_to_create:
                log_model.create(logs_to_create)

            zk.disconnect()
        except Exception as e:
            raise ValidationError(_("Error communicating with machine: %s", e))
        
        return {'type': 'ir.actions.act_window_close'}