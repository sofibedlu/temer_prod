/** @odoo-module **/

import { Component, useState, onWillStart, useEffect, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class SupervisorSalesReportClient extends Component {
    setup() {
        this.notification = useService("notification");
        this.rpc = useService("rpc");
        this.action = useService("action");
        this.isMounted = true;
        
        const today = new Date();
        const formatDate = (date) => {
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            return `${year}-${month}-${day}`;
        };
        
        this.state = useState({
            loading: false,
            show_report: false,
            data: {
                prospect: 0,
                follow_up: {},
                reservation: 0,
                sold: 0,
            },
            date_from: formatDate(today),
            date_to: formatDate(today),
            show_all_dates: false,
            user_role: '',
            is_admin: false,
            available_wings: [],
            selected_wing_id: null,
            selected_wing_name: null,
            role_display: '',
        });
        
        onWillStart(async () => {
            // Pre-load user/wing info without fetching report data
            await this._loadUserInfo();
        });
        
        onWillUnmount(() => {
            this.isMounted = false;
        });
    }
    
    async _loadUserInfo() {
        try {
            const result = await this.rpc("/supervisor_sales_report/api/report_data", {
                date_from: this.state.date_from,
                date_to: this.state.date_to,
                info_only: true,
            });
            if (this.isMounted && result && result.success) {
                this.state.user_role = result.user_role || '';
                this.state.role_display = result.role_display || '';
                this.state.is_admin = result.is_admin || false;
                if (result.available_wings) {
                    this.state.available_wings = result.available_wings;
                }
                if (result.selected_wing_name) {
                    this.state.selected_wing_name = result.selected_wing_name;
                }
            }
        } catch (e) {
            // non-critical, ignore
        }
    }

    async onShowReport() {
        this.state.show_report = true;
        await this.loadData();
    }

    onShowAllDatesChange() {
        if (this.state.show_all_dates) {
            this.state.date_from = '';
            this.state.date_to = '';
        } else {
            const today = new Date();
            const formatDate = (date) => {
                const year = date.getFullYear();
                const month = String(date.getMonth() + 1).padStart(2, '0');
                const day = String(date.getDate()).padStart(2, '0');
                return `${year}-${month}-${day}`;
            };
            this.state.date_from = formatDate(today);
            this.state.date_to = formatDate(today);
        }
        if (this.state.show_report) {
            this.loadData();
        }
    }
    
    onDateChange() {
        if (!this.state.show_all_dates && this.state.show_report) {
            this.loadData();
        }
    }

    async loadData() {
        if (!this.isMounted) return;
        this.state.loading = true;
        try {
            const params = {
                date_from: this.state.show_all_dates ? null : this.state.date_from,
                date_to: this.state.show_all_dates ? null : this.state.date_to,
            };
            
            // Add wing_id for admin users
            if (this.state.is_admin && this.state.selected_wing_id) {
                params.wing_id = this.state.selected_wing_id;
            }
            
            const result = await this.rpc("/supervisor_sales_report/api/report_data", params);
            
            // Debug logging
            console.log("API Response:", result);
            if (result && result.data) {
                console.log("Response data - reservation:", result.data.reservation, "sold:", result.data.sold);
            }
            
            if (this.isMounted && result && result.success) {
                this.state.data = result.data;
                this.state.user_role = result.user_role || '';
                this.state.role_display = result.role_display || '';
                this.state.is_admin = result.is_admin || false;
                if (result.available_wings) {
                    this.state.available_wings = result.available_wings;
                }
                if (result.selected_wing_name) {
                    this.state.selected_wing_name = result.selected_wing_name;
                } else {
                    this.state.selected_wing_name = null;
                }
            } else if (this.isMounted) {
                this.notification.add(
                    result.error || "Error loading report data",
                    { type: "danger" }
                );
            }
        } catch (error) {
            if (this.isMounted) {
                console.error("Error loading supervisor sales report:", error);
                this.notification.add("Error loading report data", { type: "danger" });
            }
        } finally {
            if (this.isMounted) {
                this.state.loading = false;
            }
        }
    }
    
    onWingChange() {
        if (this.state.show_report) {
            this.loadData();
        }
    }
    
    getFollowUpColumns() {
        const followUp = this.state.data.follow_up || {};
        return Object.keys(followUp).filter(key => followUp[key] > 0);
    }
    
    getFollowUpTotal() {
        const followUp = this.state.data.follow_up || {};
        return Object.values(followUp).reduce((sum, val) => sum + (val || 0), 0);
    }
    
    async exportExcel() {
        try {
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = '/supervisor_sales_report/api/export_excel';
            
            const dateFromInput = document.createElement('input');
            dateFromInput.type = 'hidden';
            dateFromInput.name = 'date_from';
            dateFromInput.value = this.state.show_all_dates ? '' : (this.state.date_from || '');
            form.appendChild(dateFromInput);
            
            const dateToInput = document.createElement('input');
            dateToInput.type = 'hidden';
            dateToInput.name = 'date_to';
            dateToInput.value = this.state.show_all_dates ? '' : (this.state.date_to || '');
            form.appendChild(dateToInput);
            
            if (this.state.selected_wing_id) {
                const wingIdInput = document.createElement('input');
                wingIdInput.type = 'hidden';
                wingIdInput.name = 'wing_id';
                wingIdInput.value = this.state.selected_wing_id;
                form.appendChild(wingIdInput);
            }
            
            document.body.appendChild(form);
            form.submit();
            document.body.removeChild(form);
            this.notification.add("Excel file downloaded successfully", { type: "success" });
        } catch (error) {
            console.error("Error exporting to Excel:", error);
            this.notification.add("Error exporting to Excel: " + error.message, { type: "danger" });
        }
    }
    
    async exportPDF() {
        try {
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = '/supervisor_sales_report/api/export_pdf';
            form.target = '_blank';
            
            const dateFromInput = document.createElement('input');
            dateFromInput.type = 'hidden';
            dateFromInput.name = 'date_from';
            dateFromInput.value = this.state.show_all_dates ? '' : (this.state.date_from || '');
            form.appendChild(dateFromInput);
            
            const dateToInput = document.createElement('input');
            dateToInput.type = 'hidden';
            dateToInput.name = 'date_to';
            dateToInput.value = this.state.show_all_dates ? '' : (this.state.date_to || '');
            form.appendChild(dateToInput);
            
            if (this.state.selected_wing_id) {
                const wingIdInput = document.createElement('input');
                wingIdInput.type = 'hidden';
                wingIdInput.name = 'wing_id';
                wingIdInput.value = this.state.selected_wing_id;
                form.appendChild(wingIdInput);
            }
            
            document.body.appendChild(form);
            form.submit();
            document.body.removeChild(form);
        } catch (error) {
            console.error("Error exporting to PDF:", error);
            this.notification.add("Error exporting to PDF: " + error.message, { type: "danger" });
        }
    }
    
    async onNumberClick(countType, activityType = null) {
        try {
            const params = {
                count_type: countType,
                date_from: this.state.show_all_dates ? null : this.state.date_from,
                date_to: this.state.show_all_dates ? null : this.state.date_to,
            };
            
            if (activityType) {
                params.activity_type = activityType;
            }
            
            if (this.state.is_admin && this.state.selected_wing_id) {
                params.wing_id = this.state.selected_wing_id;
            }
            
            const result = await this.rpc("/supervisor_sales_report/api/get_detail_action", params);
            
            if (result && result.success && result.action) {
                await this.action.doAction(result.action);
            } else {
                this.notification.add(
                    result.error || "Error opening detail view",
                    { type: "danger" }
                );
            }
        } catch (error) {
            console.error("Error opening detail view:", error);
            this.notification.add("Error opening detail view: " + error.message, { type: "danger" });
        }
    }
}

SupervisorSalesReportClient.template = "supervisor_sales_report.SupervisorSalesReportClient";

registry.category("actions").add("supervisor_sales_report.report", SupervisorSalesReportClient);

