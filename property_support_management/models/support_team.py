from odoo import models, fields, api

class SupportTeamConfig(models.Model):
    _name = 'support.team.config'
    _description = 'Support Team Configuration'
    _rec_name = 'user_id'

    user_id = fields.Many2one('res.users', string='User', required=True)
    department = fields.Char(string='Department', default='Support')

    @api.model_create_multi
    def create(self, vals_list):
        records = super(SupportTeamConfig, self).create(vals_list)
        support_group = self.env.ref('property_support_management.group_support_team', raise_if_not_found=False)
        user_group = self.env.ref('property_support_management.group_support_user', raise_if_not_found=False)
        if support_group and user_group:
            for record in records:
                if record.user_id not in support_group.users:
                    support_group.sudo().write({'users': [(4, record.user_id.id)]})
                if record.user_id not in user_group.users:
                    user_group.sudo().write({'users': [(4, record.user_id.id)]})
        return records

    def write(self, vals):
        if 'user_id' in vals:
            old_users = self.mapped('user_id')
        res = super(SupportTeamConfig, self).write(vals)
        if 'user_id' in vals:
            support_group = self.env.ref('property_support_management.group_support_team', raise_if_not_found=False)
            user_group = self.env.ref('property_support_management.group_support_user', raise_if_not_found=False)
            if support_group and user_group:
                # Add new users
                for record in self:
                    if record.user_id not in support_group.users:
                        support_group.sudo().write({'users': [(4, record.user_id.id)]})
                    if record.user_id not in user_group.users:
                        user_group.sudo().write({'users': [(4, record.user_id.id)]})
                # Remove old users if they are no longer in any config
                for old_user in old_users:
                    if not self.env['support.team.config'].search([('user_id', '=', old_user.id)]):
                        support_group.sudo().write({'users': [(3, old_user.id)]})
                        user_group.sudo().write({'users': [(3, old_user.id)]})
        return res

    def unlink(self):
        support_group = self.env.ref('property_support_management.group_support_team', raise_if_not_found=False)
        user_group = self.env.ref('property_support_management.group_support_user', raise_if_not_found=False)
        if support_group and user_group:
            for record in self:
                # check if user is in other team configs before removing
                other_configs = self.search([('user_id', '=', record.user_id.id), ('id', '!=', record.id)])
                if not other_configs:
                    support_group.sudo().write({'users': [(3, record.user_id.id)]})
                    user_group.sudo().write({'users': [(3, record.user_id.id)]})
        return super(SupportTeamConfig, self).unlink()
