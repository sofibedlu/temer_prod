/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useRef, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { loadJS } from "@web/core/assets";
import { getColor } from "@web/core/colors/colors";

const actionRegistry = registry.category("actions");

export class WebsiteLeadsDashboard extends Component {
    setup() {
        this.orm = useService('orm');
        this.action = useService("action");
        
        // Initialize state with default values
        this.stats = useState({
            websiteLeadDataByStage: [],
            totalWebsiteLeads: 0,
            errorMessage: false,
            isLoading: true,
            chartsLoaded: false
        });

        // Chart references
        this.websiteChartRef = useRef("websiteChartRef");
        this.websiteChartPieRef = useRef("websiteChartPieRef");
        this.charts = {
            websiteChart: null,
            websiteChartPie: null
        };

        onWillStart(async () => {
            try {
                this.stats.isLoading = true;
                await this.loadChartLibraries();
                await this.fetchStats();
            } catch (error) {
                console.error("Error in onWillStart:", error);
                this.handleLoadError(error);
            } finally {
                this.stats.isLoading = false;
            }
        });

        onMounted(() => {
            if (this.stats.chartsLoaded) {
                this.renderCharts();
            }
        });

        onWillUnmount(() => {
            this.destroyAllCharts();
        });
    }

    async loadChartLibraries() {
        try {
            await Promise.all([
                loadJS("https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js"),
                loadJS("https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0/dist/chartjs-plugin-datalabels.min.js")
            ]);
            
            if (window.Chart && window.ChartDataLabels) {
                Chart.register(window.ChartDataLabels);
                this.stats.chartsLoaded = true;
            } else {
                throw new Error("Chart libraries not loaded properly");
            }
        } catch (error) {
            console.warn("Chart library loading failed:", error);
            this.stats.chartsLoaded = false;
            this.stats.errorMessage = "Charts disabled - failed to load libraries";
        }
    }

    async fetchStats() {
        try {
            const websiteSource = await this.orm.search("utm.source", [['name', '=', 'Website']], { limit: 1 });
            const websiteDomain = websiteSource.length ? [['source_id', '=', websiteSource[0]]] : [];
            
            const [websiteLeadDataByStage, totalWebsiteLeads] = await Promise.all([
                this.orm.readGroup("crm.lead", websiteDomain, ['stage_id'], ['stage_id']),
                this.orm.searchCount("crm.lead", websiteDomain)
            ]);

            // Validate and process data
            const processedData = (websiteLeadDataByStage || []).map(item => ({
                stage_id: item.stage_id || [0, "Unknown"],
                stage_id_count: item.stage_id_count || 0
            }));

            this.stats.websiteLeadDataByStage = processedData;
            this.stats.totalWebsiteLeads = totalWebsiteLeads || processedData.reduce(
                (sum, item) => sum + item.stage_id_count, 0
            );
            
            console.log("Website chart data", this.stats.websiteLeadDataByStage);
            console.log("Total website leads:", this.stats.totalWebsiteLeads);
        } catch (error) {
            console.error("Data fetch error:", error);
            this.handleLoadError(error);
        }
    }

    handleLoadError(error) {
        this.stats.errorMessage = "Failed to load data. Showing sample data.";
        
        // Fallback data
        this.stats.websiteLeadDataByStage = [
            { stage_id: [1, "New"], stage_id_count: 15 },
            { stage_id: [2, "Qualified"], stage_id_count: 8 },
            { stage_id: [3, "Proposal"], stage_id_count: 5 },
            { stage_id: [4, "Negotiation"], stage_id_count: 3 },
            { stage_id: [5, "Won"], stage_id_count: 2 }
        ];
        this.stats.totalWebsiteLeads = this.stats.websiteLeadDataByStage.reduce(
            (sum, item) => sum + item.stage_id_count, 0
        );
    }

    destroyAllCharts() {
        Object.values(this.charts).forEach(chart => {
            if (chart) {
                chart.destroy();
            }
        });
        this.charts = {
            websiteChart: null,
            websiteChartPie: null
        };
    }

    renderCharts() {
        if (this.stats.isLoading || !this.stats.chartsLoaded) return;
        
        this.destroyAllCharts();

        try {
            // Bar Chart
            if (this.websiteChartRef.el && this.stats.websiteLeadDataByStage.length) {
                this.renderBarChart();
            }

            // Pie Chart
            if (this.websiteChartPieRef.el && this.stats.websiteLeadDataByStage.length) {
                this.renderPieChart();
            }
        } catch (error) {
            console.error("Chart rendering error:", error);
            this.stats.errorMessage = "Failed to render charts";
        }
    }

    renderBarChart() {
        const labels = this.stats.websiteLeadDataByStage.map(item => item.stage_id[1]);
        const data = this.stats.websiteLeadDataByStage.map(item => item.stage_id_count);
        const backgroundColors = labels.map((_, index) => getColor(index + 35));

        this.charts.websiteChart = new Chart(this.websiteChartRef.el, {
            type: "bar",
            data: {
                labels: labels,
                datasets: [{
                    label: 'Website Leads by Stage',
                    data: data,
                    backgroundColor: backgroundColors,
                    borderColor: backgroundColors.map(color => color.replace('0.6', '1')),
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: `Total Website Leads: ${this.stats.totalWebsiteLeads}`,
                        font: {
                            size: 16
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                const total = this.chart.data.datasets[0].data.reduce((a, b) => a + b, 0);
                                const percentage = ((value / total) * 100).toFixed(1);
                                return `${value} (${percentage}%)`;
                            }
                        }
                    }
                },
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const value = context.raw;
                                const percentage = ((value / total) * 100).toFixed(1);
                                return `${context.dataset.label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }

    renderPieChart() {
        const labels = this.stats.websiteLeadDataByStage.map(item => item.stage_id[1]);
        const data = this.stats.websiteLeadDataByStage.map(item => item.stage_id_count);
        const backgroundColors = labels.map((_, index) => getColor(index + 35));

        this.charts.websiteChartPie = new Chart(this.websiteChartPieRef.el, {
            type: "pie",
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: backgroundColors,
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: `Total Website Leads: ${this.stats.totalWebsiteLeads}`,
                        font: {
                            size: 16
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const value = context.raw;
                                const percentage = ((value / total) * 100).toFixed(1);
                                return `${context.label}: ${value} (${percentage}%)`;
                            }
                        }
                    },
                    datalabels: {
                        formatter: function(value, context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${percentage}%`;
                        },
                        color: '#fff',
                        anchor: 'center',
                        align: 'center',
                        font: { weight: 'bold' }
                    }
                }
            }
        });
    }

    goToWebsiteLeadsPage() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "crm.lead",
            view_mode: "list",
            views: [[false, "list"]],
            target: "current",
            domain: [["source_id.name", "=", "Website"]],
            context: {
                search_default_website_leads: true
            }
        });
    }
}

WebsiteLeadsDashboard.template = "crm_dashboard.website_leads_dashboard";
actionRegistry.add("website_leads_dashboard", WebsiteLeadsDashboard);