// /** @odoo-module **/

// import { registry } from "@web/core/registry";
// import { useService } from "@web/core/utils/hooks";
// import { Component, onWillStart, useState } from "@odoo/owl";
// import { loadJS } from "@web/core/assets";
// import { formatMonetary } from "@web/views/fields/formatters";

// class SalesPerformanceDashboard extends Component {
//     setup() {
//         this.orm = useService("orm");
//         this.action = useService("action");
//         // expose formatter for template, ensure value is a finite number
//         this.formatCurrency = (val) => {
//             let num = 0;
//             if (typeof val === "number" && isFinite(val)) {
//                 num = val;
//             } else if (typeof val === "string" && val.trim() !== "") {
//                 num = parseFloat(val.replace(/,/g, "")) || 0;
//             }
//             if (!isFinite(num)) num = 0;
//             return formatMonetary({ value: num });
//         };

//         this.state = useState({
//             loading: true,
//             data: [],
//             summary: {
//                 totalPlanned: 0,
//                 totalActual: 0,
//                 totalDeviation: 0,
//                 avgDeviationPercent: 0
//             },
//             filters: {
//                 dateStart: this.getDefaultStartDate(),
//                 dateEnd: this.getDefaultEndDate()
//             }
//         });
        
//         onWillStart(async () => {
//             await loadJS(["/web/static/lib/Chart/Chart.js"]);
//             await this.fetchData();
//         });
//     }

//     getDefaultStartDate() {
//         const date = new Date();
//         date.setMonth(0);
//         date.setDate(1);
//         return date.toISOString().split('T')[0];
//     }

//     getDefaultEndDate() {
//         return new Date().toISOString().split('T')[0];
//     }

//     async fetchData() {
//         this.state.loading = true;
//         try {
//             // Execute the raw SQL query
//             const results = await this.orm.query(this.getQuery(), {
//                 params: {
//                     date_start: this.state.filters.dateStart,
//                     date_end: this.state.filters.dateEnd
//                 }
//             });

//             // Process results
//             let totalPlanned = 0;
//             let totalActual = 0;
            
//             const processedData = results.map(row => {
//                 totalPlanned += row.planned_revenue;
//                 totalActual += row.actual_revenue;
                
//                 return {
//                     productId: row.product_id,
//                     productName: row.product_name,
//                     categoryId: row.category_id,
//                     categoryName: row.category_name,
//                     planned: row.planned_revenue,
//                     actual: row.actual_revenue,
//                     deviation: row.deviation,
//                     deviationPercent: row.deviation_percent || 0
//                 };
//             });

//             this.state.data = processedData;
//             this.state.summary = {
//                 totalPlanned,
//                 totalActual,
//                 totalDeviation: totalActual - totalPlanned,
//                 avgDeviationPercent: totalPlanned > 0 ? 
//                     ((totalActual - totalPlanned) / totalPlanned * 100).toFixed(2) : 0
//             };
            
//         } catch (error) {
//             console.error("Error fetching sales performance data:", error);
//         } finally {
//             this.state.loading = false;
//         }
//     }

//     getQuery() {
//         return `
//             WITH planned AS (
//                 SELECT
//                     stp.product_id,
//                     pt.name AS product_name,
//                     stp.product_categ_id,
//                     pc.name AS category_name,
//                     SUM(stp.target_revenue) AS planned_revenue
//                 FROM sales_target_plan stp
//                 LEFT JOIN product_product pp ON stp.product_id = pp.id
//                 LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id
//                 LEFT JOIN product_category pc ON stp.product_categ_id = pc.id
//                 WHERE stp.period BETWEEN $1 AND $2
//                 GROUP BY stp.product_id, pt.name, stp.product_categ_id, pc.name
//             ),
//             actual AS (
//                 SELECT
//                     sol.product_id,
//                     pt.name AS product_name,
//                     pt.categ_id AS product_categ_id,
//                     pc.name AS category_name,
//                     SUM(sol.price_total) AS actual_revenue
//                 FROM sale_order_line sol
//                 JOIN sale_order so ON sol.order_id = so.id
//                 JOIN product_product pp ON sol.product_id = pp.id
//                 JOIN product_template pt ON pp.product_tmpl_id = pt.id
//                 JOIN product_category pc ON pt.categ_id = pc.id
//                 WHERE so.state IN ('sale', 'done')
//                 AND so.date_order BETWEEN $1 AND $2
//                 GROUP BY sol.product_id, pt.name, pt.categ_id, pc.name
//             )
//             SELECT
//                 COALESCE(p.product_id, a.product_id) AS product_id,
//                 COALESCE(p.product_name, a.product_name) AS product_name,
//                 COALESCE(p.product_categ_id, a.product_categ_id) AS category_id,
//                 COALESCE(p.category_name, a.category_name) AS category_name,
//                 COALESCE(p.planned_revenue, 0) AS planned_revenue,
//                 COALESCE(a.actual_revenue, 0) AS actual_revenue,
//                 (COALESCE(a.actual_revenue, 0) - COALESCE(p.planned_revenue, 0)) AS deviation,
//                 CASE 
//                     WHEN COALESCE(p.planned_revenue, 0) <> 0 THEN
//                         ROUND((100.0 * (COALESCE(a.actual_revenue, 0) - COALESCE(p.planned_revenue, 0)) / COALESCE(p.planned_revenue, 1))::numeric, 2)
//                     ELSE NULL
//                 END AS deviation_percent
//             FROM planned p
//             FULL OUTER JOIN actual a
//                 ON p.product_id = a.product_id
//             ORDER BY category_name, product_name;
//         `;
//     }

//     applyFilters() {
//         this.fetchData();
//     }

//     resetFilters() {
//         this.state.filters.dateStart = this.getDefaultStartDate();
//         this.state.filters.dateEnd = this.getDefaultEndDate();
//         this.fetchData();
//     }

//     openProduct(productId) {
//         this.action.doAction({
//             type: "ir.actions.act_window",
//             res_model: "product.product",
//             res_id: productId,
//             views: [[false, "form"]],
//             target: "current"
//         });
//     }
// }


// // SalesPerformanceDashboard.template = "sales_performance.Dashboard";

// const actionRegistry = registry.category("actions");

// SalesPerformanceDashboard.template = "crm_dashboard.sales_performance_dashboard";
// actionRegistry.add("sales_performance_dashboard", SalesPerformanceDashboard);






/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";
import { loadJS } from "@web/core/assets";
import { formatMonetary } from "@web/views/fields/formatters";

class SalesPerformanceDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        
        // Robust currency formatter
        this.formatCurrency = (value) => {
            // Handle null/undefined
            if (value == null) return formatMonetary(0);
            
            // Convert to number if it's a string
            let num = typeof value === 'string' 
                ? parseFloat(value.replace(/[^0-9.-]/g, '')) 
                : value;
                
            // Ensure we have a valid number
            num = typeof num === 'number' && !isNaN(num) ? num : 0;
            return formatMonetary(num);
        };

        this.state = useState({
            loading: true,
            data: [],
            summary: {
                totalPlanned: 0,
                totalActual: 0,
                totalDeviation: 0,
                avgDeviationPercent: "0.00"
            },
            filters: {
                dateStart: this.getDefaultStartDate(),
                dateEnd: this.getDefaultEndDate()
            }
        });
        
        onWillStart(async () => {
            await loadJS(["/web/static/lib/Chart/Chart.js"]);
            await this.fetchData();
        });
    }

    getDefaultStartDate() {
        const date = new Date();
        date.setMonth(0);
        date.setDate(1);
        return date.toISOString().split('T')[0];
    }

    getDefaultEndDate() {
        return new Date().toISOString().split('T')[0];
    }

    async fetchData() {
        this.state.loading = true;
        try {
            const results = await this.orm.query(this.getQuery(), {
                params: {
                    date_start: this.state.filters.dateStart,
                    date_end: this.state.filters.dateEnd
                }
            });

            let totalPlanned = 0;
            let totalActual = 0;
            
            const processedData = results.map(row => {
                const planned = this.parseNumber(row.planned_revenue);
                const actual = this.parseNumber(row.actual_revenue);
                const deviation = actual - planned;
                const deviationPercent = row.deviation_percent ? 
                    this.parseNumber(row.deviation_percent).toFixed(2) : "0.00";
                
                totalPlanned += planned;
                totalActual += actual;
                
                return {
                    productId: row.product_id,
                    productName: row.product_name || "Unknown Product",
                    categoryId: row.category_id,
                    categoryName: row.category_name || "Uncategorized",
                    planned,
                    actual,
                    deviation,
                    deviationPercent
                };
            });

            const totalDeviation = totalActual - totalPlanned;
            const avgDeviationPercent = totalPlanned > 0 ? 
                ((totalDeviation / totalPlanned) * 100).toFixed(2) : "0.00";

            this.state.data = processedData;
            this.state.summary = {
                totalPlanned,
                totalActual,
                totalDeviation,
                avgDeviationPercent
            };
            
        } catch (error) {
            console.error("Error fetching sales performance data:", error);
            this.state.data = [];
            this.state.summary = {
                totalPlanned: 0,
                totalActual: 0,
                totalDeviation: 0,
                avgDeviationPercent: "0.00"
            };
        } finally {
            this.state.loading = false;
        }
    }

    parseNumber(value) {
        if (value == null) return 0;
        const num = typeof value === 'string' 
            ? parseFloat(value.replace(/[^0-9.-]/g, '')) 
            : value;
        return typeof num === 'number' && !isNaN(num) ? num : 0;
    }

    getQuery() {
        return `
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
                WHERE stp.period BETWEEN $1 AND $2
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
                WHERE so.state IN ('sale', 'done')
                AND so.date_order BETWEEN $1 AND $2
                GROUP BY sol.product_id, pt.name, pt.categ_id, pc.name
            )
            SELECT
                COALESCE(p.product_id, a.product_id) AS product_id,
                COALESCE(p.product_name, a.product_name) AS product_name,
                COALESCE(p.product_categ_id, a.product_categ_id) AS category_id,
                COALESCE(p.category_name, a.category_name) AS category_name,
                COALESCE(p.planned_revenue, 0) AS planned_revenue,
                COALESCE(a.actual_revenue, 0) AS actual_revenue,
                (COALESCE(a.actual_revenue, 0) - COALESCE(p.planned_revenue, 0)) AS deviation,
                CASE 
                    WHEN COALESCE(p.planned_revenue, 0) <> 0 THEN
                        ROUND((100.0 * (COALESCE(a.actual_revenue, 0) - COALESCE(p.planned_revenue, 0)) / COALESCE(p.planned_revenue, 1))::numeric, 2)
                    ELSE NULL
                END AS deviation_percent
            FROM planned p
            FULL OUTER JOIN actual a
                ON p.product_id = a.product_id
            ORDER BY category_name, product_name;
        `;
    }

    applyFilters() {
        this.fetchData();
    }

    resetFilters() {
        this.state.filters.dateStart = this.getDefaultStartDate();
        this.state.filters.dateEnd = this.getDefaultEndDate();
        this.fetchData();
    }

    openProduct(productId) {
        if (productId) {
            this.action.doAction({
                type: "ir.actions.act_window",
                res_model: "product.product",
                res_id: productId,
                views: [[false, "form"]],
                target: "current"
            });
        }
    }
}

SalesPerformanceDashboard.template = "crm_dashboard.sales_performance_dashboard";
registry.category("actions").add("sales_performance_dashboard", SalesPerformanceDashboard);