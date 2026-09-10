from odoo import api, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def _unlink_obsolete_pre_contract_group(self, group):
        if not group:
            return
        group = group.sudo()
        self.env['ir.model.access'].sudo().search([
            ('group_id', '=', group.id),
        ]).unlink()
        self.env['ir.rule'].sudo().search([
            ('groups', 'in', group.id),
        ]).write({'groups': [(3, group.id)]})
        self.env['ir.model.data'].sudo().search([
            ('model', '=', 'res.groups'),
            ('res_id', '=', group.id),
        ]).unlink()
        group.unlink()

    def _sync_pre_contract_groups(self):
        if self.env.context.get('skip_pre_contract_group_sync'):
            return

        user_group = self.env.ref(
            'pre_contract_refund.group_pre_contract_refund_user',
            raise_if_not_found=False,
        )
        manager_group = self.env.ref(
            'pre_contract_refund.group_pre_contract_refund_manager',
            raise_if_not_found=False,
        )
        deputy_group = self.env.ref(
            'pre_contract_refund.group_pre_contract_refund_deputy_head_pmca',
            raise_if_not_found=False,
        )
        head_group = self.env.ref(
            'pre_contract_refund.group_pre_contract_refund_head_pmca',
            raise_if_not_found=False,
        )
        if not user_group or not manager_group:
            return

        users_both = self.filtered(
            lambda u: manager_group in u.groups_id and user_group in u.groups_id
        )
        if users_both:
            users_both.with_context(skip_pre_contract_group_sync=True).write({
                'groups_id': [(3, user_group.id)],
            })
        approval_users_with_manager = self.filtered(
            lambda u: manager_group in u.groups_id
            and (
                (deputy_group and deputy_group in u.groups_id)
                or (head_group and head_group in u.groups_id)
            )
        )
        if approval_users_with_manager:
            approval_users_with_manager.with_context(skip_pre_contract_group_sync=True).write({
                'groups_id': [(3, manager_group.id)],
            })

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        users._sync_pre_contract_groups()
        return users

    def write(self, vals):
        res = super().write(vals)
        if 'groups_id' in vals:
            self._sync_pre_contract_groups()
        return res

    @api.model
    def pre_contract_refund_cleanup_groups(self):
        """Cleanup existing users on module update/install."""
        user_group = self.env.ref(
            'pre_contract_refund.group_pre_contract_refund_user',
            raise_if_not_found=False,
        )
        manager_group = self.env.ref(
            'pre_contract_refund.group_pre_contract_refund_manager',
            raise_if_not_found=False,
        )
        deputy_group = self.env.ref(
            'pre_contract_refund.group_pre_contract_refund_deputy_head_pmca',
            raise_if_not_found=False,
        )
        head_group = self.env.ref(
            'pre_contract_refund.group_pre_contract_refund_head_pmca',
            raise_if_not_found=False,
        )
        reason_creator_group = self.env.ref(
            'pre_contract_refund.group_pre_contract_refund_reason_creator',
            raise_if_not_found=False,
        )
        payment_registrar_group = self.env.ref(
            'pre_contract_refund.group_pre_contract_refund_payment_registrar',
            raise_if_not_found=False,
        )
        if not user_group or not manager_group:
            return True

        users = self.sudo().search([
            ('groups_id', 'in', manager_group.id),
            ('groups_id', 'in', user_group.id),
        ])
        if users:
            users.with_context(skip_pre_contract_group_sync=True).write({
                'groups_id': [(3, user_group.id)],
            })
        approval_domain = [('groups_id', 'in', manager_group.id)]
        approval_group_ids = [
            group.id for group in (deputy_group, head_group) if group
        ]
        if approval_group_ids:
            approval_users = self.sudo().search(
                approval_domain + [('groups_id', 'in', approval_group_ids)]
            )
            if approval_users:
                approval_users.with_context(skip_pre_contract_group_sync=True).write({
                    'groups_id': [(3, manager_group.id)],
                })
        self._unlink_obsolete_pre_contract_group(reason_creator_group)
        self._unlink_obsolete_pre_contract_group(payment_registrar_group)
        return True
