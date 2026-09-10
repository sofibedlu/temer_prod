from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class MenuVisibilityRule(models.Model):
    _name = 'menu.visibility.rule'
    _description = 'Menu Visibility Rule'
    _rec_name = 'name'

    name = fields.Char(string='Rule Name', required=True)
    menu_ids = fields.Many2many(
        'ir.ui.menu', 
        'menu_visibility_menu_rel', 
        'visibility_rule_id',
        'menu_id', 
        string='Menu Items', 
        required=True
    )
    group_ids = fields.Many2many(
        'res.groups', 
        'menu_visibility_group_rel',
        'rule_id', 
        'group_id', 
        string='Visible to Groups'
    )
    hide_from_groups = fields.Many2many(
        'res.groups', 
        'menu_visibility_hide_group_rel', 
        'rule_id', 
        'group_id', 
        string='Hidden from Groups'
    )

    @api.constrains('group_ids', 'hide_from_groups')
    def _check_group_conflict(self):
        for rule in self:
            if rule.group_ids & rule.hide_from_groups:
                raise ValidationError(_("The same group cannot be in both 'Visible to Groups' and 'Hidden from Groups'"))

    def apply_visibility_rules(self):
        for rule in self:
            for menu in rule.menu_ids:
                if rule.hide_from_groups:
                    # Get current groups
                    current_groups = menu.groups_id
                    # Remove hidden groups
                    groups_to_keep = current_groups - rule.hide_from_groups
                    menu.write({
                        'groups_id': [(6, 0, groups_to_keep.ids)]
                    })
                
                if rule.group_ids:
                    # Only specified groups should see the menu
                    menu.write({
                        'groups_id': [(6, 0, rule.group_ids.ids)]
                    })

    def restore_default_visibility(self):
        for rule in self:
            for menu in rule.menu_ids:
                menu.write({
                    'groups_id': [(5, 0, 0)]  # Clear all groups
                })

    @api.model
    def create(self, vals):
        res = super(MenuVisibilityRule, self).create(vals)
        res.apply_visibility_rules()
        return res

    def write(self, vals):
        res = super(MenuVisibilityRule, self).write(vals)
        self.apply_visibility_rules()
        return res

class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    visibility_rule_ids = fields.Many2many(
        'menu.visibility.rule',
        'menu_visibility_menu_rel',
        'menu_id',
        'visibility_rule_id',
        string='Visibility Rules'
    )

    def _visible_menu_ids(self, debug=False):
        """ Override to handle menu visibility """
        visible_ids = super()._visible_menu_ids(debug=debug)
        
        if not visible_ids:
            return visible_ids

        # Get all rules that apply to the current user
        rules = self.env['menu.visibility.rule'].search([
            '|',
                ('group_ids', 'in', self.env.user.groups_id.ids),
                ('hide_from_groups', 'in', self.env.user.groups_id.ids)
        ])

        for rule in rules:
            if rule.hide_from_groups and self.env.user.groups_id & rule.hide_from_groups:
                # Remove menus that should be hidden from user's groups
                visible_ids = list(set(visible_ids) - set(rule.menu_ids.ids))
            
            if rule.group_ids and not (self.env.user.groups_id & rule.group_ids):
                # Remove menus that user's groups don't have access to
                visible_ids = list(set(visible_ids) - set(rule.menu_ids.ids))

        return visible_ids