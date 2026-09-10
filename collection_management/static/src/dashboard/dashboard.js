/** @odoo-module */
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState, onMounted, useRef } from "@odoo/owl";
import { loadBundle } from "@web/core/assets";

export class CollectionDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        // Initialize state with default values
        this.state = useState({
            kpi: { portfolio: 0, collected: 0, overdue: 0, rate: 0 },
            charts: { cash_flow: { labels: [], data: [] }, overdue_site: { labels: [], data: [] } },
            lists: { top_overdue: [], upcoming: [] }
        });
        this.chartRef = useRef("chartCanvas");
        this.pieRef = useRef("pieCanvas");

        onWillStart(async () => {
            await loadBundle("web.chartjs_lib");
            await this.fetchData();
        });

        onMounted(() => {
            this.renderCharts();
        });
    }

    async fetchData() {
        const data = await this.orm.call("property.dashboard", "get_dashboard_data", []);
        this.state.kpi = data.kpi;
        this.state.charts = data.charts;
        this.state.lists = data.lists;
    }

    renderCharts() {
        if (this.chartRef.el) {
            new Chart(this.chartRef.el, {
                type: 'bar',
                data: {
                    labels: this.state.charts.cash_flow.labels,
                    datasets: [{
                        label: 'Expected Collection',
                        data: this.state.charts.cash_flow.data,
                        backgroundColor: '#00A09D'
                    }]
                }
            });
        }
        
        if (this.pieRef.el) {
            // Count how many sites we have
            const siteCount = this.state.charts.overdue_site.data.length;
            
            // Generate that many unique colors
            const dynamicColors = this.generateColors(siteCount);

            new Chart(this.pieRef.el, {
                type: 'doughnut',
                data: {
                    labels: this.state.charts.overdue_site.labels,
                    datasets: [{
                        data: this.state.charts.overdue_site.data,
                        backgroundColor: dynamicColors // Use the dynamic array
                    }]
                }
            });
        }
    }

    generateColors(count) {
        const colors = [];
        for (let i = 0; i < count; i++) {
            // Calculate hue: 0, 36, 72, etc. (if count is 10)
            const hue = Math.floor((360 / count) * i);
            // HSL: Hue, 70% Saturation, 60% Lightness
            colors.push(`hsl(${hue}, 70%, 60%)`);
        }
        return colors;
    }
    
    async openInstallment(id) {
        // Fetch the collection_id from the installment
        const installment = await this.orm.read('collection.installment', [id], ['collection_id']);
        if (installment && installment[0] && installment[0].collection_id) {
            this.action.doAction({
                type: 'ir.actions.act_window',
                res_model: 'collection.order', 
                res_id: installment[0].collection_id[0],
                views: [[false, 'form']],
                target: 'current',
            });
        }
    }

    formatCurrency(value) {
        if (value === undefined || value === null) {
            return "0.00";
        }
        return value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }
}

CollectionDashboard.template = "collection_management.Dashboard";
registry.category("actions").add("collection_management.dashboard", CollectionDashboard);