/** @odoo-module **/

import { Component, useState, onWillStart, useEffect, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class PlanDocumentClient extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.notification = useService("notification");
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
            filtered_data: [],
            date_from: formatDate(firstDay),
            date_to: formatDate(lastDay),
            show_all_dates: false,
            range_type: 'custom',
            search_text: '',
            role_display: '',
            selected_wing_name: '',
            wings: [],
            selected_wing_id: '',
        });
        
        onWillStart(async () => {
            // Check user role - only managers should see this
            await this.checkUserRole();
            await this.loadWings();
            await this.loadData();
        });
        
        onWillUnmount(() => {
            this.isMounted = false;
        });
        
        useEffect(
            (search_text) => {
                if (this.isMounted) {
                    this.filterData();
                }
            },
            () => [this.state.search_text, this.state.data]
        );
    }

    filterData() {
        let filtered = [...this.state.data];
        
        // Filter by search text
        if (this.state.search_text && this.state.search_text.trim()) {
            const searchLower = this.state.search_text.toLowerCase().trim();
            filtered = filtered.filter(row => {
                const name = (row.name || '').toLowerCase();
                const supervisor = (row.supervisor_name || '').toLowerCase();
                const wing = (row.wing_name || '').toLowerCase();
                return name.includes(searchLower) || supervisor.includes(searchLower) || wing.includes(searchLower);
            });
        }
        
        this.state.filtered_data = filtered;
    }

    onSearchChange() {
        this.filterData();
    }

    onRangeChange() {
        const today = new Date();
        const formatDate = (date) => {
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            return `${year}-${month}-${day}`;
        };
        if (this.state.range_type === 'weekly') {
            const toDate = new Date(today);
            toDate.setDate(toDate.getDate() + 7);
            this.state.date_from = formatDate(today);
            this.state.date_to = formatDate(toDate);
        } else if (this.state.range_type === 'monthly') {
            const toDate = new Date(today);
            toDate.setDate(toDate.getDate() + 30);
            this.state.date_from = formatDate(today);
            this.state.date_to = formatDate(toDate);
        } else if (this.state.range_type === 'quarterly') {
            const toDate = new Date(today);
            toDate.setDate(toDate.getDate() + 90);
            this.state.date_from = formatDate(today);
            this.state.date_to = formatDate(toDate);
        } else if (this.state.range_type === 'yearly') {
            const toDate = new Date(today);
            toDate.setDate(toDate.getDate() + 365);
            this.state.date_from = formatDate(today);
            this.state.date_to = formatDate(toDate);
        }
        this.state.show_all_dates = false;
        this.loadData();
    }

    async checkUserRole() {
        // Check if user is a manager (Sales Manager or Wing Manager)
        // This is handled server-side in the API, but we can add client-side check too
        // The API will return error if user is not a manager
    }

    async loadWings() {
        try {
            const result = await this.rpc("/sales_plan/get_wings_for_plan_document", {});
            if (result?.success) {
                this.state.wings = result.wings || [];
                if (this.state.wings.length === 1) {
                    this.state.selected_wing_id = this.state.wings[0].id;
                }
            }
        } catch (error) {
            console.warn("Failed to load wings:", error);
        }
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
        this.loadData();
    }

    async loadData() {
        if (!this.isMounted) return;
        this.state.loading = true;
        try {
            const data = await this.rpc("/sales_plan/api/plan_document", {
                date_from: this.state.show_all_dates ? null : this.state.date_from,
                date_to: this.state.show_all_dates ? null : this.state.date_to,
                search_text: this.state.search_text,
                wing_id: this.state.selected_wing_id || null,
            });
            
            if (!this.isMounted) return;
            
            if (data?.success) {
                this.state.data = data.data || [];
                this.state.role_display = data.role_display || '';
                this.state.selected_wing_name = data.selected_wing_name || '';
                this.filterData();
            } else {
                this.state.data = [];
                this.state.filtered_data = [];
                this.state.role_display = '';
                this.state.selected_wing_name = '';
                this.notification.add(data?.error || "Failed to load plan document data.", { type: "danger" });
            }
        } catch (error) {
            if (this.isMounted) {
                console.error("Error loading data:", error);
                this.notification.add(`Error loading plan document: ${error.message || error}`, { type: "danger" });
            } else {
                console.warn("Load data completed after component unmounted, ignoring error:", error);
            }
        } finally {
            if (this.isMounted) {
                this.state.loading = false;
            }
        }
    }

    onExportExcel() {
        const params = new URLSearchParams();
        if (!this.state.show_all_dates) {
            if (this.state.date_from) params.append('date_from', this.state.date_from);
            if (this.state.date_to) params.append('date_to', this.state.date_to);
        }
        if (this.state.search_text) params.append('search_text', this.state.search_text);
        if (this.state.selected_wing_id) params.append('wing_id', this.state.selected_wing_id);
        const url = `/sales_plan/api/plan_document_export?${params.toString()}`;
        window.open(url, "_blank");
    }

    formatDate(dateStr) {
        if (!dateStr) return '';
        const date = new Date(dateStr + 'T00:00:00');
        const day = String(date.getDate()).padStart(2, '0');
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const year = date.getFullYear();
        return `${day}/${month}/${year}`;
    }
}

PlanDocumentClient.template = "sales_plan_module.PlanDocumentClient";

registry.category("actions").add("sales_plan_module.plan_document", PlanDocumentClient);

