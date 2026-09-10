/** @odoo-module **/

import { Component, useState, onWillStart, useEffect, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class CustomerServiceReportClient extends Component {
    setup() {
        this.notification = useService("notification");
        this.isMounted = true;
        
        const today = new Date();
        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
        const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);
        
        const formatDate = (date) => {
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            return `${year}-${month}-${day}`;
        };
        
        this.state = useState({
            loading: true,
            data: [],
            filtered_data: [],
            date_from: formatDate(firstDay),
            date_to: formatDate(lastDay),
            show_all_dates: false,
            search_text: '',
        });
        
        onWillStart(async () => {
            await this.loadData();
        });
        
        onWillUnmount(() => {
            this.isMounted = false;
        });
        
        useEffect(
            () => {
                if (this.isMounted) {
                    this.filterData();
                }
            },
            () => [this.state.search_text, this.state.data]
        );
    }
    
    filterData() {
        let filtered = [...this.state.data];
        if (this.state.search_text && this.state.search_text.trim()) {
            const searchLower = this.state.search_text.toLowerCase().trim();
            filtered = filtered.filter(row => {
                const customer = (row.customer || '').toLowerCase();
                const collectionOrder = (row.collection_order || '').toLowerCase();
                const level = (row.satisfaction_level || '').toLowerCase();
                const remark = (row.remark || '').toLowerCase();
                return customer.includes(searchLower) || 
                       collectionOrder.includes(searchLower) || 
                       level.includes(searchLower) ||
                       remark.includes(searchLower);
            });
        }
        this.state.filtered_data = filtered;
    }
    
    onSearchChange() {
        this.filterData();
    }
    
    onShowAllDatesChange() {
        if (this.state.show_all_dates) {
            this.state.date_from = '';
            this.state.date_to = '';
        } else {
            const today = new Date();
            const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
            const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);
            const formatDate = (date) => {
                const year = date.getFullYear();
                const month = String(date.getMonth() + 1).padStart(2, '0');
                const day = String(date.getDate()).padStart(2, '0');
                return `${year}-${month}-${day}`;
            };
            this.state.date_from = formatDate(firstDay);
            this.state.date_to = formatDate(lastDay);
        }
    }

    async loadData() {
        if (!this.isMounted) return;
        this.state.loading = true;
        try {
            const response = await fetch("/collection_reports/api/customer_service", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "same-origin",
                body: JSON.stringify({
                    jsonrpc: "2.0",
                    method: "call",
                    params: {
                        date_from: this.state.show_all_dates ? null : this.state.date_from,
                        date_to: this.state.show_all_dates ? null : this.state.date_to,
                    },
                }),
            });
            
            if (!this.isMounted) return;
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            
            const result = await response.json();
            let data = result?.result || result;
            
            if (data?.success && this.isMounted) {
                this.state.data = data.data || [];
                this.filterData();
            } else if (this.isMounted) {
                this.state.data = [];
                this.state.filtered_data = [];
            }
        } catch (error) {
            if (this.isMounted) {
                console.error("Error loading data:", error);
                this.state.data = [];
                this.state.filtered_data = [];
            }
        } finally {
            if (this.isMounted) {
                this.state.loading = false;
            }
        }
    }

    async exportExcel() {
        if (!this.state.data || this.state.data.length === 0) {
            this.notification.add("No data to export", { type: "warning" });
            return;
        }

        try {
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = '/collection_reports/api/export_excel';
            
            const reportTypeInput = document.createElement('input');
            reportTypeInput.type = 'hidden';
            reportTypeInput.name = 'report_type';
            reportTypeInput.value = 'customer_service';
            form.appendChild(reportTypeInput);
            
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
            
            document.body.appendChild(form);
            form.submit();
            document.body.removeChild(form);
        } catch (error) {
            console.error("Error exporting Excel:", error);
            this.notification.add("Error exporting Excel", { type: "danger" });
        }
    }

    async exportPDF() {
        this.notification.add("PDF export functionality to be implemented", { type: "info" });
    }
}

CustomerServiceReportClient.template = "collection_reports.CustomerServiceReportClient";
registry.category("actions").add("collection_reports.customer_service", CustomerServiceReportClient);

