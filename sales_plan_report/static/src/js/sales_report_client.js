/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";

function formatDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

export class SalesReportClient extends Component {
    setup() {
        // Get report type from props or action context
        let reportType = 'wing';
        if (this.props && this.props.action && this.props.action.context) {
            reportType = this.props.action.context.default_report_type || 'wing';
        } else if (this.props && this.props.action && this.props.action.tag) {
            // If tag is supervisor_report, use supervisor
            if (this.props.action.tag === 'sales_plan_report.supervisor_report') {
                reportType = 'supervisor';
            }
        }
        
        // Set default dates to current week
        const today = new Date();
        const dayOfWeek = today.getDay();
        const diff = today.getDate() - dayOfWeek + (dayOfWeek === 0 ? -6 : 1); // Adjust to Monday
        const firstDay = new Date(today.setDate(diff));
        const lastDay = new Date(today.setDate(diff + 6));
        
        this.state = useState({
            loading: true,
            report_type: reportType,
            data: {},
            wings: [],
            supervisors: [],
            selected_wing_id: '',
            selected_supervisor_id: '',
            date_from: formatDate(firstDay),
            date_to: formatDate(lastDay),
            role_display: '',
            selected_wing_name: '',
        });
        
        onWillStart(async () => {
            if (this.state.report_type === 'wing') {
                await this.loadWings();
            } else {
                await this.loadSupervisors();
            }
            await this.loadData();
        });
    }
    
    async loadWings() {
        try {
            const response = await fetch("/sales_plan_report/api/get_wings", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                credentials: "same-origin",
                body: JSON.stringify({
                    jsonrpc: "2.0",
                    method: "call",
                    params: {},
                }),
            });
            
            if (response.ok) {
                const result = await response.json();
                let data = result;
                if (result && result.result) {
                    data = result.result;
                }
                if (data && data.success) {
                    this.state.wings = data.wings || [];
                }
            }
        } catch (error) {
            console.error("Error loading wings:", error);
        }
    }
    
    async loadSupervisors() {
        try {
            const response = await fetch("/sales_plan_report/api/get_supervisors", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                credentials: "same-origin",
                body: JSON.stringify({
                    jsonrpc: "2.0",
                    method: "call",
                    params: {},
                }),
            });
            
            if (response.ok) {
                const result = await response.json();
                let data = result;
                if (result && result.result) {
                    data = result.result;
                }
                if (data && data.success) {
                    this.state.supervisors = data.supervisors || [];
                }
            }
        } catch (error) {
            console.error("Error loading supervisors:", error);
        }
    }
    
    async loadData() {
        this.state.loading = true;
        try {
            const response = await fetch("/sales_plan_report/api/sales_report", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                credentials: "same-origin",
                body: JSON.stringify({
                    jsonrpc: "2.0",
                    method: "call",
                    params: {
                        report_type: this.state.report_type,
                        wing_id: this.state.selected_wing_id || null,
                        supervisor_id: this.state.selected_supervisor_id || null,
                        date_from: this.state.date_from,
                        date_to: this.state.date_to,
                    },
                }),
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            console.log("Sales Report API Response:", result);
            
            let data = result;
            if (result && result.result) {
                data = result.result;
            }
            
            if (data && data.success) {
                this.state.data = data.data || {};
                this.state.role_display = data.role_display || '';
                this.state.selected_wing_name = data.selected_wing_name || '';
                console.log("Sales Report Data loaded");
            } else {
                console.error("Error loading sales report data:", data?.error || result?.error || "Unknown error");
                this.state.data = {};
                this.state.role_display = data?.role_display || '';
                this.state.selected_wing_name = data?.selected_wing_name || '';
            }
        } catch (error) {
            console.error("Error loading sales report data:", error);
            this.state.data = {};
        } finally {
            this.state.loading = false;
        }
    }
    
    exportExcel() {
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = '/sales_plan_report/api/export_excel';
        
        const reportTypeInput = document.createElement('input');
        reportTypeInput.type = 'hidden';
        reportTypeInput.name = 'report_type';
        reportTypeInput.value = this.state.report_type;
        form.appendChild(reportTypeInput);
        
        if (this.state.report_type === 'wing' && this.state.selected_wing_id) {
            const wingIdInput = document.createElement('input');
            wingIdInput.type = 'hidden';
            wingIdInput.name = 'wing_id';
            wingIdInput.value = this.state.selected_wing_id;
            form.appendChild(wingIdInput);
        } else if (this.state.report_type === 'supervisor' && this.state.selected_supervisor_id) {
            const supervisorIdInput = document.createElement('input');
            supervisorIdInput.type = 'hidden';
            supervisorIdInput.name = 'supervisor_id';
            supervisorIdInput.value = this.state.selected_supervisor_id;
            form.appendChild(supervisorIdInput);
        }
        
        const dateFromInput = document.createElement('input');
        dateFromInput.type = 'hidden';
        dateFromInput.name = 'date_from';
        dateFromInput.value = this.state.date_from;
        form.appendChild(dateFromInput);
        
        const dateToInput = document.createElement('input');
        dateToInput.type = 'hidden';
        dateToInput.name = 'date_to';
        dateToInput.value = this.state.date_to;
        form.appendChild(dateToInput);
        
        document.body.appendChild(form);
        form.submit();
        document.body.removeChild(form);
    }
    
    exportPDF() {
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = '/sales_plan_report/api/export_pdf';
        
        const reportTypeInput = document.createElement('input');
        reportTypeInput.type = 'hidden';
        reportTypeInput.name = 'report_type';
        reportTypeInput.value = this.state.report_type;
        form.appendChild(reportTypeInput);
        
        if (this.state.report_type === 'wing' && this.state.selected_wing_id) {
            const wingIdInput = document.createElement('input');
            wingIdInput.type = 'hidden';
            wingIdInput.name = 'wing_id';
            wingIdInput.value = this.state.selected_wing_id;
            form.appendChild(wingIdInput);
        } else if (this.state.report_type === 'supervisor' && this.state.selected_supervisor_id) {
            const supervisorIdInput = document.createElement('input');
            supervisorIdInput.type = 'hidden';
            supervisorIdInput.name = 'supervisor_id';
            supervisorIdInput.value = this.state.selected_supervisor_id;
            form.appendChild(supervisorIdInput);
        }
        
        const dateFromInput = document.createElement('input');
        dateFromInput.type = 'hidden';
        dateFromInput.name = 'date_from';
        dateFromInput.value = this.state.date_from;
        form.appendChild(dateFromInput);
        
        const dateToInput = document.createElement('input');
        dateToInput.type = 'hidden';
        dateToInput.name = 'date_to';
        dateToInput.value = this.state.date_to;
        form.appendChild(dateToInput);
        
        document.body.appendChild(form);
        form.submit();
        document.body.removeChild(form);
    }
    
    onWingChange() {
        // Selection changed via dropdown, t-model handles the binding
    }
    
    onSupervisorChange() {
        // Selection changed via dropdown, t-model handles the binding
    }
}

SalesReportClient.template = "sales_plan_report.SalesReportClient";

registry.category("actions").add("sales_plan_report.wing_report", SalesReportClient);
registry.category("actions").add("sales_plan_report.supervisor_report", SalesReportClient);

