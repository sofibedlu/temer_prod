/** @odoo-module */

import { Component, onWillStart, useState, markup } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session";
import { _t } from "@web/core/l10n/translation";

//TODO: if the warnings of static props is an issue just define smt like the following for that class. 
export class HRManagerDashboard extends Component {
    static props = {
        action: Object,
        actionId: Number,
        className: { type: String, optional: true },
    }; // To avoid the warning HRManagerDashboard does not have static props..
    setup() {
        this.actionService = useService("action");
        this.rpc = useService("rpc");
        this.notification = useService("notification");

        this.state = useState({
            user_name: "",
            leave_count_manager: 0,
            allocated_leave_count_manager: 0,
            attendance_count_manager: 0,
            expense_count_manager: 0,
            contract_count_manager: 0,
            birthday_data: "",
            anniversary_data: "",
            announcement_data: "",
            expense_manager_data: "",
            attendance_manager_data: "",
            leave_manager_data: "",
        });

        this.userData = {};

        onWillStart(async () => {
            await this.fetchAllData();
        });
    }

    async fetchAllData() {
        try {
            const result = await this.rpc("/get_user_name");
            const data = typeof result === 'string' ? JSON.parse(result) : result;
            
            // Ensure userData is an object even if controller returns null
            this.userData = data || {};

            if (data) {
                this.state.user_name = data.user || "";
                this.state.leave_count_manager = data.leave_count_manager || 0;
                this.state.allocated_leave_count_manager = data.allocated_leave_count_manager || 0;
                this.state.attendance_count_manager = data.attendance_count_manager || 0;
                this.state.expense_count_manager = data.expense_count_manager || 0;
                this.state.contract_count_manager = data.contract_count_manager || 0;
            }

            const endpoints = [
                '/get_employee_birhday_data',
                '/get_employee_anniversary_data',
                '/get_annoucement_data',
                '/get_employee_expense_manager_data',
                '/get_employee_attendance_manager_data',
                '/get_employee_leave_manager_data'
            ];

            // Use Promise.allSettled to prevent one failure from stopping everything
            const results = await Promise.allSettled(endpoints.map(url => this.rpc(url)));
            
            this.state.birthday_data = markup(results[0].status === 'fulfilled' ? results[0].value : "");
            this.state.anniversary_data = markup(results[1].status === 'fulfilled' ? results[1].value : "");
            this.state.announcement_data = markup(results[2].status === 'fulfilled' ? results[2].value : "");
            this.state.expense_manager_data = markup(results[3].status === 'fulfilled' ? results[3].value : "");
            this.state.attendance_manager_data = markup(results[4].status === 'fulfilled' ? results[4].value : "");
            this.state.leave_manager_data = markup(results[5].status === 'fulfilled' ? results[5].value : "");

        } catch (error) {
            console.error("Dashboard Data Error:", error);
        }
    }

    // -------------------------------------------------------------------------
    // ACTIONS
    // -------------------------------------------------------------------------

    open_department_policy() {
        // Fix for "undefined reading map": Explicitly define params before calling doAction
        const count = this.userData.policy_count || 0;
        
        let actionObj = {
            name: _t("Department Policy"),
            type: 'ir.actions.act_window',
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'new',
        };

        if (count > 0) {
            actionObj.res_model = 'sh.department.policy.wizard';
            actionObj.context = {
                'default_department_id': this.userData.department || false,
            };
        } else {
            actionObj.res_model = 'sh.blank.data.wizard';
        }

        this.actionService.doAction(actionObj);
    }

    open_cmp_policy_manager() {
    const companyIds = this.userService?.context?.allowed_company_ids;

    if (!companyIds || !companyIds.length) {
        this.notification.add(
            _t("No active company found."),
            { type: "warning" }
        );
        return;
    }

    const currentCompanyId = companyIds[0];

    this.actionService.doAction({
        type: 'ir.actions.act_window',
        name: _t("Company Policy"),
        res_model: 'sh.company.policy.wizard',
        view_mode: 'form',
        context: {
            default_company_id: currentCompanyId,
        },
        target: 'new',
    });
}


    // --- Employee Related Actions ---
    // Removed the "if (this.userData.employee)" check so the window always opens.
    // The domain is applied conditionally.

    open_employee_contract() {
        const domain = this.userData.employee ? [['employee_id.parent_id', '=', this.userData.employee]] : [];
        
        this.actionService.doAction({
            name: _t("Contract"),
            type: 'ir.actions.act_window',
            res_model: 'hr.contract',
            view_mode: 'tree,kanban,form',
            views: [[false, 'tree'], [false, 'kanban'], [false, 'form']],
            domain: domain,
            target: 'current'
        });
    }

    open_employee_expense() {
        const domain = this.userData.employee ? [['employee_id.parent_id', '=', this.userData.employee]] : [];
        const context = { 'search_default_employee': 1 };

        this.actionService.doAction({
            name: _t("Expense"),
            type: 'ir.actions.act_window',
            res_model: 'hr.expense',
            view_mode: 'tree,kanban,form,graph,pivot,activity',
            views: [[false, 'tree'], [false, 'kanban'], [false, 'form'], [false, 'graph'], [false, 'pivot'], [false, 'activity']],
            domain: domain,
            context: context,
            target: 'current'
        });
    }

    open_employee_attendnace() {
        // Function name matches XML snake_case (attendnace typo preserved)
        const domain = this.userData.employee ? [['employee_id.parent_id', '=', this.userData.employee]] : [];
        const context = { 'search_default_employee': 1 };

        this.actionService.doAction({
            name: _t("Attendance"),
            type: 'ir.actions.act_window',
            res_model: 'hr.attendance',
            view_mode: 'tree,kanban,form',
            views: [[false, 'tree'], [false, 'kanban'], [false, 'form']],
            domain: domain,
            context: context,
            target: 'current'
        });
    }

    open_employee_leave() {
        const domain = this.userData.employee ? [['employee_id.parent_id', '=', this.userData.employee]] : [];
        
        this.actionService.doAction({
            name: _t("Leaves"),
            type: 'ir.actions.act_window',
            res_model: 'hr.leave',
            view_mode: 'calendar,tree,form,activity',
            views: [[false, 'tree'], [false, 'calendar'], [false, 'form'], [false, 'activity']],
            domain: domain,
            target: 'current'
        });
    }

    action_create_leave_manager() {
        // If no employee found, we open the form anyway (user can select employee manually)
        let context = {};
        if (this.userData.employee) {
            context['default_employee_id'] = this.userData.employee;
        }

        this.actionService.doAction({
            name: _t("Leave Request"),
            type: 'ir.actions.act_window',
            res_model: 'hr.leave',
            view_mode: 'form',
            views: [[false, 'form']],
            context: context,
            target: 'current'
        });
    }

    action_create_expense_manager() {
        let context = {};
        if (this.userData.employee) {
            context['default_employee_id'] = this.userData.employee;
        }

        this.actionService.doAction({
            name: _t("Expense"),
            type: 'ir.actions.act_window',
            res_model: 'hr.expense',
            view_mode: 'form',
            views: [[false, 'form']],
            context: context,
            target: 'current'
        });
    }

    action_create_attendance_manager() {
        if (this.userData.attendance) {
            // If there is an active attendance, open it
            this.actionService.doAction({
                name: _t("Attendance"),
                type: 'ir.actions.act_window',
                res_model: 'hr.attendance',
                view_mode: 'form',
                views: [[false, 'form']],
                res_id: this.userData.attendance,
                target: 'current'
            });
        } else {
            // Otherwise create new
            let context = {};
            if (this.userData.employee) {
                context['default_employee_id'] = this.userData.employee;
            }
            this.actionService.doAction({
                name: _t("Attendance"),
                type: 'ir.actions.act_window',
                res_model: 'hr.attendance',
                view_mode: 'form',
                views: [[false, 'form']],
                context: context,
                target: 'current'
            });
        }
    }
}

HRManagerDashboard.template = "hr_manager_dashboard.dashboard";
registry.category("actions").add("hr_manager_dashboard.dashboard", HRManagerDashboard);