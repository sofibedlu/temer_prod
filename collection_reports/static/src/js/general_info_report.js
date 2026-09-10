/** @odoo-module **/

import { Component, useState, onWillStart, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class GeneralInfoReport extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.isMounted = true;
        
        // Set default dates to current month
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
            totals: {},
            date_from: formatDate(firstDay),
            date_to: formatDate(lastDay),
        });
        
        onWillStart(async () => {
            await this.loadData();
        });
        
        onWillUnmount(() => {
            this.isMounted = false;
        });
    }

    async loadData() {
        if (!this.isMounted) return;
        this.state.loading = true;
        try {
            const result = await this.rpc("/collection_reports/api/general_info_detailed", {
                method: "POST",
                params: {
                    date_from: this.state.date_from || '',
                    date_to: this.state.date_to || '',
                }
            });
            if (!this.isMounted) return;
            if (result && result.success) {
                if (this.isMounted) {
                    this.state.data = result.data || [];
                    this.state.totals = result.totals || {};
                }
            } else {
                if (this.isMounted) {
                    this.state.data = [];
                    this.state.totals = {};
                }
            }
        } catch (error) {
            if (this.isMounted) {
                console.error("Error loading data:", error);
                this.state.data = [];
                this.state.totals = {};
            } else {
                console.warn("Load data completed after component unmounted, ignoring error:", error);
            }
        } finally {
            if (this.isMounted) {
                this.state.loading = false;
            }
        }
    }

    async exportExcel() {
        try {
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = '/collection_reports/api/export_excel';
            
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = 'report_type';
            input.value = 'general_info';
            form.appendChild(input);
            
            document.body.appendChild(form);
            form.submit();
            document.body.removeChild(form);
        } catch (error) {
            console.error("Error exporting Excel:", error);
        }
    }

    async exportPDF() {
        try {
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = '/collection_reports/api/export_pdf';
            
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = 'report_type';
            input.value = 'general_info';
            form.appendChild(input);
            
            document.body.appendChild(form);
            form.submit();
            document.body.removeChild(form);
        } catch (error) {
            console.error("Error exporting PDF:", error);
        }
    }
}

GeneralInfoReport.template = "collection_reports.GeneralInfoReport";

registry.category("actions").add("collection_reports.general_info_report", GeneralInfoReport);

