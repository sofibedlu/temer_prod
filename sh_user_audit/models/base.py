# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, api
import datetime

IGNORE_MODEL = [
    'ir.config_parameter',
    'ir.actions.actions',
    'ir.actions.act_window'
]

IGNORE_MODEL_DICT = {
    'product.template': ['product.product', 'account.tax'],
    'product.product': ['product.template', 'account.tax']
}

class BaseModel(models.AbstractModel):
    _inherit = 'base'

    def _log(self, model_id, rec_id, operation, field_list=False):
        '''Create a User Audit Log
        field_list: [
            Field ID,
            Field Old Value,
            Field New Value
        ]'''
        vals = {
            'object': model_id,
            'user': self.env.uid,
            'type': operation,
            'record_id': rec_id,
            'modify_date': datetime.datetime.now(),
            # 'view_type': view_type
        }
        if field_list:
            vals.update({
                'updated_field': field_list[0],
                'old_value': field_list[1],
                'value_updated': field_list[2]
            })
        return self.env['sh.user.audit.log'].sudo().create(vals).id

    def _find_user_audit(self, operation_field_name):
        return self.env['sh.user.audit'].sudo().search([
            (operation_field_name, '=', True),
            ('model_ids.model', 'in', [self._name]),
            '|',
            ('user_ids.id', 'in', [self.env.uid]),
            ('is_all_users', '=', True)
        ], limit=1)

    @api.model_create_multi
    @api.returns('self', lambda value: value.id)
    def create(self, vals_list):
        records = super(BaseModel, self).create(vals_list)
        audit_log_id = self._find_user_audit('is_create')
        if audit_log_id:
            model_id = self.env['ir.model'].sudo().search(
                [('model', '=', self._name)], limit=1)
            for record in records:
                self._log(model_id.id, record.id, 'create')

        return records

    def _check_for_read_log(self):
        if self._name in IGNORE_MODEL:
            return False
        audit_log_id = self._find_user_audit('is_read')
        if not audit_log_id:
            return False

        model_id = self.env['ir.model'].sudo().search(
            [('model', '=', self._name)], limit=1)

        ignore_model_list = []
        # view_type = False
        if self.env.context.get('params'):
            active_model = self.env.context['params'].get('model')
            # view_type = self.env.context['params'].get('view_type')
            if active_model:
                if active_model != model_id.model:
                    return False
                ignore_model_list = IGNORE_MODEL_DICT.get(active_model)

        if len(self.ids) != 1:
            return False
        record = self.ids[0]

        # for record in self.ids:
        if ignore_model_list and model_id.model in ignore_model_list:
            return False

        # check previous entry
        if audit_log_id.last_sh_user_audit_log_id:
            last_log = audit_log_id.last_sh_user_audit_log_id
            if last_log.object.id == model_id.id and last_log.user.id in [self.env.uid, self.env.ref('base.user_root').id] and last_log.record_id == record:
                return False

        previous_entry = self.env['sh.user.audit.log'].sudo().search([
            ('object', '=', model_id.id),
            ('type', 'in', ['read', 'write', 'create']),
            ('modify_date', '>=', datetime.datetime.now() - datetime.timedelta(seconds=10)),
            ('modify_date', '<=', datetime.datetime.now()),
            ('record_id', '=', record),
            '|',
            ('user', '=', self.env.uid),
            ('user', '=', self.env.ref('base.user_root').id)
        ], order='id desc', limit=1)

        if not previous_entry:
            audit_log_id.sudo().write({
                'last_sh_user_audit_log_id': self._log(model_id.id, record, 'read')
            })
            return True

    def read(self, fields=None, load='_classic_read'):
        self._check_for_read_log()
        return super(BaseModel, self).read(fields=fields, load=load)

    def unlink(self):
        if self._name not in ('ir.model.data', 'ir.config_parameter', 'ir.property', 'ir.default', 'ir.model.fields', 'ir.model.relation', 'ir.module.module', 'ir.model'):
            audit_log_id = self._find_user_audit('is_delete')
            if audit_log_id:
                model_id = self.env['ir.model'].sudo().search(
                    [('model', '=', self._name)], limit=1)
                for record in self.ids:
                    self._log(model_id.id, record, 'delete')

        return super(BaseModel, self).unlink()

    def _check_for_log(self, vals, one2many_field_list=False):
        if not self._name not in ('ir.model.data', 'ir.config_parameter', 'ir.property', 'ir.default', 'ir.model.fields', 'ir.model.relation', 'ir.module.module', 'ir.model'):
            return
        audit_log_id = self._find_user_audit('is_write')
        # if not audit_log_id.is_full_log and one2many_field_list:
        #     return
        if not audit_log_id:
            return

        # prepare_one2many_field_list = []
        for rec in self:
            model_id = self.env['ir.model'].sudo().search(
                [('model', '=', self._name)], limit=1)

            if not (model_id and model_id in audit_log_id.model_ids):
                continue
            
            for field_name in vals:

                field_obj = audit_log_id.field_ids.filtered(
                    lambda x: x.model_id.id == model_id.id and x.name == field_name)

                if not field_obj:
                    continue
                
                if not audit_log_id.is_full_log:
                    self._log(model_id.id, rec.id, 'write')
                    continue

                # if one2many_field_list:
                #     if field_obj.ttype != 'one2many':
                #         continue
                #     else:
                #         # process the one2many log
                #         # TODO: Can be improved in future ...
                #         pass
                # else:
                #     if field_obj.ttype == 'one2many':
                #         prepare_one2many_field_list.append(field_obj)
                #         continue
                #     else:
                #         # continue below process
                #         pass

                current_rec = self.env[model_id.model].search_read(
                    [('id', '=', rec.id)], [field_name])

                if not current_rec:
                    continue

                new_val = vals[field_name]
                old_val = current_rec[0].get(field_name)

                # Add the proper Old/New Value in Log
                if field_obj.ttype == 'selection':
                    selection_dict = dict(eval(field_obj.selection))
                    new_val = selection_dict.get(new_val)
                    old_val = selection_dict.get(old_val)

                elif field_obj.ttype == 'many2one':
                    old_val, new_val = self._many2one_vals(field_obj, old_val, new_val)

                elif field_obj.ttype == 'many2many':
                    old_val, new_val = self._many2many_vals(field_obj, old_val, new_val)

                self._log(model_id.id, rec.id, 'write', [
                    field_obj.id, old_val, new_val
                ])

        # return prepare_one2many_field_list

    def sh_name(self, object):
        return getattr(object, object._rec_name)

    def _many2one_vals(self, field_obj, old_val, new_val):
        if isinstance(new_val, int):
            many2one_rec = self.env[field_obj.relation].browse(int(new_val))
            if many2one_rec:
                new_val = self.sh_name(many2one_rec)
        if isinstance(old_val, tuple):
            if len(old_val) > 1:
                old_val = old_val[1]
        return old_val, new_val

    def _many2many_vals(self, field_obj, old_val, new_val):
        # Old Val
        old_val_list = []
        old_val_dict = {}
        if isinstance(old_val, list):
            if old_val:
                many2many_recs = self.env[field_obj.relation].browse(old_val)
                if many2many_recs:
                    old_val_dict = {many2many_obj.id:self.sh_name(many2many_obj) for many2many_obj in many2many_recs}
                    old_val_list = [many2many_obj_name for many2many_obj_name in old_val_dict.values()]
                    if old_val_list:
                        old_val = ', '.join(old_val_list)
            else:
                old_val = ''

        # New Val
        if isinstance(new_val, list):
            if new_val:
                new_val_list = old_val_list
                for relational_list in new_val:

                    if isinstance(relational_list, list) and len(relational_list) == 2:
                        operation = relational_list[0]
                        obj_id = relational_list[1]

                        # Remove the link
                        if operation == 3:
                            if old_val_dict and new_val_list:
                                new_val_list.remove(old_val_dict[obj_id])
                            continue

                        # Link the existing record
                        elif operation == 4:
                            linked_obj = self.env[field_obj.relation].browse(obj_id)
                            if linked_obj:
                                new_val_list.append(self.sh_name(linked_obj))

                new_val = ', '.join(new_val_list)
            else:
                new_val = ''
        return old_val, new_val


    def write(self, vals):
        self._check_for_log(vals)
        # one2many_field_list = self._check_for_log(vals)
        # status = super(BaseModel, self).write(vals)
        # if one2many_field_list:
        #     self._check_for_log(vals, one2many_field_list)
        return super(BaseModel, self).write(vals)
