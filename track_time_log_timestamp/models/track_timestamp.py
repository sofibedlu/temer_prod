from odoo import models, api, fields, _
from datetime import datetime

def get_changed_tracked_fields(self, vals, exclude_fields=None):
    tracked_fields = {name for name, field in self._fields.items() if getattr(field, 'tracking', False)}
    if exclude_fields:
        tracked_fields -= set(exclude_fields)

    changed_fields = []
    for field in tracked_fields:
        if field in vals:
            field_type = self._fields[field].type
            old_value = self[field]
            new_value = vals[field]

            if field_type in ['many2many']:
                old_ids = set(old_value.ids)
                new_ids = set()
                if isinstance(new_value, (list, tuple)):
                    for item in new_value:
                        if isinstance(item, (list, tuple)) and item and item[0] == 6:
                            new_ids.update(item[2])
                        elif isinstance(item, int):
                            new_ids.add(item)
                if old_ids != new_ids:
                    changed_fields.append(field)
            elif field_type == 'many2one':
                old_id = old_value.id if old_value else False
                if hasattr(new_value, 'id'):
                    new_id = new_value.id
                elif isinstance(new_value, int):
                    new_id = new_value
                else:
                    new_id = False
                if old_id != new_id:
                    changed_fields.append(field)
            else:
                if old_value != new_value:
                    changed_fields.append(field)
    return changed_fields


class Property(models.Model):
    _inherit = 'property.property'

    def write(self, vals):
        for rec in self:
            changed_fields = get_changed_tracked_fields(rec, vals)
            if changed_fields:
                current_time = fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                changed = ", ".join(self._fields[f].string for f in changed_fields)
                rec.message_post(
                    body=("Changed %s at %s") % (changed, current_time),
                    message_type="notification"
                )
        return super().write(vals)

    def create(self, vals_list):
        records = super().create(vals_list)
        current_time = fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        for rec in records:
            rec.message_post(
                body=("Property created at %s") % current_time,
                message_type="notification"
            )
        return records

class CrmLeadInheritedChatter(models.Model):
    _inherit = 'crm.lead'

    def write(self, vals):
        if self.env.context.get('chatter_custom_posted'):
            return super().write(vals)
        exclude_fields = {'phone_ids', 'phone_no', 'phone'}
        for rec in self:
            changed_fields = get_changed_tracked_fields(rec, vals, exclude_fields=exclude_fields)
            if changed_fields:
                current_time = fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                changed_labels = ", ".join(self._fields[f].string for f in changed_fields)
                rec.with_context(chatter_custom_posted=True).message_post(
                    body=("Changed %s at %s") % (changed_labels, current_time),
                    message_type="notification"
                )
        return super().write(vals)

    @api.model
    def create(self, vals_list):
        if isinstance(vals_list, dict):
            vals_list = [vals_list]
        records = super().create(vals_list)
        current_time = fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        for rec in records:
            rec.message_post(
                body=("Lead created at %s") % current_time,
                message_type="notification"
            )
        return records

class PropertyReservationChatter(models.Model):
    _inherit = 'property.reservation'

    def write(self, vals):
        for rec in self:
            changed_fields = get_changed_tracked_fields(rec, vals)
            if changed_fields:
                current_time = fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                changed_labels = ", ".join(self._fields[f].string for f in changed_fields)
                rec.with_context(chatter_custom_posted=True).message_post(
                    body=("Changed %s at %s") % (changed_labels, current_time),
                    message_type="notification"
                )
        return super().write(vals)

    @api.model
    def create(self, vals):
        record = super().create(vals)
        current_time = fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        record.message_post(
            body=("Reservation created at %s") % current_time,
            message_type="notification"
        )
        return record

class CrmLeadCallCenterChatter(models.Model):
    _inherit = 'crm.callcenter'

    def write(self, vals):
        if self.env.context.get('chatter_custom_posted'):
            return super().write(vals)
        exclude_fields = {'phone_ids', 'phone_no', 'phone'}
        for rec in self:
            changed_fields = get_changed_tracked_fields(rec, vals, exclude_fields=exclude_fields)
            if changed_fields:
                current_time = fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                changed_labels = ", ".join(self._fields[f].string for f in changed_fields)
                rec.with_context(chatter_custom_posted=True).message_post(
                    body=("Changed %s at %s") % (changed_labels, current_time),
                    message_type="notification"
                )
        return super().write(vals)

    @api.model
    def create(self, vals):
        record = super().create(vals)
        current_time = fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        record.message_post(
            body=("Call Center Lead created at %s") % current_time,
            message_type="notification"
        )
        return record

class CrmWebsiteChatter(models.Model):
    _inherit = 'crm.website'

    def write(self, vals):
        if self.env.context.get('chatter_custom_posted'):
            return super().write(vals)
        exclude_fields = {'phone_ids', 'phone_no', 'phone'}
        for rec in self:
            changed_fields = get_changed_tracked_fields(rec, vals, exclude_fields=exclude_fields)
            if changed_fields:
                current_time = fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                changed_labels = ", ".join(self._fields[f].string for f in changed_fields)
                rec.with_context(chatter_custom_posted=True).message_post(
                    body=("Changed %s at %s") % (changed_labels, current_time),
                    message_type="notification"
                )
        return super().write(vals)

    @api.model
    def create(self, vals):
        record = super().create(vals)
        current_time = fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        record.message_post(
            body=("Website Lead created at %s") % current_time,
            message_type="notification"
        )
        return record

class CrmReceptionChatter(models.Model):
    _inherit = 'crm.reception'

    def write(self, vals):
        if self.env.context.get('chatter_custom_posted'):
            return super().write(vals)
        exclude_fields = {'phone_ids', 'phone_no', 'phone'}
        for rec in self:
            changed_fields = get_changed_tracked_fields(rec, vals, exclude_fields=exclude_fields)
            if changed_fields:
                current_time = fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                changed_labels = ", ".join(self._fields[f].string for f in changed_fields)
                rec.with_context(chatter_custom_posted=True).message_post(
                    body=("Changed %s at %s") % (changed_labels, current_time),
                    message_type="notification"
                )
        return super().write(vals)

    @api.model
    def create(self, vals):
        record = super().create(vals)
        current_time = fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        record.message_post(
            body=("Reception Lead created at %s") % current_time,
            message_type="notification"
        )
        return record
