/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useRef, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { loadJS } from "@web/core/assets";
import { getColor } from "@web/core/colors/colors";

const actionRegistry = registry.category("actions");

export class PropertySiteDashboard extends Component {
    setup() {
        this.orm = useService('orm');
        this.action = useService("action");
        this.siteData = useState([]);
        this.canvasRef = useRef("canvas");
        this.canvasReftwo = useRef("canvastwo");
        this.chart = null;
        this.charttwo = null;

        onWillStart(async () => {
            await loadJS(["/web/static/lib/Chart/Chart.js"]);
            await this.fetchSiteData();
        });

        onMounted(() => {
            this.renderCharts();
        });

        onWillUnmount(() => {
            if (this.chart) {
                this.chart.destroy();
                this.chart = null;
            }
            if (this.charttwo) {
                this.charttwo.destroy();
                this.charttwo = null;
            }
        });
    }

    // async fetchSiteData() {
    //     this.siteData = await this.orm.call("property.site", "get_site_status_data", []);
    //     console.log("llllllllllllllllllllllllllllllllll",this.siteData)
    // }

    async fetchSiteData() {
    try {
        const data = await this.orm.call("property.site", "get_site_status_data", []);
        console.log("🔍 raw site data from backend:", data);
        if (!data || !data.length) {
            console.warn("No rows returned! Check that your Python method is returning dictfetchall().");
        }
        this.siteData = data;
        this.renderCharts();
    } catch (e) {
        console.error("Error fetching site data:", e);
    }
}


    renderCharts() {
        if (!this.canvasRef.el || !this.canvasReftwo.el || !this.siteData.length) {
            return;
        }

        // Prepare data for charts
        const siteNames = this.siteData.map(site => site.site_name);
        const statusData = {
            reserved: this.siteData.map(site => site.reserved_count),
            requested: this.siteData.map(site => site.requested_count),
            cancelled: this.siteData.map(site => site.cancelled_count),
            expired: this.siteData.map(site => site.expired_count),
            sold: this.siteData.map(site => site.sold_count)
        };

        // Destroy existing charts if they exist
        if (this.chart) {
            this.chart.destroy();
            this.chart = null;
        }
        if (this.charttwo) {
            this.charttwo.destroy();
            this.charttwo = null;
        }

        // Bar Chart - Status Distribution by Site
        const ctx = this.canvasRef.el.getContext('2d');
        if (ctx) {
            this.chart = new Chart(ctx, {
                type: "bar",
                data: {
                    labels: siteNames,
                    datasets: [
                        {
                            label: 'Reserved',
                            data: statusData.reserved,
                            backgroundColor: getColor(0),
                        },
                        {
                            label: 'Requested',
                            data: statusData.requested,
                            backgroundColor: getColor(1),
                        },
                        {
                            label: 'Cancelled',
                            data: statusData.cancelled,
                            backgroundColor: getColor(2),
                        },
                        {
                            label: 'Expired',
                            data: statusData.expired,
                            backgroundColor: getColor(3),
                        },
                        {
                            label: 'Sold',
                            data: statusData.sold,
                            backgroundColor: getColor(4),
                        }
                    ]
                },
                options: {
                    responsive: true,
                    plugins: {
                        title: {
                            display: true,
                            text: 'Property Site Status Distribution'
                        },
                        tooltip: {
                            mode: 'index',
                            intersect: false
                        },
                    },
                    scales: {
                        x: {
                            stacked: true,
                            title: {
                                display: true,
                                text: 'Property Sites'
                            }
                        },
                        y: {
                            stacked: true,
                            title: {
                                display: true,
                                text: 'Number of Customers'
                            },
                            beginAtZero: true
                        }
                    }
                }
            });
        }

        // Pie Chart - Total Status Distribution
        const totalStatusCounts = {
            reserved: statusData.reserved.reduce((a, b) => a + b, 0),
            requested: statusData.requested.reduce((a, b) => a + b, 0),
            cancelled: statusData.cancelled.reduce((a, b) => a + b, 0),
            expired: statusData.expired.reduce((a, b) => a + b, 0),
            sold: statusData.sold.reduce((a, b) => a + b, 0)
        };

        const ctx2 = this.canvasReftwo.el.getContext('2d');
        if (ctx2) {
            this.charttwo = new Chart(ctx2, {
                type: "pie",
                data: {
                    labels: ['Reserved', 'Requested', 'Cancelled', 'Expired', 'Sold'],
                    datasets: [{
                        data: [
                            totalStatusCounts.reserved,
                            totalStatusCounts.requested,
                            totalStatusCounts.cancelled,
                            totalStatusCounts.expired,
                            totalStatusCounts.sold
                        ],
                        backgroundColor: [
                            getColor(0),
                            getColor(1),
                            getColor(2),
                            getColor(3),
                            getColor(4)
                        ],
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        title: {
                            display: true,
                            text: 'Overall Status Distribution'
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const label = context.label || '';
                                    const value = context.raw || 0;
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = Math.round((value / total) * 100);
                                    return `${label}: ${value} (${percentage}%)`;
                                }
                            }
                        }
                    }
                }
            });
        }
    }

    goToSiteDetails(siteId) {
        if (this.action) {
            this.action.doAction({
                type: "ir.actions.act_window",
                res_model: "property.site",
                res_id: siteId,
                views: [[false, "form"]],
                target: "current"
            });
        }
    }
}

PropertySiteDashboard.template = "crm_dashboard.dashboard";
actionRegistry.add("dashboard", PropertySiteDashboard);