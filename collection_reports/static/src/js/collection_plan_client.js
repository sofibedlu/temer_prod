/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class CollectionPlanClient extends Component {
    setup() {
        this.notification = useService("notification");
        this.rpc = useService("rpc");
        
        const today = new Date();
        const formatDate = (date) => {
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            return `${year}-${month}-${day}`;
        };
        
        this.state = useState({
            loading: true,
            total_clients: 0,
            no_of_sites: 0,
            stock_residences: 0,
            stock_shops: 0,
            total_receivable: 0.0,
            period_type: 'daily',
            date_from: formatDate(today),
            date_to: formatDate(today),
            date_period: formatDate(today),
            collected_amount_plan: 0.0,
            collected_amount_actual: 0.0,
            collected_amount_achievement: 0.0,
            collected_clients_plan: 0,
            collected_clients_actual: 0,
            collected_clients_achievement: 0.0,
            discount_amount: 0.0,
            discount_percentage: 0.0,
        });
        
        onWillStart(async () => {
            await this.loadData();
        });
    }
    
    _getDateRange() {
        const today = new Date();
        const formatDate = (date) => {
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            return `${year}-${month}-${day}`;
        };
        
        let date_from, date_to, date_period;
        
        if (this.state.period_type === 'daily') {
            date_from = formatDate(today);
            date_to = formatDate(today);
            date_period = `${date_from} to ${date_to}`;
        } else if (this.state.period_type === 'monthly') {
            const firstDay = new Date(today.getFullYear(), today.getMonth() - 1, 1);
            const lastDay = new Date(today.getFullYear(), today.getMonth(), 0);
            date_from = formatDate(firstDay);
            date_to = formatDate(lastDay);
            date_period = `${date_from} to ${date_to}`;
        } else if (this.state.period_type === 'yearly') {
            const firstDay = new Date(today.getFullYear() - 1, 0, 1);
            const lastDay = new Date(today.getFullYear() - 1, 11, 31);
            date_from = formatDate(firstDay);
            date_to = formatDate(lastDay);
            date_period = `${date_from} to ${date_to}`;
        } else if (this.state.period_type === 'all') {
            const firstDay = new Date(today.getFullYear() - 10, 0, 1);
            date_from = formatDate(firstDay);
            date_to = formatDate(today);
            date_period = 'All Data';
        } else { // custom
            date_from = this.state.date_from || formatDate(today);
            date_to = this.state.date_to || formatDate(today);
            date_period = `${date_from} to ${date_to}`;
        }
        
        return { date_from, date_to, date_period };
    }
    
    async loadData() {
        this.state.loading = true;
        try {
            const { date_from, date_to, date_period } = this._getDateRange();
            this.state.date_period = date_period;
            
            const result = await this.rpc("/collection_reports/api/collection_plan", {
                period_type: this.state.period_type,
                date_from: date_from,
                date_to: date_to,
            });
            
            if (result && result.success) {
                this.state.total_clients = result.data.total_clients || 0;
                this.state.no_of_sites = result.data.no_of_sites || 0;
                this.state.stock_residences = result.data.stock_residences || 0;
                this.state.stock_shops = result.data.stock_shops || 0;
                this.state.total_receivable = result.data.total_receivable || 0.0;
                this.state.collected_amount_plan = result.data.collected_amount_plan || 0.0;
                this.state.collected_amount_actual = result.data.collected_amount_actual || 0.0;
                this.state.collected_amount_achievement = result.data.collected_amount_achievement || 0.0;
                this.state.collected_clients_plan = result.data.collected_clients_plan || 0;
                this.state.collected_clients_actual = result.data.collected_clients_actual || 0;
                this.state.collected_clients_achievement = result.data.collected_clients_achievement || 0.0;
                this.state.discount_amount = result.data.discount_amount || 0.0;
                this.state.discount_percentage = result.data.discount_percentage || 0.0;
            } else {
                this.notification.add(result?.error || "Error loading data", { type: "danger" });
            }
        } catch (error) {
            console.error("Error loading data:", error);
            this.notification.add("Error loading data: " + error.message, { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }
    
    onPeriodTypeChange() {
        const { date_from, date_to } = this._getDateRange();
        this.state.date_from = date_from;
        this.state.date_to = date_to;
        this.loadData();
    }
    
    onDateChange() {
        this.loadData();
    }
    
    formatNumber(value) {
        return value ? value.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 }) : '0';
    }
    
    formatCurrency(value) {
        return value ? value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '0.00';
    }
    
    formatPercentage(value) {
        const percentage = value ? Math.min(value, 100) : 0;
        return percentage.toFixed(1) + '%';
    }
    
    async exportExcel() {
        try {
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = '/collection_reports/api/export_excel';
            form.target = '_blank';
            
            const reportTypeInput = document.createElement('input');
            reportTypeInput.type = 'hidden';
            reportTypeInput.name = 'report_type';
            reportTypeInput.value = 'collection_plan';
            form.appendChild(reportTypeInput);
            
            const { date_from, date_to } = this._getDateRange();
            
            const periodTypeInput = document.createElement('input');
            periodTypeInput.type = 'hidden';
            periodTypeInput.name = 'period_type';
            periodTypeInput.value = this.state.period_type || 'daily';
            form.appendChild(periodTypeInput);
            
            const dateFromInput = document.createElement('input');
            dateFromInput.type = 'hidden';
            dateFromInput.name = 'date_from';
            dateFromInput.value = date_from || '';
            form.appendChild(dateFromInput);
            
            const dateToInput = document.createElement('input');
            dateToInput.type = 'hidden';
            dateToInput.name = 'date_to';
            dateToInput.value = date_to || '';
            form.appendChild(dateToInput);
            
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
            form.action = '/collection_reports/api/export_pdf';
            form.target = '_blank';
            
            const reportTypeInput = document.createElement('input');
            reportTypeInput.type = 'hidden';
            reportTypeInput.name = 'report_type';
            reportTypeInput.value = 'collection_plan';
            form.appendChild(reportTypeInput);
            
            const { date_from, date_to } = this._getDateRange();
            
            const periodTypeInput = document.createElement('input');
            periodTypeInput.type = 'hidden';
            periodTypeInput.name = 'period_type';
            periodTypeInput.value = this.state.period_type || 'daily';
            form.appendChild(periodTypeInput);
            
            const dateFromInput = document.createElement('input');
            dateFromInput.type = 'hidden';
            dateFromInput.name = 'date_from';
            dateFromInput.value = date_from || '';
            form.appendChild(dateFromInput);
            
            const dateToInput = document.createElement('input');
            dateToInput.type = 'hidden';
            dateToInput.name = 'date_to';
            dateToInput.value = date_to || '';
            form.appendChild(dateToInput);
            
            document.body.appendChild(form);
            form.submit();
            document.body.removeChild(form);
        } catch (error) {
            console.error("Error exporting to PDF:", error);
            this.notification.add("Error exporting to PDF: " + error.message, { type: "danger" });
        }
    }
}

CollectionPlanClient.template = "collection_reports.CollectionPlanClient";
registry.category("actions").add("collection_reports.collection_plan", CollectionPlanClient);

