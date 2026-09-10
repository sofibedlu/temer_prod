# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, api
import datetime

class UserAudit(models.Model):
    _name = "sh.user.audit.log"
    _description = "User Audit Logs"
    _order = 'id desc'

    object = fields.Many2one('ir.model', string="Object")
    record_id = fields.Integer(string="Record ID")
    name = fields.Char(string="Reference", readonly=True)
    user = fields.Many2one('res.users', string="User")
    type = fields.Selection([
        ("read", "Read"),
        ("write", "Write"),
        ("create", "Create"),
        ("delete", "Delete"),
    ], )
    modify_date = fields.Datetime(string="Date")
    updated_field = fields.Many2one('ir.model.fields', string="Update Field")
    value_updated = fields.Char("Updated Value")
    old_value = fields.Char("Old Values")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.update(
                {"name": self.env["ir.sequence"].next_by_code("name.entry")})
        return super(UserAudit, self).create(vals_list)

# class BaseModel(models.AbstractModel):
#     _inherit = 'base'

#     @api.model_create_multi
#     @api.returns('self', lambda value: value.id)
#     def create(self, vals_list):
#         records = super(BaseModel, self).create(vals_list)
#         audit_log_id = self.env['sh.user.audit'].sudo().search([('is_create', '=', True),
#                                                                 ('model_ids.model', 'in', [
#                                                                  self._name]),
#                                                                 '|', ('user_ids.id', 'in', [self.env.uid]), ('is_all_users', '=', True)], limit=1)
#         if audit_log_id:
#             model_id = self.env['ir.model'].sudo().search(
#                 [('model', '=', self._name)], limit=1)
#             for record in records:
#                 self.env['sh.user.audit.log'].sudo().create({'object': model_id.id,
#                                                              'user': self.env.uid,
#                                                              'type': 'create',
#                                                              'record_id': record.id,
#                                                              'modify_date': datetime.datetime.now()
#                                                              })

#         return records

#     def read(self, fields=None, load='_classic_read'):
#         if self._name != 'ir.config_parameter':
#             audit_log_id = self.env['sh.user.audit'].sudo().search([('is_read', '=', True),
#                                                                     ('model_ids.model', 'in', [self._name]), '|', ('user_ids.id', 'in', [self.env.uid]), ('is_all_users', '=', True)], limit=1)
#             if audit_log_id:
#                 model_id = self.env['ir.model'].sudo().search(
#                     [('model', '=', self._name)], limit=1)
#                 for record in self.ids:
#                     # check previous entry
#                     previous_entry = self.env['sh.user.audit.log'].sudo().search([('object', '=', model_id.id),
#                                                                                   ('type', '=',
#                                                                                    'read'),
#                                                                                   ('modify_date', '>=', datetime.datetime.now(
#                                                                                   ) - datetime.timedelta(seconds=10)),
#                                                                                   ('modify_date', '<=', datetime.datetime.now(
#                                                                                   )),
#                                                                                   '|', ('user', '=', self.env.uid), ('user', '=', self.env.ref('base.user_root').id)])
#                     if not previous_entry:
#                         self.env['sh.user.audit.log'].sudo().create({'object': model_id.id,
#                                                                      'user': self.env.uid,
#                                                                      'type': 'read',
#                                                                      'record_id': record,
#                                                                      'modify_date': datetime.datetime.now()
#                                                                      })

#         return super(BaseModel, self).read(fields=fields, load=load)

#     def unlink(self):
#         if self._name not in ('ir.model.data', 'ir.config_parameter','ir.property','ir.default','ir.model.fields','ir.model.relation','ir.module.module','ir.model'):
#             audit_log_id = self.env['sh.user.audit'].sudo().search([('is_delete', '=', True),
#                                                                     ('model_ids.model', 'in',[self._name]),
#                                                                     '|', ('user_ids.id', 'in', [self.env.uid]), ('is_all_users', '=', True)], limit=1)
#             if audit_log_id:
#                 model_id = self.env['ir.model'].sudo().search(
#                     [('model', '=', self._name)], limit=1)
#                 for record in self.ids:
#                     self.env['sh.user.audit.log'].sudo().create({'object': model_id.id,
#                                                                  'user': self.env.uid,
#                                                                  'type': 'delete',
#                                                                  'record_id': record,
#                                                                  'modify_date': datetime.datetime.now()
#                                                                  })

#         return super(BaseModel, self).unlink()

#     def write(self, vals):
#         if self._name not in ('ir.model.data', 'ir.config_parameter','ir.property','ir.default','ir.model.fields','ir.model.relation','ir.module.module','ir.model'):
#             audit_log_id = self.env['sh.user.audit'].sudo().search([('is_write', '=', True),
#                                                                     ('model_ids.model', 'in', [
#                                                                      self._name]),
#                                                                     '|', ('user_ids.id', 'in', [self.env.uid]), ('is_all_users', '=', True)], limit=1)
#             if audit_log_id:
#                 for rec in self:
#                     model_id = self.env['ir.model'].sudo().search(
#                         [('model', '=', self._name)], limit=1)
#                     if model_id and model_id in audit_log_id.model_ids:
#                         for key in vals:
#                             field_log_track = audit_log_id.field_ids.filtered(
#                                 lambda x: x.model_id.id == model_id.id and x.name == key)
#                             if field_log_track:
#                                 if audit_log_id.is_full_log:
#                                     current_rec = self.env[model_id.model].search_read(
#                                         [('id', '=', rec.id)], [key])
#                                     if current_rec:
#                                         self.env['sh.user.audit.log'].sudo().create({'object': model_id.id,
#                                                                                      'user': self.env.uid,
#                                                                                      'type': 'write',
#                                                                                      'record_id': rec.id,
#                                                                                      'modify_date': datetime.datetime.now(),
#                                                                                      'updated_field': field_log_track.id,
#                                                                                      'value_updated': vals[key],
#                                                                                      'old_value': current_rec[0].get(key)
#                                                                                      })
#                                 else:
#                                     self.env['sh.user.audit.log'].sudo().create({'object': model_id.id,
#                                                                                  'user': self.env.uid,
#                                                                                  'type': 'write',
#                                                                                  'record_id': self.id,
#                                                                                  'modify_date': datetime.datetime.now(),
    
#                                                                                  })
#         return super(BaseModel, self).write(vals)
