/** @odoo-module */

import { Component, onWillStart, useState, markup } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session";
import { _t } from "@web/core/l10n/translation";

export class HRDashboard extends Component {
    static props = {
        action: Object,
        actionId: Number,
        className: { type: String, optional: true },
    }; // To avoid the warning HRManagerDashboard does not have static props..
    setup() {
        this.actionService = useService("action");
        this.rpc = useService("rpc");
        
        // Reactive state for the view
        this.state = useState({
            user_name: "",
            leave_count: 0,
            allocated_leave_count: 0,
            attendance_count: 0,
            expense_count: 0,
            contract_count: 0,
            // Store HTML snippets here
            birthday_data: "",
            anniversary_data: "",
            announcement_data: "",
            expense_data: "",
            attendance_data: "",
            leave_data: "",
        });

        // Store employee/user data globally for this component so we don't fetch on every click
        this.userData = {};

        onWillStart(async () => {
            await this.fetchAllData();
        });
    }

    async fetchAllData() {
        // 1. Fetch User/Employee Context (Replacing /get_user_name)
        // Note: Ideally, convert your Python controller to type='json' and return a dict directly.
        // Assuming current controllers return JSON strings via HTTP as per legacy code:
        try {
            const userDataResult = await this.rpc("/get_user_name");
            // If the controller returns a string, parse it. If it's already JSON, remove JSON.parse
            this.userData = typeof userDataResult === 'string' ? JSON.parse(userDataResult) : userDataResult;
            
            // Update State for Top Bar
            this.state.user_name = this.userData.user || "";
            this.state.leave_count = this.userData.leave_count || 0;
            this.state.allocated_leave_count = this.userData.allocated_leave_count || 0;
            this.state.attendance_count = this.userData.attendance_count || 0;
            this.state.expense_count = this.userData.expense_count || 0;
            this.state.contract_count = this.userData.contract_count || 0;

        } catch (e) {
            console.error("Error fetching user data", e);
        }

        // 2. Fetch HTML Snippets (Replacing the $.get calls)
        // We run these in parallel for speed
        const endpoints = [
            '/get_employee_birhday_data',
            '/get_employee_anniversary_data',
            '/get_annoucement_data',
            '/get_employee_expense_data',
            '/get_employee_attendance_data',
            '/get_employee_leave_data'
        ];

        const results = await Promise.all(endpoints.map(url => this.rpc(url).catch(() => "")));
        // Added markup so it works well with t-raw for html rendering, instead of putting out as plain text
        this.state.birthday_data = markup(results[0] || "");
        this.state.anniversary_data = markup(results[1] || "");
        this.state.announcement_data = markup(results[2] || "");
        this.state.expense_data = markup(results[3] || "");
        this.state.attendance_data = markup(results[4] || "");
        this.state.leave_data = markup(results[5] || "");
    }

    // -------------------------------------------------------------------------
    // Actions
    // -------------------------------------------------------------------------

    openCmpPolicy(event) {
        // stopPropagation is handled by OWL modifiers usually, but explicit here if needed
        const currentCompanyId = session.user_context.allowed_company_ids[0];
        if (currentCompanyId) {
            this.actionService.doAction({
                name: _t("Company Policy"),
                type: 'ir.actions.act_window',
                res_model: 'sh.company.policy.wizard',
                view_mode: 'form',
                views: [[false, 'form']],
                context: {
                    'default_company_id': currentCompanyId,
                },
                target: 'new'
            });
        }
    }

    openEmployeeContract() {
        if (this.userData.employee) {
            this.actionService.doAction({
                name: _t("Contract"),
                type: 'ir.actions.act_window',
                res_model: 'hr.contract',
                view_mode: 'tree,kanban,form',
                views: [
                    [false, 'tree'],
                    [false, 'kanban'],
                    [false, 'form'],
                ],
                domain: [['employee_id', '=', this.userData.employee]],
                target: 'current'
            });
        }
    }

    openEmployeeExpense() {
        if (this.userData.employee) {
            this.actionService.doAction({
                name: _t("Expense"),
                type: 'ir.actions.act_window',
                res_model: 'hr.expense',
                view_mode: 'tree,kanban,form,graph,pivot,activity',
                views: [
                    [false, 'tree'],
                    [false, 'kanban'],
                    [false, 'form'],
                    [false, 'graph'],
                    [false, 'pivot'],
                    [false, 'activity']
                ],
                domain: [['employee_id', '=', this.userData.employee]],
                target: 'current'
            });
        }
    }

    openEmployeeAttendance() {
        if (this.userData.employee) {
            this.actionService.doAction({
                name: _t("Attendance"),
                type: 'ir.actions.act_window',
                res_model: 'hr.attendance',
                view_mode: 'tree,kanban,form',
                views: [
                    [false, 'tree'],
                    [false, 'kanban'],
                    [false, 'form']
                ],
                domain: [['employee_id', '=', this.userData.employee]],
                target: 'current'
            });
        }
    }

    openEmployeeLeave() {
        if (this.userData.employee) {
            this.actionService.doAction({
                name: _t("Leaves"),
                type: 'ir.actions.act_window',
                res_model: 'hr.leave',
                view_mode: 'calendar,tree,form,activity',
                views: [
                    [false, 'calendar'],
                    [false, 'tree'],
                    [false, 'form'],
                    [false, 'activity']
                ],
                domain: [['employee_id', '=', this.userData.employee]],
                target: 'current'
            });
        }
    }

    actionCreateLeave() {
        if (this.userData.employee) {
            this.actionService.doAction({
                name: _t("Leave Request"),
                type: 'ir.actions.act_window',
                res_model: 'hr.leave',
                view_mode: 'form',
                views: [[false, 'form']],
                context: { 'default_employee_id': this.userData.employee },
                target: 'current'
            });
        }
    }

    actionCreateExpense() {
        if (this.userData.employee) {
            this.actionService.doAction({
                name: _t("Expense"),
                type: 'ir.actions.act_window',
                res_model: 'hr.expense',
                view_mode: 'form',
                views: [[false, 'form']],
                context: { 'default_employee_id': this.userData.employee },
                target: 'current'
            });
        }
    }

    actionCreateAttendance() {
        if (this.userData.attendance) {
            this.actionService.doAction({
                name: _t("Attendance"),
                type: 'ir.actions.act_window',
                res_model: 'hr.attendance',
                view_mode: 'form',
                views: [[false, 'form']],
                res_id: this.userData.attendance,
                target: 'current'
            });
        } else if (this.userData.employee) {
            this.actionService.doAction({
                name: _t("Attendance"),
                type: 'ir.actions.act_window',
                res_model: 'hr.attendance',
                view_mode: 'form',
                views: [[false, 'form']],
                context: { 'default_employee_id': this.userData.employee },
                target: 'current'
            });
        }
    }
}

// Ensure this matches the template name in your XML file
HRDashboard.template = "hr_dashboard.dashboard";

registry.category("actions").add("hr_dashboard.dashboard", HRDashboard);