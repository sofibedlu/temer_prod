/** @odoo-module **/

import { Component, useState, onWillStart, onMounted, onPatched, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadBundle } from "@web/core/assets";
import { _t } from "@web/core/l10n/translation";

export class StockInventoryReportClient extends Component {
    setup() {
        this.notification = useService("notification");
        this.rpc = useService("rpc");
        this.typeChartRef = useRef("typeChart");
        this.wingChartRef = useRef("wingChart");
        this.typePieChartRef = useRef("typePieChart");
        this.advancedChartRef = useRef("advancedChart");
        this.wingAdvancedChartRef = useRef("wingAdvancedChart");
        this.reservationActivityChartRef = useRef("reservationActivityChart");
        this.typeMiniChartRef = useRef("typeMiniChart");
        this.wingMiniChartRef = useRef("wingMiniChart");
        this.stockPieChartRef = useRef("stockPieChart");
        this.wingMetricsChartRef = useRef("wingMetricsChart");
        this._typeChart = null;
        this._wingChart = null;
        this._typePieChart = null;
        this._advancedChart = null;
        this._wingAdvancedChart = null;
        this._reservationActivityChart = null;
        this._typeMiniChart = null;
        this._wingMiniChart = null;
        this._stockPieChart = null;
        this._wingMetricsChart = null;
        this._chartsRendered = false;

        const today = new Date();
        const formatDate = (date) => {
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            return `${year}-${month}-${day}`;
        };
        
        this.state = useState({
            loading: true,
            use_all_dates: false,
            date_from: formatDate(today),
            date_to: formatDate(today),
            data: {
                sites_handed_over: 0,
                available_properties: 0,
                available_sites: 0,
                stock_available: {
                    residence: { qty: 0, estimated_value: 0 },
                    shops: { qty: 0, estimated_value: 0 },
                    mixed: { qty: 0, estimated_value: 0 },
                    total: { qty: 0, estimated_value: 0 }
                },
                signed_contracts: 0,
                reservations: 0,
                cancelled_reservations: 0,
                expired_reservations: 0,
                refunds: { count: 0, value: 0 },
                sales_table: [],
                wing_metrics_table: [],
                total_sales_units: 0,
                total_available_stock: 0,
                inventory_absorption_ratio: 0,
                timeseries: {
                    labels: [],
                    sites_handed_over: [],
                    signed_contracts: [],
                    reservations: [],
                    cancelled_reservations: [],
                    expired_reservations: []
                }
            }
        });
        
        onWillStart(async () => {
            await loadBundle("web.chartjs_lib");
            await this.loadData();
        });

        onMounted(() => {
            if (!this.state.loading && !this._chartsRendered) {
                setTimeout(() => this.renderCharts(), 150);
            }
        });

        // IMPORTANT: only render once per data load to avoid infinite re-render/blinking
        onPatched(() => {
            if (!this.state.loading && !this._chartsRendered) {
                setTimeout(() => this.renderCharts(), 150);
            }
        });
    }
    
    _getEffectiveDates() {
        if (this.state.use_all_dates) {
            const today = new Date();
            return {
                date_from: '2000-01-01',
                date_to: `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`,
            };
        }
        return { date_from: this.state.date_from, date_to: this.state.date_to };
    }

    onAllDatesChange() {
        this.loadData();
    }

    async loadData() {
        this.state.loading = true;
        this._chartsRendered = false;
        const { date_from, date_to } = this._getEffectiveDates();
        try {
            const [result, timeseriesResult] = await Promise.all([
                this.rpc("/manager_reports/api/stock_inventory_data", {
                    date_from,
                    date_to,
                }),
                this.rpc("/manager_reports/api/stock_inventory_timeseries", {
                    date_from,
                    date_to,
                })
            ]);
            
            if (result.success) {
                this.state.data = result.data;
                if (timeseriesResult && timeseriesResult.success && timeseriesResult.data) {
                    this.state.data.timeseries = timeseriesResult.data;
                } else {
                    this.state.data.timeseries = {
                        labels: [],
                        sites_handed_over: [],
                        signed_contracts: [],
                        reservations: [],
                        cancelled_reservations: [],
                        expired_reservations: []
                    };
                }
            } else {
                this.notification.add(result.error || "Error loading data", { type: "danger" });
            }
        } catch (error) {
            console.error("Error loading data:", error);
            this.notification.add("Error loading report data", { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }
    
    onDateChange() {
        this.loadData();
    }

    renderCharts() {
        const Chart = window.Chart;
        if (!Chart || !Chart.prototype) {
            return;
        }
        const baseOptions = {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 900, easing: "easeOutQuart" },
            plugins: {
                tooltip: { enabled: true },
                legend: {
                    labels: {
                        boxWidth: 12,
                        boxHeight: 12,
                        font: { size: 11, weight: "600" },
                        color: "#1b5e20",
                    },
                },
            },
        };
        const axisOptions = {
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { color: "#1b5e20", font: { size: 11 } },
                },
                y: {
                    beginAtZero: true,
                    grid: { color: "rgba(46,125,50,0.12)" },
                    ticks: { color: "#1b5e20", font: { size: 11 } },
                },
            },
        };
        const barSpacing = {
            // Reduce empty space between bars
            datasets: {
                bar: {
                    categoryPercentage: 0.7,
                    barPercentage: 0.9,
                },
            },
        };

        // Destroy existing charts to avoid duplicates
        if (this._typeChart) {
            this._typeChart.destroy();
            this._typeChart = null;
        }
        if (this._wingChart) {
            this._wingChart.destroy();
            this._wingChart = null;
        }
        if (this._typePieChart) {
            this._typePieChart.destroy();
            this._typePieChart = null;
        }
        if (this._advancedChart) {
            this._advancedChart.destroy();
            this._advancedChart = null;
        }
        if (this._wingAdvancedChart) {
            this._wingAdvancedChart.destroy();
            this._wingAdvancedChart = null;
        }
        if (this._reservationActivityChart) {
            this._reservationActivityChart.destroy();
            this._reservationActivityChart = null;
        }
        if (this._typeMiniChart) {
            this._typeMiniChart.destroy();
            this._typeMiniChart = null;
        }
        if (this._wingMiniChart) {
            this._wingMiniChart.destroy();
            this._wingMiniChart = null;
        }
        if (this._stockPieChart) {
            this._stockPieChart.destroy();
            this._stockPieChart = null;
        }
        if (this._wingMetricsChart) {
            this._wingMetricsChart.destroy();
            this._wingMetricsChart = null;
        }

        // Stock pie chart (next to Stock Available table)
        const stockData = this.state.data && this.state.data.stock_available ? this.state.data.stock_available : {};
        if (this.stockPieChartRef.el && stockData) {
            const stockLabels = [];
            const stockValues = [];
            const stockColors = [];
            
            if (stockData.residence && (stockData.residence.qty > 0 || stockData.residence.estimated_value > 0)) {
                stockLabels.push('Residence');
                stockValues.push(stockData.residence.qty || 0);
                stockColors.push('#2e7d32');
            }
            if (stockData.shops && (stockData.shops.qty > 0 || stockData.shops.estimated_value > 0)) {
                stockLabels.push('Shops');
                stockValues.push(stockData.shops.qty || 0);
                stockColors.push('#00897b');
            }
            if (stockData.mixed && (stockData.mixed.qty > 0 || stockData.mixed.estimated_value > 0)) {
                stockLabels.push('Mixed');
                stockValues.push(stockData.mixed.qty || 0);
                stockColors.push('#1565c0');
            }
            
            if (stockLabels.length > 0) {
                this._stockPieChart = new Chart(this.stockPieChartRef.el, {
                    type: "doughnut",
                    data: {
                        labels: stockLabels,
                        datasets: [{
                            label: "Stock QTY",
                            data: stockValues,
                            backgroundColor: stockColors,
                            borderWidth: 0,
                        }],
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                position: 'bottom',
                                labels: {
                                    padding: 12,
                                    font: { size: 11 }
                                }
                            },
                            tooltip: {
                                callbacks: {
                                    label: (ctx) => {
                                        const label = ctx.label || '';
                                        const value = ctx.parsed || 0;
                                        const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                                        const percent = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                                        return `${label}: ${value} (${percent}%)`;
                                    }
                                }
                            }
                        }
                    },
                });
            }
        }

        // Chart 1: Sold units by type (Residences/Shops/Mixed) + Total
        const rows = (this.state.data && this.state.data.sales_table) ? this.state.data.sales_table : [];
        const typeRows = rows.filter(r => ["Residences", "Shops", "Mixed", "TOTAL"].includes(r.type));
        const wingRows = rows.filter(r => !["Residences", "Shops", "Mixed", "TOTAL"].includes(r.type));

        // Mini charts (next to table): only 2 bar charts
        if (this.typeMiniChartRef.el && typeRows.length) {
            this._typeMiniChart = new Chart(this.typeMiniChartRef.el, {
                type: "bar",
                data: {
                    labels: typeRows.map(r => r.type),
                    datasets: [{
                        label: "Unit Sold",
                        data: typeRows.map(r => r.unit_sold || 0),
                        backgroundColor: ["#2e7d32", "#00897b", "#1565c0", "#00695c"],
                        borderRadius: 8,
                        maxBarThickness: 40,
                    }],
                },
                options: {
                    ...baseOptions,
                    ...axisOptions,
                    ...barSpacing,
                    plugins: { ...baseOptions.plugins, legend: { display: false } },
                },
            });
        }

        if (this.wingMiniChartRef.el && wingRows.length) {
            const barPalette = ['#2e7d32', '#00897b', '#1565c0', '#00695c', '#0097a7', '#5e35b1'];
            const colors = wingRows.map((_, i) => barPalette[i % barPalette.length]);
            this._wingMiniChart = new Chart(this.wingMiniChartRef.el, {
                type: "bar",
                data: {
                    labels: wingRows.map(r => r.type),
                    datasets: [{
                        label: "Unit Sold",
                        data: wingRows.map(r => r.unit_sold || 0),
                        backgroundColor: colors,
                        borderRadius: 8,
                        maxBarThickness: 34,
                    }],
                },
                options: {
                    ...baseOptions,
                    ...axisOptions,
                    ...barSpacing,
                    plugins: { ...baseOptions.plugins, legend: { display: false } },
                },
            });
        }

        if (this.typeChartRef.el && typeRows.length) {
            this._typeChart = new Chart(this.typeChartRef.el, {
                type: "bar",
                data: {
                    labels: typeRows.map(r => r.type),
                    datasets: [{
                        label: "Unit Sold",
                        data: typeRows.map(r => r.unit_sold || 0),
                        backgroundColor: ["#2e7d32", "#00897b", "#1565c0", "#00695c"],
                        borderRadius: 8,
                        maxBarThickness: 46,
                    }],
                },
                options: {
                    ...baseOptions,
                    ...axisOptions,
                    ...barSpacing,
                },
            });
        }

        // Chart 2: Sold units by wing (exclude type rows and TOTAL)
        if (this.wingChartRef.el && wingRows.length) {
            const barPalette = ['#2e7d32', '#00897b', '#1565c0', '#00695c', '#0097a7', '#5e35b1'];
            const colors = wingRows.map((_, i) => barPalette[i % barPalette.length]);
            this._wingChart = new Chart(this.wingChartRef.el, {
                type: "bar",
                data: {
                    labels: wingRows.map(r => r.type),
                    datasets: [{
                        label: "Unit Sold (Wings)",
                        data: wingRows.map(r => r.unit_sold || 0),
                        backgroundColor: colors,
                        borderRadius: 8,
                    }],
                },
                options: {
                    ...baseOptions,
                    ...axisOptions,
                    ...barSpacing,
                    plugins: { ...baseOptions.plugins, legend: { display: false } },
                },
            });
        }

        // Chart 3: Doughnut (type distribution by total price)
        const pieRows = rows.filter(r => ["Residences", "Shops", "Mixed"].includes(r.type));
        if (this.typePieChartRef.el && pieRows.length) {
            this._typePieChart = new Chart(this.typePieChartRef.el, {
                type: "doughnut",
                data: {
                    labels: pieRows.map(r => r.type),
                    datasets: [{
                        label: "Total Price",
                        data: pieRows.map(r => r.total_price || 0),
                        backgroundColor: ["#2e7d32", "#00897b", "#1565c0"],
                        borderWidth: 0,
                    }],
                },
                options: {
                    ...baseOptions,
                    cutout: "65%",
                    plugins: { ...baseOptions.plugins, legend: { position: "bottom", ...baseOptions.plugins.legend } },
                },
            });
        }

        // Chart 4: Advanced Paid by Type
        if (this.advancedChartRef.el && pieRows.length) {
            this._advancedChart = new Chart(this.advancedChartRef.el, {
                type: "bar",
                data: {
                    labels: pieRows.map(r => r.type),
                    datasets: [{
                        label: "Advanced Paid (ETB)",
                        data: pieRows.map(r => (r.advanced_paid && r.advanced_paid.value) ? r.advanced_paid.value : 0),
                        backgroundColor: ["#2e7d32", "#00897b", "#1565c0"],
                        borderRadius: 8,
                    }],
                },
                options: {
                    ...baseOptions,
                    ...axisOptions,
                    ...barSpacing,
                },
            });
        }

        // Chart 5: Advanced Paid by Wing
        if (this.wingAdvancedChartRef.el && wingRows.length) {
            const barPalette = ['#2e7d32', '#00897b', '#1565c0', '#00695c', '#0097a7', '#5e35b1'];
            const colors = wingRows.map((_, i) => barPalette[i % barPalette.length]);
            this._wingAdvancedChart = new Chart(this.wingAdvancedChartRef.el, {
                type: "bar",
                data: {
                    labels: wingRows.map(r => r.type),
                    datasets: [{
                        label: "Advanced Paid (ETB)",
                        data: wingRows.map(r => (r.advanced_paid && r.advanced_paid.value) ? r.advanced_paid.value : 0),
                        backgroundColor: colors,
                        borderRadius: 8,
                    }],
                },
                options: {
                    ...baseOptions,
                    ...axisOptions,
                    ...barSpacing,
                    plugins: { ...baseOptions.plugins, legend: { display: false } },
                },
            });
        }

        // Chart 5b: Per Wing - Reservations, Cancelled, Expired (counts only; Advanced Paid removed - money vs count not comparable)
        const wingMetrics = this.state.data.wing_metrics_table || [];
        if (this.wingMetricsChartRef.el && wingMetrics.length > 0) {
            const labels = wingMetrics.map(r => r.wing_name);
            this._wingMetricsChart = new Chart(this.wingMetricsChartRef.el, {
                type: "bar",
                data: {
                    labels,
                    datasets: [
                        {
                            label: "Reservations",
                            data: wingMetrics.map(r => r.reservations || 0),
                            backgroundColor: "#00897b",
                            borderRadius: 6,
                        },
                        {
                            label: "Cancelled",
                            data: wingMetrics.map(r => r.cancelled || 0),
                            backgroundColor: "#ef4444",
                            borderRadius: 6,
                        },
                        {
                            label: "Expired",
                            data: wingMetrics.map(r => r.expired || 0),
                            backgroundColor: "#00695c",
                            borderRadius: 6,
                        },
                    ],
                },
                options: {
                    ...baseOptions,
                    ...axisOptions,
                    responsive: true,
                    plugins: { ...baseOptions.plugins, legend: { display: true, position: "top" } },
                    scales: {
                        x: {
                            grid: { display: false },
                            ticks: { color: "#1b5e20", font: { size: 10 }, maxRotation: 45 },
                        },
                        y: {
                            beginAtZero: true,
                            title: { display: true, text: "Count" },
                            grid: { color: "rgba(46,125,50,0.12)" },
                            ticks: { color: "#1b5e20", precision: 0 },
                        },
                    },
                    datasets: {
                        bar: {
                            categoryPercentage: 0.8,
                            barPercentage: 0.9,
                        },
                    },
                },
            });
        }

        // Chart 6: Currently Reserved / Cancelled / Expired - line graph
        const ts = this.state.data.timeseries || {};
        if (this.reservationActivityChartRef.el && ts.labels && ts.labels.length > 0) {
            this._reservationActivityChart = new Chart(this.reservationActivityChartRef.el, {
                type: "line",
                data: {
                    labels: ts.labels,
                    datasets: [
                        {
                            label: "Currently Reserved",
                            data: ts.reservations || [],
                            borderColor: "#2e7d32",
                            backgroundColor: "rgba(46, 125, 50, 0.15)",
                            fill: false,
                            tension: 0.4,
                            borderWidth: 3,
                            pointRadius: 4,
                            pointHoverRadius: 6,
                        },
                        {
                            label: "Cancelled",
                            data: ts.cancelled_reservations || [],
                            borderColor: "#ef4444",
                            backgroundColor: "rgba(239, 68, 68, 0.1)",
                            fill: false,
                            tension: 0.4,
                            borderWidth: 3,
                            pointRadius: 4,
                            pointHoverRadius: 6,
                        },
                        {
                            label: "Expired",
                            data: ts.expired_reservations || [],
                            borderColor: "#00897b",
                            backgroundColor: "rgba(0, 137, 123, 0.15)",
                            fill: false,
                            tension: 0.4,
                            borderWidth: 3,
                            pointRadius: 4,
                            pointHoverRadius: 6,
                        },
                    ],
                },
                options: {
                    ...baseOptions,
                    ...axisOptions,
                    scales: axisOptions.scales,
                    plugins: { ...baseOptions.plugins, legend: { display: true, position: "top" } },
                },
            });
        }

        this._chartsRendered = true;
    }

    _getChartImages() {
        const safeImg = (chart) => {
            try {
                return chart ? chart.toBase64Image() : "";
            } catch (e) {
                return "";
            }
        };
        return {
            type_chart: safeImg(this._typeChart),
            wing_chart: safeImg(this._wingChart),
            pie_chart: safeImg(this._typePieChart),
            advanced_chart: safeImg(this._advancedChart),
            wing_advanced_chart: safeImg(this._wingAdvancedChart),
            wing_metrics_chart: safeImg(this._wingMetricsChart),
            reservation_activity_chart: safeImg(this._reservationActivityChart),
            type_mini_chart: safeImg(this._typeMiniChart),
            wing_mini_chart: safeImg(this._wingMiniChart),
            stock_pie_chart: safeImg(this._stockPieChart),
        };
    }

    _postDownload(url, payload, openInNewWindow = false) {
        // Create a form POST to download binary (xlsx/pdf)
        const form = document.createElement("form");
        form.method = "POST";
        form.action = url;
        form.style.display = "none";
        if (openInNewWindow) {
            form.target = "_blank"; // Open response in new tab so closing it does not close the main app
        }
        Object.entries(payload).forEach(([k, v]) => {
            const input = document.createElement("input");
            input.type = "hidden";
            input.name = k;
            input.value = v === undefined || v === null ? "" : String(v);
            form.appendChild(input);
        });
        document.body.appendChild(form);
        form.submit();
        document.body.removeChild(form);
    }

    exportExcel() {
        const { date_from, date_to } = this._getEffectiveDates();
        const images = this._getChartImages();
        this._postDownload("/manager_reports/api/export_stock_inventory_excel", Object.assign({
            date_from,
            date_to,
        }, images));
    }

    exportPDF() {
        const { date_from, date_to } = this._getEffectiveDates();
        const images = this._getChartImages();
        this._postDownload("/manager_reports/api/export_stock_inventory_pdf", Object.assign({
            date_from,
            date_to,
        }, images), true); // open in new window so cancel/close only closes the preview
    }
    
    formatCurrency(value) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'ETB',
            minimumFractionDigits: 0
        }).format(value || 0);
    }
    
    formatNumber(value) {
        return new Intl.NumberFormat('en-US').format(value || 0);
    }

    t(key) {
        return _t(key);
    }
}

StockInventoryReportClient.template = "manager_reports.StockInventoryReportClient";

registry.category("actions").add("manager_reports.stock_inventory", StockInventoryReportClient);

