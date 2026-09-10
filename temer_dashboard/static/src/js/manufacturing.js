// /** @odoo-module **/

// import { registry } from "@web/core/registry";
// import { useService } from "@web/core/utils/hooks";
// import { Component, onWillStart, useRef, onMounted, onWillUnmount, useState } from "@odoo/owl";
// import { loadJS } from "@web/core/assets";
// import { getColor } from "@web/core/colors/colors";

// const actionRegistry = registry.category("actions");

// export class AnnualProductionDashboard extends Component {
//     setup() {
//         this.orm = useService('orm');
//         this.action = useService("action");

//         // State management
//         this.selectedProductId = useState({ value: null }); // <-- Add product selection state
//         this.productList = useState([]); // <-- List of available products

//         this.dateFilters = useState({
//             startDate: this.getDefaultStartDate(),
//             endDate: this.getDefaultEndDate()
//         });
//         this.stats = useState({
//             totalPlanned: 0,
//             totalProduced: 0,
//             productionData: [],
//             productData: [],
//             monthlyData: [],
//             isLoaded: false
//         });

//         // Chart references
//         this.barChartRef = useRef("barChart");
//         this.pieChartRef = useRef("pieChart");
//         this.lineChartRef = useRef("lineChart");
//         this.productChartRef = useRef("productChart");

//         this.charts = {
//             barChart: null,
//             pieChart: null,
//             lineChart: null,
//             productChart: null
//         };

//         onWillStart(async () => {
//             await loadJS(["/web/static/lib/Chart/Chart.js"]);
//             await this.loadProductList(); // <-- Load product list for filter
//             await this.fetchStats();
//         });

//         onMounted(() => {
//             this.renderCharts();
//             window.addEventListener('resize', this.handleResize);
//         });

//         onWillUnmount(() => {
//             this.destroyAllCharts();
//             window.removeEventListener('resize', this.handleResize);
//         });
//     }

//     getDefaultStartDate() {
//         const date = new Date();
//         date.setMonth(0);  // January
//         date.setDate(1);   // First day
//         return date.toISOString().split('T')[0];
//     }

//     getDefaultEndDate() {
//         const date = new Date();
//         return date.toISOString().split('T')[0];
//     }

//     destroyAllCharts() {
//         Object.values(this.charts).forEach(chart => {
//             if (chart) {
//                 chart.destroy();
//             }
//         });
//         this.charts = {
//             barChart: null,
//             pieChart: null,
//             lineChart: null,
//             productChart: null
//         };
//     }

//     handleResize() {
//         clearTimeout(this.resizeTimer);
//         this.resizeTimer = setTimeout(() => {
//             this.renderCharts();
//         }, 200);
//     }

//     async loadProductList() {
//         // Get all products that have a plan or production in the date range
//         const productIds = await this.orm.search("product.product", [], { limit: 1000 });
//         if (productIds.length) {
//             const products = await this.orm.read("product.product", productIds, ['name']);
//             this.productList.splice(0, this.productList.length, ...products);
//         }
//     }

//     async fetchStats() {
//         try {
//             // Filter by selected product if set
//             const productDomain = this.selectedProductId.value
//                 ? [['product_id', '=', this.selectedProductId.value]]
//                 : [];

//             // Get production data grouped by product
//             const productionData = await this.orm.readGroup(
//                 "annual.production.plan",
//                 [
//                     ['year', '=', new Date().getFullYear()],
//                     ['create_date', '>=', this.dateFilters.startDate],
//                     ['create_date', '<=', this.dateFilters.endDate + ' 23:59:59'],
//                     ...productDomain
//                 ],
//                 ['product_id', 'planned_quantity'],
//                 ['product_id'],
//                 { lazy: false }
//             );

//             // Get actual production data from manufacturing orders
//             const producedData = await this.orm.readGroup(
//                 "mrp.production",
//                 [
//                     ['date_planned_start', '>=', this.dateFilters.startDate],
//                     ['date_planned_start', '<=', this.dateFilters.endDate + ' 23:59:59'],
//                     ['state', '=', 'done'],
//                     ...productDomain
//                 ],
//                 ['product_id', 'product_qty'],
//                 ['product_id'],
//                 { lazy: false }
//             );

//             // Get monthly production data
//             const monthlyData = await this.orm.readGroup(
//                 "mrp.production",
//                 [
//                     ['date_planned_start', '>=', this.dateFilters.startDate],
//                     ['date_planned_start', '<=', this.dateFilters.endDate + ' 23:59:59'],
//                     ['state', '=', 'done'],
//                     ...productDomain
//                 ],
//                 ['product_qty'],
//                 ['date_planned_start:month'],
//                 { lazy: false }
//             );

//             // Calculate totals
//             const totalPlanned = productionData.reduce((sum, item) => sum + item.planned_quantity, 0);
//             const totalProduced = producedData.reduce((sum, item) => sum + item.product_qty, 0);

//             // Get product names
//             const productIds = [...new Set([
//                 ...productionData.map(item => item.product_id[0]),
//                 ...producedData.map(item => item.product_id[0])
//             ].filter(Boolean))];

//             const products = productIds.length ?
//                 await this.orm.read("product.product", productIds, ['name']) : [];

//             // Prepare product comparison data
//             const productComparison = productIds.map(productId => {
//                 const product = products.find(p => p.id === productId);
//                 const plannedItem = productionData.find(item => item.product_id && item.product_id[0] === productId);
//                 const producedItem = producedData.find(item => item.product_id && item.product_id[0] === productId);

//                 return {
//                     id: productId,
//                     name: product ? product.name : 'Unknown',
//                     planned: plannedItem ? plannedItem.planned_quantity : 0,
//                     produced: producedItem ? producedItem.product_qty : 0
//                 };
//             });

//             // Prepare monthly data for chart
//             const processedMonthlyData = monthlyData.map(item => ({
//                 month: item['date_planned_start:month'],
//                 quantity: item.product_qty
//             }));

//             // Update stats
//             this.stats.totalPlanned = totalPlanned;
//             this.stats.totalProduced = totalProduced;
//             this.stats.productionData = productionData;
//             this.stats.productData = productComparison;
//             this.stats.monthlyData = processedMonthlyData;
//             this.stats.isLoaded = true;

//         } catch (error) {
//             console.error("Error fetching production stats:", error);
//         }
//     }

//     renderCharts() {
//         this.destroyAllCharts();

//         // Planned vs Produced Bar Chart
//         if (this.stats.isLoaded && this.barChartRef.el) {
//             try {
//                 this.charts.barChart = new Chart(this.barChartRef.el, {
//                     type: "bar",
//                     data: {
//                         labels: ["Planned", "Produced"],
//                         datasets: [{
//                             label: 'Quantity',
//                             data: [this.stats.totalPlanned, this.stats.totalProduced],
//                             backgroundColor: [
//                                 getColor(0),
//                                 getColor(1)
//                             ],
//                             borderColor: [
//                                 getColor(0).replace('0.6', '1'),
//                                 getColor(1).replace('0.6', '1')
//                             ],
//                             borderWidth: 1
//                         }]
//                     },
//                     options: {
//                         responsive: true,
//                         maintainAspectRatio: false,
//                         scales: {
//                             y: {
//                                 beginAtZero: true
//                             }
//                         },
//                         plugins: {
//                             tooltip: {
//                                 callbacks: {
//                                     label: function(context) {
//                                         return `${context.dataset.label}: ${context.raw}`;
//                                     }
//                                 }
//                             }
//                         }
//                     }
//                 });
//             } catch (error) {
//                 console.error("Error rendering bar chart:", error);
//             }
//         }

//         // Planned vs Produced Pie Chart
//         if (this.stats.isLoaded && this.pieChartRef.el) {
//             try {
//                 this.charts.pieChart = new Chart(this.pieChartRef.el, {
//                     type: "pie",
//                     data: {
//                         labels: ["Planned", "Produced"],
//                         datasets: [{
//                             data: [this.stats.totalPlanned, this.stats.totalProduced],
//                             backgroundColor: [
//                                 getColor(0),
//                                 getColor(1)
//                             ],
//                             borderWidth: 1
//                         }]
//                     },
//                     options: {
//                         responsive: true,
//                         maintainAspectRatio: false,
//                         plugins: {
//                             tooltip: {
//                                 callbacks: {
//                                     label: function(context) {
//                                         const total = context.dataset.data.reduce((a, b) => a + b, 0);
//                                         const value = context.raw;
//                                         const percentage = ((value / total) * 100).toFixed(1);
//                                         return `${context.label}: ${value} (${percentage}%)`;
//                                     }
//                                 }
//                             }
//                         }
//                     }
//                 });
//             } catch (error) {
//                 console.error("Error rendering pie chart:", error);
//             }
//         }

//         // Monthly Production Line Chart
//         if (this.stats.monthlyData.length && this.lineChartRef.el) {
//             try {
//                 const labels = this.stats.monthlyData.map(item => item.month);
//                 const data = this.stats.monthlyData.map(item => item.quantity);

//                 this.charts.lineChart = new Chart(this.lineChartRef.el, {
//                     type: "line",
//                     data: {
//                         labels: labels,
//                         datasets: [{
//                             label: 'Monthly Production',
//                             data: data,
//                             backgroundColor: getColor(2),
//                             borderColor: getColor(2).replace('0.6', '1'),
//                             borderWidth: 2,
//                             fill: true,
//                             tension: 0.4
//                         }]
//                     },
//                     options: {
//                         responsive: true,
//                         maintainAspectRatio: false,
//                         scales: {
//                             y: {
//                                 beginAtZero: true
//                             }
//                         }
//                     }
//                 });
//             } catch (error) {
//                 console.error("Error rendering line chart:", error);
//             }
//         }

//         // Product Comparison Chart
//         if (this.stats.productData.length && this.productChartRef.el) {
//             try {
//                 const labels = this.stats.productData.map(item => item.name);
//                 const plannedData = this.stats.productData.map(item => item.planned);
//                 const producedData = this.stats.productData.map(item => item.produced);

//                 this.charts.productChart = new Chart(this.productChartRef.el, {
//                     type: "bar",
//                     data: {
//                         labels: labels,
//                         datasets: [
//                             {
//                                 label: 'Planned',
//                                 data: plannedData,
//                                 backgroundColor: getColor(3),
//                                 borderColor: getColor(3).replace('0.6', '1'),
//                                 borderWidth: 1
//                             },
//                             {
//                                 label: 'Produced',
//                                 data: producedData,
//                                 backgroundColor: getColor(4),
//                                 borderColor: getColor(4).replace('0.6', '1'),
//                                 borderWidth: 1
//                             }
//                         ]
//                     },
//                     options: {
//                         responsive: true,
//                         maintainAspectRatio: false,
//                         scales: {
//                             x: {
//                                 stacked: false,
//                             },
//                             y: {
//                                 stacked: false,
//                                 beginAtZero: true
//                             }
//                         }
//                     }
//                 });
//             } catch (error) {
//                 console.error("Error rendering product chart:", error);
//             }
//         }
//     }

//     // Navigation methods
//     goToProductionPlans() {
//         this.action.doAction({
//             type: "ir.actions.act_window",
//             res_model: "annual.production.plan",
//             view_mode: "list,form",
//             views: [[false, "list"], [false, "form"]],
//             target: "current",
//             domain: [
//                 ['year', '=', new Date().getFullYear()],
//                 ['create_date', '>=', this.dateFilters.startDate],
//                 ['create_date', '<=', this.dateFilters.endDate + ' 23:59:59']
//             ]
//         });
//     }

//     goToManufacturingOrders() {
//         this.action.doAction({
//             type: "ir.actions.act_window",
//             res_model: "mrp.production",
//             view_mode: "list,form",
//             views: [[false, "list"], [false, "form"]],
//             target: "current",
//             domain: [
//                 ['date_planned_start', '>=', this.dateFilters.startDate],
//                 ['date_planned_start', '<=', this.dateFilters.endDate + ' 23:59:59'],
//                 ['state', '=', 'done']
//             ]
//         });
//     }

//     applyDateFilter() {
//         this.stats.isLoaded = false;
//         this.fetchStats().then(() => {
//             this.renderCharts();
//         });
//     }

//     resetDateFilter() {
//         this.dateFilters.startDate = this.getDefaultStartDate();
//         this.dateFilters.endDate = this.getDefaultEndDate();
//         this.stats.isLoaded = false;
//         this.fetchStats().then(() => {
//             this.renderCharts();
//         });
//     }

//     // Add a handler for product selection
//     onProductChange(ev) {
//         this.selectedProductId.value = ev.target.value ? parseInt(ev.target.value) : null;
//         this.stats.isLoaded = false;
//         this.fetchStats().then(() => {
//             this.renderCharts();
//         });
//     }
// }

// AnnualProductionDashboard.template = "crm_dashboard.annual";
// actionRegistry.add("annual", AnnualProductionDashboard);












/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useRef, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { loadJS } from "@web/core/assets";
import { getColor } from "@web/core/colors/colors";

const actionRegistry = registry.category("actions");

export class AnnualProductionDashboard extends Component {
    setup() {
        this.orm = useService('orm');
        this.action = useService("action");

        this.selectedProductId = useState({ value: null });
        this.productList = useState([]);

        this.dateFilters = useState({
            startDate: this.getDefaultStartDate(),
            endDate: this.getDefaultEndDate()
        });
        this.stats = useState({
            totalPlanned: 0,
            totalProduced: 0,
            productionData: [],
            productData: [],
            monthlyData: [],
            isLoaded: false,
            selectedProductStats: null
        });

        this.barChartRef = useRef("barChart");
        this.pieChartRef = useRef("pieChart");
        this.lineChartRef = useRef("lineChart");
        this.productChartRef = useRef("productChart");

        this.charts = {
            barChart: null,
            pieChart: null,
            lineChart: null,
            productChart: null
        };

        onWillStart(async () => {
            await loadJS(["/web/static/lib/Chart/Chart.js"]);
            await this.loadProductList();
            await this.fetchStats();
        });

        onMounted(() => {
            this.renderCharts();
            window.addEventListener('resize', this.handleResize);
        });

        onWillUnmount(() => {
            this.destroyAllCharts();
            window.removeEventListener('resize', this.handleResize);
        });
    }

    getDefaultStartDate() {
        const date = new Date();
        date.setMonth(0);
        date.setDate(1);
        return date.toISOString().split('T')[0];
    }

    getDefaultEndDate() {
        const date = new Date();
        return date.toISOString().split('T')[0];
    }

    destroyAllCharts() {
        Object.values(this.charts).forEach(chart => {
            if (chart) {
                chart.destroy();
            }
        });
        this.charts = {
            barChart: null,
            pieChart: null,
            lineChart: null,
            productChart: null
        };
    }

    handleResize() {
        clearTimeout(this.resizeTimer);
        this.resizeTimer = setTimeout(() => {
            this.renderCharts();
        }, 200);
    }

    async loadProductList() {
        const productIds = await this.orm.search("product.product", [], { limit: 1000 });
        if (productIds.length) {
            const products = await this.orm.read("product.product", productIds, ['name']);
            this.productList.splice(0, this.productList.length, ...products);
        }
    }

    async fetchStats() {
        try {
            const productDomain = this.selectedProductId.value
                ? [['product_id', '=', this.selectedProductId.value]]
                : [];

            const productionData = await this.orm.readGroup(
                "annual.production.plan",
                [
                    ['year', '=', new Date().getFullYear()],
                    ['create_date', '>=', this.dateFilters.startDate],
                    ['create_date', '<=', this.dateFilters.endDate + ' 23:59:59'],
                    ...productDomain
                ],
                ['product_id', 'planned_quantity'],
                ['product_id'],
                { lazy: false }
            );

            const producedData = await this.orm.readGroup(
                "mrp.production",
                [
                    ['date_planned_start', '>=', this.dateFilters.startDate],
                    ['date_planned_start', '<=', this.dateFilters.endDate + ' 23:59:59'],
                    ['state', '=', 'done'],
                    ...productDomain
                ],
                ['product_id', 'product_qty'],
                ['product_id'],
                { lazy: false }
            );

            const monthlyData = await this.orm.readGroup(
                "mrp.production",
                [
                    ['date_planned_start', '>=', this.dateFilters.startDate],
                    ['date_planned_start', '<=', this.dateFilters.endDate + ' 23:59:59'],
                    ['state', '=', 'done'],
                    ...productDomain
                ],
                ['product_qty'],
                ['date_planned_start:month'],
                { lazy: false }
            );

            const totalPlanned = productionData.reduce((sum, item) => sum + item.planned_quantity, 0);
            const totalProduced = producedData.reduce((sum, item) => sum + item.product_qty, 0);

            const productIds = [...new Set([
                ...productionData.map(item => item.product_id[0]),
                ...producedData.map(item => item.product_id[0])
            ].filter(Boolean))];

            const products = productIds.length ?
                await this.orm.read("product.product", productIds, ['name']) : [];

            const productComparison = productIds.map(productId => {
                const product = products.find(p => p.id === productId);
                const plannedItem = productionData.find(item => item.product_id && item.product_id[0] === productId);
                const producedItem = producedData.find(item => item.product_id && item.product_id[0] === productId);

                return {
                    id: productId,
                    name: product ? product.name : 'Unknown',
                    planned: plannedItem ? plannedItem.planned_quantity : 0,
                    produced: producedItem ? producedItem.product_qty : 0
                };
            });

            const processedMonthlyData = monthlyData.map(item => ({
                month: item['date_planned_start:month'],
                quantity: item.product_qty
            }));

            let selectedProductStats = null;
            if (this.selectedProductId.value) {
                const product = products.find(p => p.id === this.selectedProductId.value);
                if (product) {
                    const planned = productionData.find(item => item.product_id && item.product_id[0] === this.selectedProductId.value);
                    const produced = producedData.find(item => item.product_id && item.product_id[0] === this.selectedProductId.value);
                    
                    selectedProductStats = {
                        name: product.name,
                        planned: planned ? planned.planned_quantity : 0,
                        produced: produced ? produced.product_qty : 0
                    };
                }
            }

            this.stats.totalPlanned = totalPlanned;
            this.stats.totalProduced = totalProduced;
            this.stats.productionData = productionData;
            this.stats.productData = productComparison;
            this.stats.monthlyData = processedMonthlyData;
            this.stats.selectedProductStats = selectedProductStats;
            this.stats.isLoaded = true;

        } catch (error) {
            console.error("Error fetching production stats:", error);
        }
    }

    renderCharts() {
        this.destroyAllCharts();

        if (this.stats.isLoaded && this.barChartRef.el) {
            try {
                this.charts.barChart = new Chart(this.barChartRef.el, {
                    type: "bar",
                    data: {
                        labels: ["Planned", "Produced"],
                        datasets: [{
                            label: 'Quantity',
                            data: [this.stats.totalPlanned, this.stats.totalProduced],
                            backgroundColor: [
                                getColor(0),
                                getColor(1)
                            ],
                            borderColor: [
                                getColor(0).replace('0.6', '1'),
                                getColor(1).replace('0.6', '1')
                            ],
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: {
                                beginAtZero: true
                            }
                        },
                        plugins: {
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        return `${context.dataset.label}: ${context.raw}`;
                                    }
                                }
                            }
                        }
                    }
                });
            } catch (error) {
                console.error("Error rendering bar chart:", error);
            }
        }

        if (this.stats.isLoaded && this.pieChartRef.el) {
            try {
                this.charts.pieChart = new Chart(this.pieChartRef.el, {
                    type: "pie",
                    data: {
                        labels: ["Planned", "Produced"],
                        datasets: [{
                            data: [this.stats.totalPlanned, this.stats.totalProduced],
                            backgroundColor: [
                                getColor(0),
                                getColor(1)
                            ],
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                        const value = context.raw;
                                        const percentage = ((value / total) * 100).toFixed(1);
                                        return `${context.label}: ${value} (${percentage}%)`;
                                    }
                                }
                            }
                        }
                    }
                });
            } catch (error) {
                console.error("Error rendering pie chart:", error);
            }
        }

        if (this.stats.monthlyData.length && this.lineChartRef.el) {
            try {
                const labels = this.stats.monthlyData.map(item => item.month);
                const data = this.stats.monthlyData.map(item => item.quantity);

                this.charts.lineChart = new Chart(this.lineChartRef.el, {
                    type: "line",
                    data: {
                        labels: labels,
                        datasets: [{
                            label: 'Monthly Production',
                            data: data,
                            backgroundColor: getColor(2),
                            borderColor: getColor(2).replace('0.6', '1'),
                            borderWidth: 2,
                            fill: true,
                            tension: 0.4
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: {
                                beginAtZero: true
                            }
                        }
                    }
                });
            } catch (error) {
                console.error("Error rendering line chart:", error);
            }
        }

        if (this.stats.productData.length && this.productChartRef.el) {
            try {
                const labels = this.stats.productData.map(item => item.name);
                const plannedData = this.stats.productData.map(item => item.planned);
                const producedData = this.stats.productData.map(item => item.produced);

                this.charts.productChart = new Chart(this.productChartRef.el, {
                    type: "bar",
                    data: {
                        labels: labels,
                        datasets: [
                            {
                                label: 'Planned',
                                data: plannedData,
                                backgroundColor: getColor(3),
                                borderColor: getColor(3).replace('0.6', '1'),
                                borderWidth: 1
                            },
                            {
                                label: 'Produced',
                                data: producedData,
                                backgroundColor: getColor(4),
                                borderColor: getColor(4).replace('0.6', '1'),
                                borderWidth: 1
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            x: {
                                stacked: false,
                            },
                            y: {
                                stacked: false,
                                beginAtZero: true
                            }
                        }
                    }
                });
            } catch (error) {
                console.error("Error rendering product chart:", error);
            }
        }
    }

    goToProductionPlans() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "annual.production.plan",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
            domain: [
                ['year', '=', new Date().getFullYear()],
                ['create_date', '>=', this.dateFilters.startDate],
                ['create_date', '<=', this.dateFilters.endDate + ' 23:59:59']
            ]
        });
    }

    goToManufacturingOrders() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "mrp.production",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
            domain: [
                ['date_planned_start', '>=', this.dateFilters.startDate],
                ['date_planned_start', '<=', this.dateFilters.endDate + ' 23:59:59'],
                ['state', '=', 'done']
            ]
        });
    }

    applyDateFilter() {
        this.stats.isLoaded = false;
        this.fetchStats().then(() => {
            this.renderCharts();
        });
    }

    resetDateFilter() {
        this.dateFilters.startDate = this.getDefaultStartDate();
        this.dateFilters.endDate = this.getDefaultEndDate();
        this.stats.isLoaded = false;
        this.fetchStats().then(() => {
            this.renderCharts();
        });
    }

    onProductChange(ev) {
        this.selectedProductId.value = ev.target.value ? parseInt(ev.target.value) : null;
        this.stats.isLoaded = false;
        this.fetchStats().then(() => {
            this.renderCharts();
        });
    }
}

AnnualProductionDashboard.template = "crm_dashboard.annual";
actionRegistry.add("annual", AnnualProductionDashboard);