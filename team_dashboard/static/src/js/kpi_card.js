/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useRef, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { loadJS } from "@web/core/assets";
import { getColor } from "@web/core/colors/colors";

const actionRegistry = registry.category("actions");

export class AnnualProductionDashboard extends Component {
    getDefaultStartDate() {
        const date = new Date();
        date.setMonth(0);
        date.setDate(1);
        return date.toISOString().split('T')[0];
    }
    getDefaultEndDate() {
        return new Date().toISOString().split('T')[0];
    }

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        this.selectedProductId = useState({ value: null });
        this.productList = useState([]);

        this.dateFilters = useState({
            startDate: this.getDefaultStartDate(),
            endDate: this.getDefaultEndDate(),
        });
        this.stats = useState({
            totalPlanned: 0,
            totalProduced: 0,
            totalDifference: 0,
            productData: [],
            monthlyData: [],
            isLoaded: false,
            salesRevenue: {
                target: 0, actual: 0, deviation: 0, deviationPerc: 0,
                byProduct: [], byCategory: []
            },
            salesQty: { target: 0, actual: 0, deviation: 0 },
            salesCommission: {
                sold: 0, paid: 0, deviation: 0, deviationPerc: 0, bySalesperson: []
            },
            selectedProductStats: null,
        });

        this.barChartRef = useRef("barChart");
        this.pieChartRef = useRef("pieChart");
        this.lineChartRef = useRef("lineChart");
        this.productChartRef = useRef("productChart");

        this.charts = {
            barChart: null,
            pieChart: null,
            lineChart: null,
            productChart: null,
        };

        onWillStart(async () => {
            await loadJS(["/web/static/lib/Chart/Chart.js"]);
            await this.loadProductList();
            await this.fetchStats();
        });

        onMounted(() => {
            this.renderCharts();
            window.addEventListener("resize", this.handleResize);
        });

        onWillUnmount(() => {
            this.destroyAllCharts();
            window.removeEventListener("resize", this.handleResize);
        });
    }

    destroyAllCharts() {
        Object.values(this.charts).forEach((chart) => {
            if (chart) {
                chart.destroy();
            }
        });
        this.charts = {
            barChart: null,
            pieChart: null,
            lineChart: null,
            productChart: null,
        };
    }

    handleResize = () => {
        clearTimeout(this.resizeTimer);
        this.resizeTimer = setTimeout(() => {
            this.renderCharts();
        }, 200);
    };

    async loadProductList() {
        const productIds = await this.orm.search("product.product", [], { limit: 1000 });
        if (productIds.length) {
            const products = await this.orm.read("product.product", productIds, ['name']);
            this.productList.splice(0, this.productList.length, ...products);
        }
    }

    async fetchStats() {
        try {
            // 1. Get planned quantity by product & month
            const plannedGroups = await this.orm.readGroup(
                "annual.production.plan",
                [],
                ["product_id", "planned_quantity"],
                ["product_id", "create_date:month"],
                { lazy: false }
            );

            // 2. Get produced quantity by product & month
            const producedGroups = await this.orm.readGroup(
                "mrp.production",
                [["state", "=", "done"]],
                ["product_id", "product_qty"],
                ["product_id", "date_start:month"],
                { lazy: false }
            );

            // 3. Index for easy merging
            const productMonthMap = {};
            let totalPlanned = 0;
            let totalProduced = 0;

            // Build planned data map
            plannedGroups.forEach((item) => {
                const productId = item.product_id && item.product_id[0];
                const productName = item.product_id && item.product_id[1];
                const month = item["create_date:month"];
                const key = productId + ":" + month;
                if (!productMonthMap[key]) {
                    productMonthMap[key] = {
                        product_id: productId,
                        product_name: productName,
                        month: month,
                        planned: 0,
                        produced: 0,
                    };
                }
                productMonthMap[key].planned = item.planned_quantity || 0;
                totalPlanned += item.planned_quantity || 0;
            });

            // Merge produced data
            producedGroups.forEach((item) => {
                const productId = item.product_id && item.product_id[0];
                const productName = item.product_id && item.product_id[1];
                const month = item["date_start:month"];
                const key = productId + ":" + month;
                if (!productMonthMap[key]) {
                    productMonthMap[key] = {
                        product_id: productId,
                        product_name: productName,
                        month: month,
                        planned: 0,
                        produced: 0,
                    };
                }
                productMonthMap[key].produced = item.product_qty || 0;
                totalProduced += item.product_qty || 0;
            });

            // Prepare arrays for charts
            const productMap = {};
            const monthMap = {};
            Object.values(productMonthMap).forEach((item) => {
                // Product-wise sum
                if (!productMap[item.product_name]) {
                    productMap[item.product_name] = { name: item.product_name, planned: 0, produced: 0, difference: 0 };
                }
                productMap[item.product_name].planned += item.planned;
                productMap[item.product_name].produced += item.produced;

                // Month-wise produced sum
                if (!monthMap[item.month]) {
                    monthMap[item.month] = 0;
                }
                monthMap[item.month] += item.produced || 0;
            });

            // Calculate differences
            Object.values(productMap).forEach((prod) => {
                prod.difference = prod.planned - prod.produced;
            });

            // Prepare final lists for charts
            const productData = Object.values(productMap);
            const monthlyData = Object.entries(monthMap).map(([month, quantity]) => ({
                month,
                quantity,
            }));

            this.stats.totalPlanned = totalPlanned;
            this.stats.totalProduced = totalProduced;
            this.stats.totalDifference = totalPlanned - totalProduced;
            this.stats.productData = productData;
            this.stats.monthlyData = monthlyData;
            this.stats.isLoaded = true;

            // now load sales figures
            await this.fetchSalesStats();
        } catch (error) {
            console.error("Error fetching production stats:", error);
        }
    }

    async fetchSalesStats() {
        const sql = `
            WITH planned AS (
                SELECT
                    stp.product_id,
                    pt.name AS product_name,
                    stp.product_categ_id,
                    pc.name AS category_name,
                    SUM(stp.target_revenue) AS planned_revenue
                FROM sales_target_plan stp
                LEFT JOIN product_product pp ON stp.product_id = pp.id
                LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id
                LEFT JOIN product_category pc ON stp.product_categ_id = pc.id
                WHERE stp.period >= $1 AND stp.period <= $2
                GROUP BY stp.product_id, pt.name, stp.product_categ_id, pc.name
            ),
            actual AS (
                SELECT
                    sol.product_id,
                    pt.name AS product_name,
                    pt.categ_id AS product_categ_id,
                    pc.name AS category_name,
                    SUM(sol.price_total) AS actual_revenue
                FROM sale_order_line sol
                JOIN sale_order so ON sol.order_id = so.id
                JOIN product_product pp ON sol.product_id = pp.id
                JOIN product_template pt ON pp.product_tmpl_id = pt.id
                JOIN product_category pc ON pt.categ_id = pc.id
                WHERE so.state IN ('sale','done')
                  AND so.date_order >= $1 AND so.date_order <= $2
                GROUP BY sol.product_id, pt.name, pt.categ_id, pc.name
            )
            SELECT
                COALESCE(p.product_id, a.product_id) AS product_id,
                COALESCE(p.product_name, a.product_name) AS product_name,
                COALESCE(p.product_categ_id, a.product_categ_id) AS category_id,
                COALESCE(p.category_name, a.category_name) AS category_name,
                COALESCE(p.planned_revenue,0) AS planned_revenue,
                COALESCE(a.actual_revenue,0) AS actual_revenue,
                (COALESCE(a.actual_revenue,0) - COALESCE(p.planned_revenue,0)) AS deviation,
                CASE WHEN COALESCE(p.planned_revenue,0)<>0
                    THEN ROUND((100.0*(COALESCE(a.actual_revenue,0)-COALESCE(p.planned_revenue,0))/COALESCE(p.planned_revenue,1))::numeric,2)
                    ELSE 0 END AS deviation_percent
            FROM planned p
            FULL OUTER JOIN actual a ON p.product_id = a.product_id
            ORDER BY category_name, product_name
        `;
        const params = [this.dateFilters.startDate, this.dateFilters.endDate + ' 23:59:59'];
        const rows = await this.orm.query(sql, params);

        console.log("Sales SQL result:", rows); // <-- log the result

        // map into byProduct array
        this.stats.salesRevenue.byProduct = rows.map(r => ({
            product_id: r.product_id,
            product_name: r.product_name,
            category_name: r.category_name,
            planned: r.planned_revenue,
            actual: r.actual_revenue,
            deviation: r.deviation,
            deviationPerc: r.deviation_percent,
        }));
        // totals
        const totalPlanned = rows.reduce((s,r) => s + r.planned_revenue, 0);
        const totalActual  = rows.reduce((s,r) => s + r.actual_revenue,  0);
        const totalDev     = totalActual - totalPlanned;
        const totalDevPerc = totalPlanned
            ? ((100 * totalDev / totalPlanned).toFixed(2))
            : 0;
        this.stats.salesRevenue.target = totalPlanned;
        this.stats.salesRevenue.actual = totalActual;
        this.stats.salesRevenue.deviation = totalDev;
        this.stats.salesRevenue.deviationPerc = totalDevPerc;
    }

    goToProductionPlans() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "annual.production.plan",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
            domain: [],
        });
    }

    goToManufacturingOrders() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "mrp.production",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
            domain: [['state', '=', 'done']],
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

    renderCharts() {
        this.destroyAllCharts();

        // Bar Chart - Planned vs Produced vs Difference
        if (this.stats.isLoaded && this.barChartRef.el) {
            try {
                this.charts.barChart = new Chart(this.barChartRef.el, {
                    type: "bar",
                    data: {
                        labels: ["Planned", "Produced", "Difference"],
                        datasets: [
                            {
                                label: "Quantity",
                                data: [
                                    this.stats.totalPlanned,
                                    this.stats.totalProduced,
                                    this.stats.totalDifference,
                                ],
                                backgroundColor: [getColor(0), getColor(1), getColor(2)],
                                borderColor: [
                                    getColor(0).replace("0.6", "1"),
                                    getColor(1).replace("0.6", "1"),
                                    getColor(2).replace("0.6", "1"),
                                ],
                                borderWidth: 1,
                            },
                        ],
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: {
                                beginAtZero: true,
                            },
                        },
                    },
                });
            } catch (error) {
                console.error("Error rendering bar chart:", error);
            }
        }

        // Pie Chart - Production Distribution
        if (this.stats.isLoaded && this.pieChartRef.el) {
            try {
                this.charts.pieChart = new Chart(this.pieChartRef.el, {
                    type: "pie",
                    data: {
                        labels: ["Planned", "Produced"],
                        datasets: [
                            {
                                data: [this.stats.totalPlanned, this.stats.totalProduced],
                                backgroundColor: [getColor(0), getColor(1)],
                                borderWidth: 1,
                            },
                        ],
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                    },
                });
            } catch (error) {
                console.error("Error rendering pie chart:", error);
            }
        }

        // Line Chart - Monthly Production Trend
        if (this.stats.monthlyData.length && this.lineChartRef.el) {
            try {
                const labels = this.stats.monthlyData.map((item) => item.month);
                const data = this.stats.monthlyData.map((item) => item.quantity);

                this.charts.lineChart = new Chart(this.lineChartRef.el, {
                    type: "line",
                    data: {
                        labels: labels,
                        datasets: [
                            {
                                label: "Monthly Production",
                                data: data,
                                backgroundColor: getColor(3),
                                borderColor: getColor(3).replace("0.6", "1"),
                                borderWidth: 2,
                                fill: true,
                                tension: 0.4,
                            },
                        ],
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: {
                                beginAtZero: true,
                            },
                        },
                    },
                });
            } catch (error) {
                console.error("Error rendering line chart:", error);
            }
        }

        // Product Chart - Product Comparison
        if (this.stats.productData.length && this.productChartRef.el) {
            try {
                const labels = this.stats.productData.map((item) => item.name);
                const plannedData = this.stats.productData.map((item) => item.planned);
                const producedData = this.stats.productData.map((item) => item.produced);

                this.charts.productChart = new Chart(this.productChartRef.el, {
                    type: "bar",
                    data: {
                        labels: labels,
                        datasets: [
                            {
                                label: "Planned",
                                data: plannedData,
                                backgroundColor: getColor(4),
                                borderColor: getColor(4).replace("0.6", "1"),
                                borderWidth: 1,
                            },
                            {
                                label: "Produced",
                                data: producedData,
                                backgroundColor: getColor(5),
                                borderColor: getColor(5).replace("0.6", "1"),
                                borderWidth: 1,
                            },
                        ],
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: {
                                beginAtZero: true,
                            },
                        },
                    },
                });
            } catch (error) {
                console.error("Error rendering product chart:", error);
            }
        }
    }
}

AnnualProductionDashboard.template = "crm_dashboard.annual";
actionRegistry.add("annual", AnnualProductionDashboard);























