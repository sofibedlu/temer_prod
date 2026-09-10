# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import fields, models


class Clearlog(models.TransientModel):
    _name = "sh.clear.log"
    _description = "Clear Log Details"

    to_date = fields.Date(string="To Date", default=fields.Date.today())
    wizard_read = fields.Boolean()
    wizard_write = fields.Boolean()
    wizard_create = fields.Boolean()
    wizard_delete = fields.Boolean()
    configuration_ids = fields.Many2many("ir.model")
    all_log = fields.Boolean("All Log")

    def clear_log(self):
        domain = []

        if self.all_log:
            user_audit_logs = self.env['sh.user.audit.log'].search(domain)
            user_audit_logs.unlink()
        else:
            if self.to_date:
                domain.append(
                    ('modify_date', '>=', self.to_date.strftime("%Y-%m-%d 00:00:00")))
                domain.append(
                    ('modify_date', '<=', self.to_date.strftime("%Y-%m-%d 23:59:59")))

            if self.configuration_ids:
                domain.append(('object', 'in', self.configuration_ids.ids))

            user_audit_logs = self.env['sh.user.audit.log'].search(domain)
            delete_ids = []
            if self.wizard_read:
                read_user_audit_logs = user_audit_logs.filtered(
                    lambda x: x.type == 'read')
                if read_user_audit_logs:
                    for log in read_user_audit_logs:
                        if log not in delete_ids:
                            delete_ids.append(log)

            if self.wizard_write:
                write_user_audit_logs = user_audit_logs.filtered(
                    lambda x: x.type == 'write')
                if write_user_audit_logs:
                    for log in write_user_audit_logs:
                        if log not in delete_ids:
                            delete_ids.append(log)

            if self.wizard_create:
                create_user_audit_logs = user_audit_logs.filtered(
                    lambda x: x.type == 'create')
                if create_user_audit_logs:
                    for log in create_user_audit_logs:
                        if log not in delete_ids:
                            delete_ids.append(log)

            if self.wizard_delete:
                delete_user_audit_logs = user_audit_logs.filtered(
                    lambda x: x.type == 'delete')
                if delete_user_audit_logs:
                    for log in delete_user_audit_logs:
                        if log not in delete_ids:
                            delete_ids.append(log)

            if len(delete_ids) > 0:
                for log in delete_ids:
                    log.unlink()

    def cancle(self):
        pass
