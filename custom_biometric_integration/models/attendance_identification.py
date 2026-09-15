from odoo import api, fields, models

class AttendanceIdentification(models.Model):
    _name = 'attendance.identification'
    _description = 'Attendance Identification'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    partner_id = fields.Many2one('res.partner', related='employee_id.user_id.partner_id', string='Partner', store=True)
    badge_id = fields.Char(related='employee_id.barcode', string='Badge ID', store=True)
    
    bio_id = fields.Char(string='Biometric ID', required=True)
    machine_id = fields.Many2one('biometric.config', string='Machine/Device', required=True)



class BiometricAttendanceDevices(models.Model):
    _inherit = 'biometric.attendance.devices'

    # to keep track of the linked identification record
    ident_id = fields.Many2one('attendance.identification', string="Linked Identification", ondelete="set null")

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            # create the corresponding record in attendance.identification
            ident = self.env['attendance.identification'].create({
                'employee_id': rec.employee_id.id,
                'bio_id': rec.biometric_attendance_id,
                'machine_id': rec.device_id.id,
            })
            # Link them together
            rec.ident_id = ident.id
        return records

    def write(self, vals):
        res = super().write(vals)
        for rec in self:
            if rec.ident_id:
                update_vals = {}
                if 'employee_id' in vals: 
                    update_vals['employee_id'] = rec.employee_id.id
                if 'biometric_attendance_id' in vals: 
                    update_vals['bio_id'] = rec.biometric_attendance_id
                if 'device_id' in vals: 
                    update_vals['machine_id'] = rec.device_id.id
                
                if update_vals:
                    rec.ident_id.write(update_vals)
        return res

    def unlink(self):
        # Find the linked identification records before deleting
        ident_records = self.mapped('ident_id')
        res = super().unlink()
        # delete them from attendance.identification
        if ident_records:
            ident_records.unlink()
        return res