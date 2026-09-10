// // // // /** @odoo-module **/

// // // // import { registry } from "@web/core/registry";
// // // // import { useService } from "@web/core/utils/hooks";
// // // // import { Component, onWillStart, useState } from "@odoo/owl";

// // // // class MySalesSummaryDashboard extends Component {
// // // //     setup() {
// // // //         this.orm = useService('orm');
// // // //         this.user = useService('user');

// // // //         this.state = useState({
// // // //             loading: true,
// // // //             salesData: [],
// // // //             dateFilters: {
// // // //                 endDate: new Date().toISOString().slice(0, 10) // defaults to today's date
// // // //             },
// // // //         });

// // // //         onWillStart(async () => {
// // // //             await this.loadSalesData();
// // // //         });
// // // //     }

// // // //     // Method to fetch sales data
// // // //     async loadSalesData() {
// // // //         try {
// // // //             this.state.loading = true;
// // // //             const end = this.state.dateFilters.endDate;
// // // //             const results = await this.orm.call(
// // // //                 "crm.lead",
// // // //                 "get_my_sales_summary",
// // // //                 [end],
// // // //                 {}
// // // //             );
// // // //             this.state.salesData = results;
// // // //         } catch (error) {
// // // //             console.error("Error fetching sales summary:", error);
// // // //             this.state.salesData = [];
// // // //         } finally {
// // // //             this.state.loading = false;
// // // //         }
// // // //     }

// // // //     // Event handler for date change
// // // //     async handleDateChange(ev) {
// // // //         this.state.dateFilters.endDate = ev.target.value;
// // // //         await this.loadSalesData(); // Reload data with new date
// // // //     }

// // // //     get summary() {
// // // //         if (!this.state.salesData.length) {
// // // //             return {
// // // //                 sales_person: this.user.partnerDisplayName,
// // // //                 prospect: 0,
// // // //                 follow_up: 0,
// // // //                 reservation_count: 0,
// // // //                 sold_reservation_count: 0,
// // // //                 expired: 0,
// // // //                 won: 0,
// // // //                 total: 0
// // // //             };
// // // //         }

// // // //         const data = this.state.salesData[0];

// // // //         return {
// // // //             sales_person: this.user.partnerDisplayName,
// // // //             prospect: data.prospect || 0,
// // // //             follow_up: data.follow_up || 0,
// // // //             reservation_count: data.reservation_count || 0,
// // // //             sold_reservation_count: data.sold_reservation_count || 0,
// // // //             expired: data.expired || 0,
// // // //             won: data.won || 0,
// // // //             total: (data.prospect + data.follow_up + data.reservation_count + data.sold_reservation_count + data.expired + data.won) || 0
// // // //         };
// // // //     }
// // // // }

// // // // MySalesSummaryDashboard.template = "temer_dashboard.my_sales_summary";
// // // // registry.category("actions").add("my_sales_summary", MySalesSummaryDashboard);








// // // /** @odoo-module **/

// // // import { registry } from "@web/core/registry";
// // // import { useService } from "@web/core/utils/hooks";
// // // import { Component, onWillStart, useState } from "@odoo/owl";

// // // class MySalesSummaryDashboard extends Component {
// // //     setup() {
// // //         this.orm = useService('orm');
// // //         this.user = useService('user');

// // //         const today = new Date();
// // //         const oneWeekAgo = new Date();
// // //         oneWeekAgo.setDate(today.getDate() - 7);

// // //         this.state = useState({
// // //             loading: true,
// // //             salesData: [],
// // //             dateFilters: {
// // //                 startDate: oneWeekAgo.toISOString().slice(0, 10), // Default to one week ago
// // //                 endDate: today.toISOString().slice(0, 10) // Default to today
// // //             },
// // //         });

// // //         onWillStart(async () => {
// // //             await this.loadSalesData();
// // //         });
// // //     }

// // //     // Method to fetch sales data
// // //     async loadSalesData() {
// // //         try {
// // //             this.state.loading = true;
// // //             const { startDate, endDate } = this.state.dateFilters;
// // //             const results = await this.orm.call(
// // //                 "crm.lead",
// // //                 "get_my_sales_summary",
// // //                 [startDate, endDate],
// // //                 {}
// // //             );
// // //             this.state.salesData = results;
// // //         } catch (error) {
// // //             console.error("Error fetching sales summary:", error);
// // //             this.state.salesData = [];
// // //         } finally {
// // //             this.state.loading = false;
// // //         }
// // //     }

// // //     // Event handler for date change
// // //     async onDateFilterChange(ev) {
// // //         this.state.dateFilters[ev.target.name] = ev.target.value;
// // //         await this.loadSalesData(); // Reload data with new dates
// // //     }

// // //     get summary() {
// // //         if (!this.state.salesData.length) {
// // //             return {
// // //                 sales_person: this.user.partnerDisplayName,
// // //                 prospect: 0,
// // //                 follow_up: 0,
// // //                 reservation_count: 0,
// // //                 sold_reservation_count: 0,
// // //                 expired: 0,
// // //                 won: 0,
// // //                 total: 0
// // //             };
// // //         }

// // //         const data = this.state.salesData[0];

// // //         return {
// // //             sales_person: this.user.partnerDisplayName,
// // //             prospect: data.prospect || 0,
// // //             follow_up: data.follow_up || 0,
// // //             reservation_count: data.reservation_count || 0,
// // //             sold_reservation_count: data.sold_reservation_count || 0,
// // //             expired: data.expired || 0,
// // //             won: data.won || 0,
// // //             total: (data.prospect + data.follow_up + data.reservation_count + data.sold_reservation_count + data.expired + data.won) || 0
// // //         };
// // //     }
// // // }

// // // MySalesSummaryDashboard.template = "temer_dashboard.my_sales_summary";
// // // registry.category("actions").add("my_sales_summary", MySalesSummaryDashboard);




// // /** @odoo-module **/

// // import { registry } from "@web/core/registry";
// // import { useService } from "@web/core/utils/hooks";
// // import { Component, onWillStart, onMounted, useState, useRef } from "@odoo/owl";
// // import { loadJS } from "@web/core/assets";

// // class MySalesSummaryDashboard extends Component {
// //     setup() {
// //         this.orm = useService('orm');
// //         this.user = useService('user');
// //         this.chartRef = useRef("chart");
// //         this.pieChartRef = useRef("pieChart");

// //         const today = new Date();
// //         const oneWeekAgo = new Date();
// //         oneWeekAgo.setDate(today.getDate() - 7);

// //         this.state = useState({
// //             loading: true,
// //             salesData: [],
// //             dateFilters: {
// //                 date_to: today.toISOString().slice(0, 10) // Using date_to to match Python method
// //             },
// //             chart: null,
// //             pieChart: null
// //         });

// //         onWillStart(async () => {
// //             try {
// //                 await loadJS("/web/static/lib/Chart/Chart.js");
// //                 await this.loadSalesData();
// //             } catch (error) {
// //                 console.error("Error initializing dashboard:", error);
// //             }
// //         });

// //         onMounted(() => {
// //             this.renderCharts();
// //         });
// //     }

// //     async loadSalesData() {
// //         try {
// //             this.state.loading = true;
// //             const { date_to } = this.state.dateFilters;
// //             const results = await this.orm.call(
// //                 "crm.lead",
// //                 "get_my_sales_summary",
// //                 [date_to], // Only passing date_to as expected by Python method
// //                 {}
// //             );
// //             this.state.salesData = results;
// //             this.renderCharts();
// //         } catch (error) {
// //             console.error("Error fetching sales summary:", error);
// //             this.state.salesData = [];
// //         } finally {
// //             this.state.loading = false;
// //         }
// //     }

// //     async onDateFilterChange(ev) {
// //         this.state.dateFilters[ev.target.name] = ev.target.value;
// //         await this.loadSalesData();
// //     }

// //     renderCharts() {
// //         this.renderBarChart();
// //         this.renderPieChart();
// //     }

// //     renderBarChart() {
// //         if (!this.chartRef.el) return;

// //         const ctx = this.chartRef.el.getContext('2d');
// //         if (!ctx) return;

// //         if (this.state.chart) {
// //             this.state.chart.destroy();
// //         }

// //         const summary = this.summary;
// //         const labels = ['Prospects', 'Follow Ups', 'Reservations', 'Won', 'Expired'];
// //         const data = [
// //             summary.prospect,
// //             summary.follow_up,
// //             summary.reservation_count,
// //             summary.won,
// //             summary.expired
// //         ];

// //         this.state.chart = new Chart(ctx, {
// //             type: 'bar',
// //             data: {
// //                 labels: labels,
// //                 datasets: [{
// //                     label: 'Sales Summary',
// //                     data: data,
// //                     backgroundColor: [
// //                         'rgba(54, 162, 235, 0.7)',
// //                         'rgba(255, 206, 86, 0.7)',
// //                         'rgba(75, 192, 192, 0.7)',
// //                         'rgba(75, 192, 75, 0.7)',
// //                         'rgba(255, 99, 132, 0.7)'
// //                     ],
// //                     borderColor: [
// //                         'rgba(54, 162, 235, 1)',
// //                         'rgba(255, 206, 86, 1)',
// //                         'rgba(75, 192, 192, 1)',
// //                         'rgba(75, 192, 75, 1)',
// //                         'rgba(255, 99, 132, 1)'
// //                     ],
// //                     borderWidth: 1
// //                 }]
// //             },
// //             options: {
// //                 responsive: true,
// //                 maintainAspectRatio: false,
// //                 plugins: {
// //                     title: {
// //                         display: true,
// //                         text: 'My Sales Summary'
// //                     },
// //                 },
// //                 scales: {
// //                     y: {
// //                         beginAtZero: true,
// //                         title: {
// //                             display: true,
// //                             text: 'Count'
// //                         }
// //                     }
// //                 }
// //             }
// //         });
// //     }

// //     renderPieChart() {
// //         if (!this.pieChartRef.el) return;

// //         const ctx = this.pieChartRef.el.getContext('2d');
// //         if (!ctx) return;

// //         if (this.state.pieChart) {
// //             this.state.pieChart.destroy();
// //         }

// //         const summary = this.summary;
// //         const labels = ['Prospects', 'Follow Ups', 'Reservations', 'Won', 'Expired'];
// //         const data = [
// //             summary.prospect,
// //             summary.follow_up,
// //             summary.reservation_count,
// //             summary.won,
// //             summary.expired
// //         ];

// //         this.state.pieChart = new Chart(ctx, {
// //             type: 'pie',
// //             data: {
// //                 labels: labels,
// //                 datasets: [{
// //                     data: data,
// //                     backgroundColor: [
// //                         'rgba(54, 162, 235, 1)',
// //                         'rgba(255, 206, 86, 1)',
// //                         'rgba(75, 192, 192, 1)',
// //                         'rgba(75, 192, 75, 1)',
// //                         'rgba(255, 99, 132, 1)'
// //                     ],
// //                     borderWidth: 1
// //                 }]
// //             },
// //             options: {
// //                 responsive: true,
// //                 maintainAspectRatio: false,
// //                 plugins: {
// //                     title: {
// //                         display: true,
// //                         text: 'Sales Distribution'
// //                     },
// //                     legend: {
// //                         position: 'right'
// //                     }
// //                 }
// //             }
// //         });
// //     }

// //     get summary() {
// //         if (!this.state.salesData.length) {
// //             return {
// //                 sales_person: this.user.partnerDisplayName,
// //                 prospect: 0,
// //                 follow_up: 0,
// //                 reservation_count: 0,
// //                 sold_reservation_count: 0,
// //                 expired: 0,
// //                 won: 0,
// //                 total: 0
// //             };
// //         }

// //         const data = this.state.salesData[0];

// //         return {
// //             sales_person: this.user.partnerDisplayName,
// //             prospect: data.prospect || 0,
// //             follow_up: data.follow_up || 0,
// //             reservation_count: data.reservation_count || 0,
// //             sold_reservation_count: data.sold_reservation_count || 0,
// //             expired: data.expired || 0,
// //             won: data.won || 0,
// //             total: (data.prospect + data.follow_up + data.reservation_count + 
// //                    data.sold_reservation_count + data.expired + data.won) || 0
// //         };
// //     }
// // }

// // MySalesSummaryDashboard.template = "temer_dashboard.my_sales_summary";
// // registry.category("actions").add("my_sales_summary", MySalesSummaryDashboard);








// /** @odoo-module **/

// import { registry } from "@web/core/registry";
// import { useService } from "@web/core/utils/hooks";
// import { Component, onWillStart, onMounted, useState, useRef } from "@odoo/owl";
// import { loadJS } from "@web/core/assets";

// class MySalesSummaryDashboard extends Component {
//     setup() {
//         this.orm = useService('orm');
//         this.user = useService('user');
//         this.chartRef = useRef("chart");
//         this.pieChartRef = useRef("pieChart");

//         const today = new Date();
//         const oneWeekAgo = new Date();
//         oneWeekAgo.setDate(today.getDate() - 7);

//         this.state = useState({
//             loading: true,
//             salesData: [],
//             dateFilters: {
//                 date_from: oneWeekAgo.toISOString().slice(0, 10),
//                 date_to: today.toISOString().slice(0, 10)
//             },
//             chart: null,
//             pieChart: null,
//             errorMessage: null
//         });

//         onWillStart(async () => {
//             try {
//                 await loadJS("/web/static/lib/Chart/Chart.js");
//                 await this.loadSalesData();
//             } catch (error) {
//                 console.error("Error initializing dashboard:", error);
//                 this.state.errorMessage = "Failed to load charting library";
//             }
//         });

//         onMounted(() => {
//             this.renderCharts();
//         });
//     }

//     async loadSalesData() {
//         try {
//             this.state.loading = true;
//             this.state.errorMessage = null;
            
//             const { date_from, date_to } = this.state.dateFilters;
            
//             // Validate dates
//             if (new Date(date_from) > new Date(date_to)) {
//                 this.state.errorMessage = "Start date cannot be after end date";
//                 return;
//             }

//             const results = await this.orm.call(
//                 "crm.lead",
//                 "get_my_sales_summary",
//                 [date_to], // Passing date_to as the main parameter
//                 { context: { default_date_from: date_from } } // Passing date_from in context
//             );
            
//             this.state.salesData = results;
//             this.renderCharts();
//         } catch (error) {
//             console.error("Error fetching sales summary:", error);
//             this.state.errorMessage = "Failed to load sales data";
//             this.state.salesData = [];
//         } finally {
//             this.state.loading = false;
//         }
//     }

//     async onDateFilterChange(ev) {
//         this.state.dateFilters[ev.target.name] = ev.target.value;
//         await this.loadSalesData();
//     }

//     renderCharts() {
//         this.renderBarChart();
//         this.renderPieChart();
//     }

//     renderBarChart() {
//         if (!this.chartRef.el) return;

//         const ctx = this.chartRef.el.getContext('2d');
//         if (!ctx) return;

//         if (this.state.chart) {
//             this.state.chart.destroy();
//         }

//         const summary = this.summary;
//         const labels = ['Prospects', 'Follow Ups', 'Reservations', 'Won', 'Expired'];
//         const data = [
//             summary.prospect,
//             summary.follow_up,
//             summary.reservation_count,
//             summary.won,
//             summary.expired
//         ];

//         this.state.chart = new Chart(ctx, {
//             type: 'bar',
//             data: {
//                 labels: labels,
//                 datasets: [{
//                     label: 'Sales Summary',
//                     data: data,
//                     backgroundColor: [
//                         'rgba(54, 162, 235, 0.7)',
//                         'rgba(255, 206, 86, 0.7)',
//                         'rgba(75, 192, 192, 0.7)',
//                         'rgba(75, 192, 75, 0.7)',
//                         'rgba(255, 99, 132, 0.7)'
//                     ],
//                     borderColor: [
//                         'rgba(54, 162, 235, 1)',
//                         'rgba(255, 206, 86, 1)',
//                         'rgba(75, 192, 192, 1)',
//                         'rgba(75, 192, 75, 1)',
//                         'rgba(255, 99, 132, 1)'
//                     ],
//                     borderWidth: 1
//                 }]
//             },
//             options: {
//                 responsive: true,
//                 maintainAspectRatio: false,
//                 plugins: {
//                     title: {
//                         display: true,
//                         text: `My Sales Summary (${this.state.dateFilters.date_from} to ${this.state.dateFilters.date_to})`
//                     },
//                 },
//                 scales: {
//                     y: {
//                         beginAtZero: true,
//                         title: {
//                             display: true,
//                             text: 'Count'
//                         }
//                     }
//                 }
//             }
//         });
//     }

//     renderPieChart() {
//         if (!this.pieChartRef.el) return;

//         const ctx = this.pieChartRef.el.getContext('2d');
//         if (!ctx) return;

//         if (this.state.pieChart) {
//             this.state.pieChart.destroy();
//         }

//         const summary = this.summary;
//         const labels = ['Prospects', 'Follow Ups', 'Reservations', 'Won', 'Expired'];
//         const data = [
//             summary.prospect,
//             summary.follow_up,
//             summary.reservation_count,
//             summary.won,
//             summary.expired
//         ];

//         this.state.pieChart = new Chart(ctx, {
//             type: 'pie',
//             data: {
//                 labels: labels,
//                 datasets: [{
//                     data: data,
//                     backgroundColor: [
//                         'rgba(54, 162, 235, 1)',
//                         'rgba(255, 206, 86, 1)',
//                         'rgba(75, 192, 192, 1)',
//                         'rgba(75, 192, 75, 1)',
//                         'rgba(255, 99, 132, 1)'
//                     ],
//                     borderWidth: 1
//                 }]
//             },
//             options: {
//                 responsive: true,
//                 maintainAspectRatio: false,
//                 plugins: {
//                     title: {
//                         display: true,
//                         text: 'Sales Distribution'
//                     },
//                     legend: {
//                         position: 'right'
//                     }
//                 }
//             }
//         });
//     }

//     get summary() {
//         if (!this.state.salesData.length) {
//             return {
//                 sales_person: this.user.partnerDisplayName,
//                 prospect: 0,
//                 follow_up: 0,
//                 reservation_count: 0,
//                 sold_reservation_count: 0,
//                 expired: 0,
//                 won: 0,
//                 total: 0
//             };
//         }

//         const data = this.state.salesData[0];

//         return {
//             sales_person: this.user.partnerDisplayName,
//             prospect: data.prospect || 0,
//             follow_up: data.follow_up || 0,
//             reservation_count: data.reservation_count || 0,
//             sold_reservation_count: data.sold_reservation_count || 0,
//             expired: data.expired || 0,
//             won: data.won || 0,
//             total: (data.prospect + data.follow_up + data.reservation_count + 
//                    data.sold_reservation_count + data.expired + data.won) || 0
//         };
//     }
// }

// MySalesSummaryDashboard.template = "temer_dashboard.my_sales_summary";
// registry.category("actions").add("my_sales_summary", MySalesSummaryDashboard);




/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, onMounted, useState, useRef } from "@odoo/owl";
import { loadJS } from "@web/core/assets";

class MySalesSummaryDashboard extends Component {
    setup() {
        this.orm = useService('orm');
        this.user = useService('user');
        this.chartRef = useRef("chart");
        this.pieChartRef = useRef("pieChart");

        const today = new Date();
        const oneWeekAgo = new Date();
        oneWeekAgo.setDate(today.getDate() - 7);

        this.state = useState({
            loading: true,
            salesData: [],
            dateFilters: {
                date_from: oneWeekAgo.toISOString().slice(0, 10),
                date_to: today.toISOString().slice(0, 10)
            },
            totals: {
                prospects: 0,
                follow_ups: 0,
                reservations: 0,
                won: 0,
                expired: 0,
                sold_reservations: 0,
                leads_count: 0
            },
            chart: null,
            pieChart: null,
            errorMessage: null
        });

        onWillStart(async () => {
            try {
                await loadJS("/web/static/lib/Chart/Chart.js");
                await this.loadSalesData();
            } catch (error) {
                console.error("Error initializing dashboard:", error);
                this.state.errorMessage = "Failed to load charting library";
                this.state.loading = false;
            }
        });

        onMounted(() => {
            this.renderChartsWithRetry();
        });
    }

    cleanSupervisorName(name) {
        try {
            const strName = typeof name === 'string' ? name : String(name || '');
            const cleanedName = strName.includes(',') ? strName.split(',')[1].trim() : strName;
            return typeof cleanedName === 'string' 
                ? cleanedName.replace('(Team Total)', '').trim() 
                : 'No Supervisor';
        } catch (error) {
            console.error('Error cleaning supervisor name:', error, 'Original name:', name);
            return 'No Supervisor';
        }
    }

    renderChartsWithRetry(attempt = 0) {
        if (attempt > 3) {
            console.error('Failed to render charts after multiple attempts');
            return;
        }

        if (!this.chartRef.el || !this.pieChartRef.el) {
            console.warn(`Chart containers not found (attempt ${attempt + 1}), retrying...`);
            setTimeout(() => this.renderChartsWithRetry(attempt + 1), 500);
            return;
        }

        this.renderCharts();
    }

    renderCharts() {
        try {
            if (this.state.chart) {
                this.state.chart.destroy();
                this.state.chart = null;
            }
            if (this.state.pieChart) {
                this.state.pieChart.destroy();
                this.state.pieChart = null;
            }

            this.renderBarChart();
            this.renderPieChart();
        } catch (error) {
            console.error('Error in renderCharts:', error);
        }
    }

    renderBarChart() {
        try {
            if (!this.chartRef.el) {
                console.warn('Bar chart container not found in DOM');
                return;
            }

            const ctx = this.chartRef.el.getContext('2d');
            if (!ctx) {
                console.warn('Could not get 2D context for bar chart');
                return;
            }

            const labels = ['Leads', 'Prospects', 'Follow Ups', 'Reservations', 'Won', 'Expired'];
            const data = [
                this.state.totals.leads_count,
                this.state.totals.prospects,
                this.state.totals.follow_ups,
                this.state.totals.reservations,
                this.state.totals.won,
                this.state.totals.expired
            ];

            this.state.chart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Sales Summary',
                        data: data,
                        backgroundColor: [
                            'rgba(153, 102, 255, 0.7)', // Color for leads_count
                            'rgba(54, 162, 235, 0.7)',
                            'rgba(255, 206, 86, 0.7)',
                            'rgba(75, 192, 192, 0.7)',
                            'rgba(75, 192, 75, 0.7)',
                            'rgba(255, 99, 132, 0.7)'
                        ],
                        borderColor: [
                            'rgba(153, 102, 255, 1)',
                            'rgba(54, 162, 235, 1)',
                            'rgba(255, 206, 86, 1)',
                            'rgba(75, 192, 192, 1)',
                            'rgba(75, 192, 75, 1)',
                            'rgba(255, 99, 132, 1)'
                        ],
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        title: {
                            display: true,
                            text: `My Sales Summary (${this.state.dateFilters.date_from} to ${this.state.dateFilters.date_to})`
                        },
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Count'
                            }
                        }
                    }
                }
            });
        } catch (error) {
            console.error('Error rendering bar chart:', error);
        }
    }

    renderPieChart() {
        try {
            if (!this.pieChartRef.el) {
                console.warn('Pie chart container not found in DOM');
                return;
            }

            const ctx = this.pieChartRef.el.getContext('2d');
            if (!ctx) {
                console.warn('Could not get 2D context for pie chart');
                return;
            }

            const labels = ['Prospects', 'Follow Ups', 'Reservations', 'Won', 'Expired'];
            const data = [
                this.state.totals.prospects,
                this.state.totals.follow_ups,
                this.state.totals.reservations,
                this.state.totals.won,
                this.state.totals.expired
            ];

            this.state.pieChart = new Chart(ctx, {
                type: 'pie',
                data: {
                    labels: labels,
                    datasets: [{
                        data: data,
                        backgroundColor: [
                            'rgba(54, 162, 235, 1)',
                            'rgba(255, 206, 86, 1)',
                            'rgba(75, 192, 192, 1)',
                            'rgba(75, 192, 75, 1)',
                            'rgba(255, 99, 132, 1)'
                        ],
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        title: {
                            display: true,
                            text: 'Sales Distribution'
                        },
                        legend: {
                            position: 'right'
                        }
                    }
                }
            });
        } catch (error) {
            console.error('Error rendering pie chart:', error);
        }
    }

    async loadSalesData() {
        try {
            this.state.loading = true;
            this.state.errorMessage = null;

            const { date_from, date_to } = this.state.dateFilters;

            // Validate dates
            if (!date_from || new Date(date_from) > new Date(date_to)) {
                this.state.errorMessage = "Start date cannot be after end date or is missing";
                this.state.salesData = [];
                this.state.totals = {
                    prospects: 0,
                    follow_ups: 0,
                    reservations: 0,
                    won: 0,
                    expired: 0,
                    sold_reservations: 0,
                    leads_count: 0
                };
                return;
            }

            // Fetch leads for the logged-in user
            const leads = await this.orm.call(
                'crm.lead',
                'search_read',
                [[
                    ['create_date', '>=', date_from],
                    ['create_date', '<=', date_to],
                    ['user_id', '=', this.user.userId]
                ]],
                { fields: ['id', 'create_date', 'stage_id', 'user_id', 'supervisor_id', 'wing_id'] }
            );

            const stageIds = [...new Set(leads.map(l => l.stage_id ? l.stage_id[0] : null).filter(id => id))];
            const stages = stageIds.length ? await this.orm.call('crm.stage', 'search_read', [[['id', 'in', stageIds]]], { fields: ['id', 'name'] }) : [];
            const stageMap = new Map(stages.map(s => [s.id, s.name || 'Unknown Stage']));

            // Fetch reservations
            const reservations = await this.orm.call(
                'property.reservation',
                'search_read',
                [[
                    ['create_date', '>=', date_from],
                    ['create_date', '<=', date_to]
                ]],
                { fields: ['id', 'crm_lead_id', 'status', 'create_date'] }
            );

            const userIds = [this.user.userId];
            const supervisorIds = [...new Set(leads.map(l => l.supervisor_id ? l.supervisor_id[0] : null).filter(id => id))];
            const wingIds = [...new Set(leads.map(l => l.wing_id ? l.wing_id[0] : null).filter(id => id))];

            const users = userIds.length ? await this.orm.call('res.users', 'search_read', [[['id', 'in', userIds]]], { fields: ['id', 'name'] }) : [];
            const supervisors = supervisorIds.length ? await this.orm.call('property.sales.supervisor', 'search_read', [[['id', 'in', supervisorIds]]], { fields: ['id', 'name'] }) : [];
            const wings = wingIds.length ? await this.orm.call('property.sales.wing', 'search_read', [[['id', 'in', wingIds]]], { fields: ['id', 'name'] }) : [];

            const userMap = new Map(users.map(u => [u.id, u.name || 'Unknown User']));
            const supervisorMap = new Map(supervisors.map(s => [s.id, s.name || 'Unknown Supervisor']));
            const wingMap = new Map(wings.map(w => [w.id, w.name || 'Unknown Wing']));

            // Filter for Team - Taj
            const filteredLeads = leads.filter(lead => wingMap.get(lead.wing_id ? lead.wing_id[0] : 0) === 'Team - Taj');

            // Process lead events
            const leadEvents = filteredLeads.map(lead => {
                let event_type = null;
                const stageName = lead.stage_id ? (stageMap.get(lead.stage_id[0]) || '').toLowerCase() : '';
                if (stageName) {
                    if (stageName.includes('expired')) event_type = 'Expired';
                    else if (stageName.includes('won')) event_type = 'Won';
                    else if (stageName.includes('reservation')) event_type = 'Reservation';
                    else if (stageName.includes('follow')) event_type = 'Follow Up';
                    else if (stageName.includes('prospect')) event_type = 'Prospect';
                }
                return {
                    lead_id: lead.id,
                    sales_person: lead.user_id ? userMap.get(lead.user_id[0]) || 'No Sales Person' : 'No Sales Person',
                    supervisor_name: lead.supervisor_id ? this.cleanSupervisorName(supervisorMap.get(lead.supervisor_id[0])) || 'No Supervisor' : 'No Supervisor',
                    supervisor_id: lead.supervisor_id ? lead.supervisor_id[0] : 0,
                    wing_name: lead.wing_id ? wingMap.get(lead.wing_id[0]) || 'Team - Taj' : 'Team - Taj',
                    wing_manager_name: '',
                    event_type
                };
            });

            const activityEvents = filteredLeads
                .filter(lead => lead.stage_id && stageMap.get(lead.stage_id[0])?.toLowerCase().includes('won'))
                .map(lead => ({
                    lead_id: lead.id,
                    sales_person: lead.user_id ? userMap.get(lead.user_id[0]) || 'No Sales Person' : 'No Sales Person',
                    supervisor_name: lead.supervisor_id ? this.cleanSupervisorName(supervisorMap.get(lead.supervisor_id[0])) || 'No Supervisor' : 'No Supervisor',
                    supervisor_id: lead.supervisor_id ? lead.supervisor_id[0] : 0,
                    wing_name: lead.wing_id ? wingMap.get(lead.wing_id[0]) || 'Team - Taj' : 'Team - Taj',
                    wing_manager_name: '',
                    event_type: 'Won'
                }));

            const unionedEvents = [...leadEvents, ...activityEvents];

            const eventCounts = {};
            unionedEvents.forEach(event => {
                const key = `${event.wing_name}|${event.wing_manager_name}|${event.supervisor_name}|${event.sales_person}`;
                if (!eventCounts[key]) {
                    eventCounts[key] = {
                        wing_name: event.wing_name,
                        wing_manager_name: event.wing_manager_name,
                        supervisor_name: event.supervisor_name || 'No Supervisor',
                        supervisor_id: event.supervisor_id,
                        sales_person: event.sales_person,
                        prospect: 0,
                        follow_up: 0,
                        won: 0,
                        expired: 0
                    };
                }
                if (event.event_type === 'Prospect') eventCounts[key].prospect += 1;
                if (event.event_type === 'Follow Up') eventCounts[key].follow_up += 1;
                if (event.event_type === 'Won') eventCounts[key].won += 1;
                if (event.event_type === 'Expired') eventCounts[key].expired += 1;
            });

            const reservationCounts = {};
            reservations.forEach(res => {
                const lead = filteredLeads.find(l => l.id === (res.crm_lead_id ? res.crm_lead_id[0] : null));
                if (!lead) return;
                const key = `${lead.wing_id ? wingMap.get(lead.wing_id[0]) || 'Team - Taj' : 'Team - Taj'}||${lead.supervisor_id ? this.cleanSupervisorName(supervisorMap.get(lead.supervisor_id[0])) || 'No Supervisor' : 'No Supervisor'}|${lead.user_id ? userMap.get(lead.user_id[0]) || 'No Sales Person' : 'No Sales Person'}`;
                if (!reservationCounts[key]) {
                    reservationCounts[key] = {
                        wing_name: lead.wing_id ? wingMap.get(lead.wing_id[0]) || 'Team - Taj' : 'Team - Taj',
                        wing_manager_name: '',
                        supervisor_name: lead.supervisor_id ? this.cleanSupervisorName(supervisorMap.get(lead.supervisor_id[0])) || 'No Supervisor' : 'No Supervisor',
                        supervisor_id: lead.supervisor_id ? lead.supervisor_id[0] : 0,
                        sales_person: lead.user_id ? userMap.get(lead.user_id[0]) || 'No Sales Person' : 'No Sales Person',
                        reservation_count: 0,
                        sold_reservation_count: 0
                    };
                }
                reservationCounts[key].reservation_count += 1;
                if (res.status === 'sold') reservationCounts[key].sold_reservation_count += 1;
            });

            const data = [];
            const allKeys = new Set([...Object.keys(eventCounts), ...Object.keys(reservationCounts)]);
            allKeys.forEach(key => {
                const ec = eventCounts[key] || {};
                const rc = reservationCounts[key] || {};
                const record = {
                    wing_name: String(ec.wing_name || rc.wing_name || 'Team - Taj'),
                    wing_manager_name: String(ec.wing_manager_name || rc.wing_manager_name || ''),
                    supervisor_name: this.cleanSupervisorName(String(ec.supervisor_name || rc.supervisor_name || 'No Supervisor')),
                    supervisor_id: ec.supervisor_id || rc.supervisor_id || 0,
                    sales_person: String(ec.sales_person || rc.sales_person || 'No Sales Person'),
                    prospect: ec.prospect || 0,
                    follow_up: ec.follow_up || 0,
                    won: ec.won || 0,
                    expired: ec.expired || 0,
                    reservation_count: rc.reservation_count || 0,
                    sold_reservation_count: rc.sold_reservation_count || 0,
                    leads_count: (ec.prospect || 0) + (ec.follow_up || 0) + (rc.reservation_count || 0) + (ec.won || 0) + (ec.expired || 0)
                };
                data.push(record);
            });

            this.state.salesData = data;

            const totals = {
                prospects: 0,
                follow_ups: 0,
                reservations: 0,
                won: 0,
                expired: 0,
                sold_reservations: 0,
                leads_count: 0
            };

            data.forEach(record => {
                totals.prospects += record.prospect;
                totals.follow_ups += record.follow_up;
                totals.reservations += record.reservation_count;
                totals.won += record.won;
                totals.expired += record.expired;
                totals.sold_reservations += record.sold_reservation_count;
                totals.leads_count += record.leads_count;
            });

            this.state.totals = totals;

            if (data.length === 0) {
                this.state.errorMessage = "No data found for the selected date range.";
            }
        } catch (error) {
            console.error("Error fetching sales summary:", error);
            this.state.errorMessage = `Error loading data: ${error.message}`;
            this.state.salesData = [];
            this.state.totals = {
                prospects: 0,
                follow_ups: 0,
                reservations: 0,
                won: 0,
                expired: 0,
                sold_reservations: 0,
                leads_count: 0
            };
        } finally {
            this.state.loading = false;
            this.renderCharts();
        }
    }

    async onDateFilterChange(ev) {
        this.state.dateFilters[ev.target.name] = ev.target.value;
        await this.loadSalesData();
    }

    get summary() {
        return {
            sales_person: this.user.partnerDisplayName,
            prospect: this.state.totals.prospects,
            follow_up: this.state.totals.follow_ups,
            reservation_count: this.state.totals.reservations,
            sold_reservation_count: this.state.totals.sold_reservations,
            expired: this.state.totals.expired,
            won: this.state.totals.won,
            leads_count: this.state.totals.leads_count,
            total: this.state.totals.prospects + this.state.totals.follow_ups + 
                   this.state.totals.reservations + this.state.totals.won + 
                   this.state.totals.expired + this.state.totals.sold_reservations
        };
    }
}

MySalesSummaryDashboard.template = "temer_dashboard.my_sales_summary";
registry.category("actions").add("my_sales_summary", MySalesSummaryDashboard);