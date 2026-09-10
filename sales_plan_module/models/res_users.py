# -*- coding: utf-8 -*-

from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'
    
    def write(self, vals):
        """Override write to prevent manual assignment/removal of sales plan groups"""
        # Get sales plan group IDs
        manager_group = self.env.ref('sales_plan_module.group_sales_plan_manager', raise_if_not_found=False)
        supervisor_group = self.env.ref('sales_plan_module.group_sales_plan_supervisor_only', raise_if_not_found=False)
        
        if manager_group and supervisor_group and 'groups_id' in vals:
            # Remove sales plan groups from the write operation - they're managed automatically
            sales_plan_group_ids = [manager_group.id, supervisor_group.id]
            
            # If groups_id is being modified, filter out sales plan groups
            if isinstance(vals['groups_id'], list):
                # Filter out commands that add/remove sales plan groups
                filtered_commands = []
                for cmd in vals['groups_id']:
                    if len(cmd) >= 2:
                        op = cmd[0]
                        group_ids = cmd[1] if isinstance(cmd[1], list) else [cmd[1]]
                        
                        # Check if any of the groups being modified are sales plan groups
                        if any(gid in sales_plan_group_ids for gid in group_ids):
                            # Skip this command - don't allow manual modification of sales plan groups
                            _logger.info(f"Skipping manual modification of sales plan groups for user {self.name}")
                            continue
                    
                    filtered_commands.append(cmd)
                
                vals['groups_id'] = filtered_commands
        
        return super().write(vals)
    
    @api.model
    def _assign_manager_group(self):
        """
        Post-init hook: Automatically assign groups to control menu visibility.
        - Managers (Team Managers, Wing Managers) and CRM Admin get 'group_sales_plan_manager' (see Plan Document menu)
        - Supervisors who are NOT managers get 'group_sales_plan_supervisor_only' (see Sales Plan menu)
        Note: CRM Admin access is handled via direct group assignment in menu configuration
        """
        try:
            manager_group = self.env.ref('sales_plan_module.group_sales_plan_manager', raise_if_not_found=False)
            supervisor_only_group = self.env.ref('sales_plan_module.group_sales_plan_supervisor_only', raise_if_not_found=False)
            
            if not manager_group or not supervisor_only_group:
                _logger.warning("Sales Plan groups not found, skipping assignment")
                return
            
            # Get all users who are team managers or wing managers
            # Note: CRM Admin access is handled separately via direct group assignment in menu configuration
            manager_user_ids = set()
            manager_details = []  # For logging
            
            # Check for team managers
            if 'property.sales.team' in self.env:
                teams = self.env['property.sales.team'].search([])
                _logger.info(f"=== SALES PLAN GROUP ASSIGNMENT: Found {len(teams)} teams")
                for team in teams:
                    if team.manager_id:
                        manager_user_ids.add(team.manager_id.id)
                        manager_details.append(f"Team Manager: {team.manager_id.name} (ID: {team.manager_id.id}) - Team: {team.name if hasattr(team, 'name') else 'N/A'}")
                        _logger.info(f"  → Team Manager found: {team.manager_id.name} (ID: {team.manager_id.id})")
            
            # Check for wing managers
            if 'property.sales.wing' in self.env:
                wings = self.env['property.sales.wing'].search([])
                _logger.info(f"=== SALES PLAN GROUP ASSIGNMENT: Found {len(wings)} wings")
                for wing in wings:
                    if wing.manager_id:
                        manager_user_ids.add(wing.manager_id.id)
                        manager_details.append(f"Wing Manager: {wing.manager_id.name} (ID: {wing.manager_id.id}) - Wing: {wing.name if hasattr(wing, 'name') else 'N/A'}")
                        _logger.info(f"  → Wing Manager found: {wing.manager_id.name} (ID: {wing.manager_id.id})")
            
            _logger.info(f"=== SALES PLAN GROUP ASSIGNMENT: Total managers found: {len(manager_user_ids)}")
            _logger.info(f"  Manager User IDs: {list(manager_user_ids)}")
            
            # Get all users who are supervisors (but NOT managers)
            supervisor_only_user_ids = set()
            if 'property.sales.supervisor' in self.env:
                supervisors = self.env['property.sales.supervisor'].search([])
                _logger.info(f"=== SALES PLAN GROUP ASSIGNMENT: Found {len(supervisors)} supervisors")
                for supervisor in supervisors:
                    if supervisor.name and supervisor.name.id not in manager_user_ids:
                        supervisor_only_user_ids.add(supervisor.name.id)
                        _logger.info(f"  → Supervisor (not manager): {supervisor.name.name} (ID: {supervisor.name.id})")
            
            # Update manager group
            current_manager_users = set(manager_group.users.ids)
            users_to_add_manager = list(manager_user_ids - current_manager_users)
            users_to_remove_manager = list(current_manager_users - manager_user_ids)
            
            _logger.info(f"=== MANAGER GROUP UPDATE:")
            _logger.info(f"  Current manager group users: {list(current_manager_users)}")
            _logger.info(f"  Users to add: {users_to_add_manager}")
            _logger.info(f"  Users to remove: {users_to_remove_manager}")
            
            if users_to_add_manager:
                manager_group.write({'users': [(4, uid) for uid in users_to_add_manager]})
                _logger.info(f"✓ Assigned Manager group to {len(users_to_add_manager)} users: {users_to_add_manager}")
                # Log details for each user added
                for uid in users_to_add_manager:
                    user = self.env['res.users'].browse(uid)
                    _logger.info(f"  → User: {user.name} (ID: {uid}) - Groups: {[g.name for g in user.groups_id]}")
            
            if users_to_remove_manager:
                manager_group.write({'users': [(3, uid) for uid in users_to_remove_manager]})
                _logger.info(f"✓ Removed Manager group from {len(users_to_remove_manager)} users: {users_to_remove_manager}")
            
            # Update supervisor-only group
            current_supervisor_only_users = set(supervisor_only_group.users.ids)
            users_to_add_supervisor = list(supervisor_only_user_ids - current_supervisor_only_users)
            users_to_remove_supervisor = list(current_supervisor_only_users - supervisor_only_user_ids)
            
            _logger.info(f"=== SUPERVISOR-ONLY GROUP UPDATE:")
            _logger.info(f"  Current supervisor-only group users: {list(current_supervisor_only_users)}")
            _logger.info(f"  Users to add: {users_to_add_supervisor}")
            _logger.info(f"  Users to remove: {users_to_remove_supervisor}")
            
            if users_to_add_supervisor:
                supervisor_only_group.write({'users': [(4, uid) for uid in users_to_add_supervisor]})
                _logger.info(f"✓ Assigned Supervisor-Only group to {len(users_to_add_supervisor)} users: {users_to_add_supervisor}")
            
            if users_to_remove_supervisor:
                supervisor_only_group.write({'users': [(3, uid) for uid in users_to_remove_supervisor]})
                _logger.info(f"✓ Removed Supervisor-Only group from {len(users_to_remove_supervisor)} users: {users_to_remove_supervisor}")
                
        except Exception as e:
            _logger.error(f"Error in _assign_manager_group: {e}", exc_info=True)
    
    def _check_menu_visibility(self):
        """
        Debug method to check menu visibility for current user.
        Logs all relevant group memberships and menu access.
        """
        user = self.env.user
        _logger.info("=" * 80)
        _logger.info(f"=== MENU VISIBILITY CHECK for User: {user.name} (ID: {user.id}) ===")
        
        # Check base groups
        is_system = user.has_group('base.group_system')
        is_supervisor = user.has_group('temer_structure.access_property_sales_supervisor_group')
        is_team_manager = user.has_group('temer_structure.access_property_sales_team_manager_group')
        is_wing_manager = user.has_group('temer_structure.access_property_wing_manager_group')
        is_crm_admin = user.has_group('temer_structure.access_property_crm_admin_group')
        
        _logger.info(f"  Base Groups:")
        _logger.info(f"    - System Admin: {is_system}")
        _logger.info(f"    - Supervisor: {is_supervisor}")
        _logger.info(f"    - Team Manager: {is_team_manager}")
        _logger.info(f"    - Wing Manager: {is_wing_manager}")
        _logger.info(f"    - CRM Admin: {is_crm_admin}")
        
        # Check custom groups
        manager_group = self.env.ref('sales_plan_module.group_sales_plan_manager', raise_if_not_found=False)
        supervisor_only_group = self.env.ref('sales_plan_module.group_sales_plan_supervisor_only', raise_if_not_found=False)
        
        has_manager_group = manager_group and user.id in manager_group.users.ids if manager_group else False
        has_supervisor_only_group = supervisor_only_group and user.id in supervisor_only_group.users.ids if supervisor_only_group else False
        
        _logger.info(f"  Custom Groups:")
        _logger.info(f"    - Sales Plan Manager Group: {has_manager_group}")
        _logger.info(f"    - Sales Plan Supervisor Only Group: {has_supervisor_only_group}")
        
        # Check actual role assignments
        is_team_manager_role = False
        is_wing_manager_role = False
        
        if 'property.sales.team' in self.env:
            teams = self.env['property.sales.team'].search([('manager_id', '=', user.id)])
            if teams:
                is_team_manager_role = True
                _logger.info(f"  Role Check: Team Manager = TRUE (Teams: {[t.name for t in teams]})")
            else:
                _logger.info(f"  Role Check: Team Manager = FALSE")
        
        if 'property.sales.wing' in self.env:
            wings = self.env['property.sales.wing'].search([('manager_id', '=', user.id)])
            if wings:
                is_wing_manager_role = True
                _logger.info(f"  Role Check: Wing Manager = TRUE (Wings: {[w.name for w in wings]})")
            else:
                _logger.info(f"  Role Check: Wing Manager = FALSE")
        
        # Check menu visibility
        _logger.info(f"  Menu Visibility:")
        _logger.info(f"    - Sales Plan Root Menu: Should be visible (all groups)")
        _logger.info(f"    - Sales Plans Submenu: Should be visible if supervisor-only group = {has_supervisor_only_group}")
        _logger.info(f"    - Plan Document Submenu: Should be visible if (CRM Admin OR Team Manager OR Wing Manager) = {is_crm_admin or is_team_manager or is_wing_manager}")
        
        # All user groups
        all_groups = [g.name for g in user.groups_id]
        _logger.info(f"  All User Groups ({len(all_groups)}): {all_groups}")
        
        _logger.info("=" * 80)
        
        return {
            'user_id': user.id,
            'user_name': user.name,
            'is_system': is_system,
            'is_supervisor': is_supervisor,
            'is_team_manager': is_team_manager,
            'is_wing_manager': is_wing_manager,
            'is_crm_admin': is_crm_admin,
            'has_manager_group': has_manager_group,
            'has_supervisor_only_group': has_supervisor_only_group,
            'is_team_manager_role': is_team_manager_role,
            'is_wing_manager_role': is_wing_manager_role,
            'all_groups': all_groups
        }
    
    @api.model
    def debug_all_managers_menu_access(self):
        """
        Debug method to check menu access for all managers.
        Logs detailed information about each manager's group memberships and menu visibility.
        """
        _logger.info("=" * 80)
        _logger.info("=== DEBUGGING ALL MANAGERS MENU ACCESS ===")
        
        # Get all team managers
        team_managers = []
        if 'property.sales.team' in self.env:
            teams = self.env['property.sales.team'].search([])
            for team in teams:
                if team.manager_id:
                    team_managers.append({
                        'user': team.manager_id,
                        'team': team,
                        'type': 'Team Manager'
                    })
        
        # Get all wing managers
        wing_managers = []
        if 'property.sales.wing' in self.env:
            wings = self.env['property.sales.wing'].search([])
            for wing in wings:
                if wing.manager_id:
                    wing_managers.append({
                        'user': wing.manager_id,
                        'wing': wing,
                        'type': 'Wing Manager'
                    })
        
        all_managers = team_managers + wing_managers
        
        _logger.info(f"Found {len(all_managers)} managers total ({len(team_managers)} team managers, {len(wing_managers)} wing managers)")
        
        # Check each manager
        for mgr_info in all_managers:
            user = mgr_info['user']
            _logger.info("-" * 80)
            _logger.info(f"Manager: {user.name} (ID: {user.id}) - Type: {mgr_info['type']}")
            
            # Check groups
            has_team_manager_group = user.has_group('temer_structure.access_property_sales_team_manager_group')
            has_wing_manager_group = user.has_group('temer_structure.access_property_wing_manager_group')
            has_crm_admin_group = user.has_group('temer_structure.access_property_crm_admin_group')
            has_supervisor_group = user.has_group('temer_structure.access_property_sales_supervisor_group')
            
            manager_group = self.env.ref('sales_plan_module.group_sales_plan_manager', raise_if_not_found=False)
            has_manager_custom_group = manager_group and user.id in manager_group.users.ids if manager_group else False
            
            _logger.info(f"  Groups:")
            _logger.info(f"    - Team Manager Group: {has_team_manager_group}")
            _logger.info(f"    - Wing Manager Group: {has_wing_manager_group}")
            _logger.info(f"    - CRM Admin Group: {has_crm_admin_group}")
            _logger.info(f"    - Supervisor Group: {has_supervisor_group}")
            _logger.info(f"    - Sales Plan Manager Custom Group: {has_manager_custom_group}")
            
            # Check menu visibility groups
            menu_plan_document = self.env.ref('sales_plan_module.menu_plan_document', raise_if_not_found=False)
            menu_root = self.env.ref('sales_plan_module.menu_sales_plan_root', raise_if_not_found=False)
            
            if menu_plan_document:
                user_groups_for_menu = set(user.groups_id.ids)
                menu_groups = set(menu_plan_document.groups_id.ids)
                has_access = bool(user_groups_for_menu & menu_groups) or user.has_group('base.group_system')
                _logger.info(f"  Plan Document Menu:")
                _logger.info(f"    - Menu Groups: {[g.name for g in menu_plan_document.groups_id]}")
                _logger.info(f"    - User has matching group: {has_access}")
                _logger.info(f"    - Menu visible: {menu_plan_document._is_visible() if hasattr(menu_plan_document, '_is_visible') else 'N/A'}")
            
            if menu_root:
                user_groups_for_root = set(user.groups_id.ids)
                root_menu_groups = set(menu_root.groups_id.ids)
                has_root_access = bool(user_groups_for_root & root_menu_groups) or user.has_group('base.group_system')
                _logger.info(f"  Root Menu:")
                _logger.info(f"    - Menu Groups: {[g.name for g in menu_root.groups_id]}")
                _logger.info(f"    - User has matching group: {has_root_access}")
                _logger.info(f"    - Menu visible: {menu_root._is_visible() if hasattr(menu_root, '_is_visible') else 'N/A'}")
            
            # Check role assignments
            if mgr_info['type'] == 'Team Manager':
                _logger.info(f"  Team Assignment: {mgr_info['team'].name if hasattr(mgr_info['team'], 'name') else 'N/A'}")
            elif mgr_info['type'] == 'Wing Manager':
                _logger.info(f"  Wing Assignment: {mgr_info['wing'].name if hasattr(mgr_info['wing'], 'name') else 'N/A'}")
        
        _logger.info("=" * 80)
        
        return {
            'total_managers': len(all_managers),
            'team_managers': len(team_managers),
            'wing_managers': len(wing_managers)
        }

