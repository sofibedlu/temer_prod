/** @odoo-module **/

import { Component, useState, onWillStart, onPatched, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadBundle } from "@web/core/assets";
import { _t } from "@web/core/l10n/translation";

export class SalesPerformanceReportClient extends Component {
    setup() {
        this.notification = useService("notification");
        this.rpc = useService("rpc");
        
        // Chart refs
        this.openingStockPieChartRef = useRef("openingStockPieChart");
        this.reportContentRef = useRef("reportContent");
        this.wingComparisonTimelineChartRef = useRef("wingComparisonTimelineChart");
        this.activityTimeseriesChartRef = useRef("activityTimeseriesChart");
        
        // Chart instances
        this._openingStockPieChart = null;
        this._wingCharts = {};  // { 'wingId-qty': chart, 'wingId-money': chart }
        
        // Flag to prevent infinite rendering loops
        this._chartsRendered = false;
        this._isRenderingCharts = false;
        
        const today = new Date();
        const formatDate = (date) => {
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            return `${year}-${month}-${day}`;
        };
        
        this.state = useState({
            loading: true,
            wings: [],
            wing_id: 'all',
            use_all_dates: false,
            date_from: formatDate(today),
            date_to: formatDate(today),
            data: {
                performance: {
                    prospect: { plan: 0, actual: 0, achievement: 0 },
                    reservation: { plan: 0, actual: 0, achievement: 0 },
                    cancellation: { plan: 0, actual: 0, achievement: 0 },
                    sales_qty: { plan: 0, actual: 0, achievement: 0 },
                    sales_value: { plan: 0, actual: 0, achievement: 0 },
                    advance_paid: { plan: 0, actual: 0, achievement: 0 },
                    conversion_rate: { plan: 0, actual: 0, achievement: 0 },
                    iar: { plan: 0, actual: 0, achievement: 0 },
                },
                opening_stock: {
                    residence: { qty: 0, value: 0 },
                    shops: { qty: 0, value: 0 },
                    mixed_use: { qty: 0, value: 0 },
                    total: { qty: 0, value: 0 },
                },
                timeseries: {
                    labels: [],
                    prospects: [],
                    reservations: [],
                    cancellations: [],
                    sales_qty: [],
                    sales_value: [],
                    advance_paid: []
                }
            },
            wingComparisonData: [], // Store data for all wings for comparison
        });
        
        onWillStart(async () => {
            await loadBundle("web.chartjs_lib");
            await this.loadData();
        });
        
        onPatched(() => {
            if (!this.state.loading && this.state.data &&
                !this._chartsRendered && !this._isRenderingCharts) {
                // Use setTimeout to ensure DOM is fully updated
                setTimeout(() => {
                    this.renderCharts();
                }, 50);
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

    onDateChange() {
        this.loadData();
    }

    onAllDatesChange() {
        this.loadData();
    }
    
    onWingChange() {
        this.loadData();
    }
    
    async loadData() {
        this._chartsRendered = false;
        this._isRenderingCharts = false;
        this.state.loading = true;
        const { date_from, date_to } = this._getEffectiveDates();
        try {
            const params = {
                period_type: 'custom',
                date_from,
                date_to,
                wing_id: this.state.wing_id,
            };
            const [result, timeseriesResult] = await Promise.all([
                this.rpc("/manager_reports/api/sales_performance_data", params),
                this.rpc("/manager_reports/api/sales_performance_timeseries", {
                    date_from,
                    date_to,
                    wing_id: this.state.wing_id
                })
            ]);
            
            console.log('API Response success:', result?.success);
            console.log('API Response data keys:', result?.data ? Object.keys(result.data) : 'No data');
            
            if (result && result.success) {
                this.state.data = result.data;
                // Ensure opening_stock and nested keys always have qty/value to avoid "Cannot read properties of undefined (reading 'qty')"
                const safeEntry = (e) => (e && typeof e.qty === 'number' && typeof e.value === 'number' ? e : { qty: 0, value: 0 });
                if (!this.state.data.opening_stock || typeof this.state.data.opening_stock !== 'object') {
                    this.state.data.opening_stock = {
                        residence: { qty: 0, value: 0 },
                        shops: { qty: 0, value: 0 },
                        mixed_use: { qty: 0, value: 0 },
                        total: { qty: 0, value: 0 },
                    };
                } else {
                    const os = this.state.data.opening_stock;
                    os.residence = safeEntry(os.residence);
                    os.shops = safeEntry(os.shops);
                    os.mixed_use = safeEntry(os.mixed_use);
                    os.total = safeEntry(os.total);
                }
                // Ensure performance and all metric keys exist to avoid undefined access in template
                const defPerf = (p, k) => (p[k] = p[k] && typeof p[k].plan !== 'undefined' ? p[k] : { plan: 0, actual: 0, achievement: 0 });
                if (this.state.data.performance) {
                    const p = this.state.data.performance;
                    ['prospect', 'reservation', 'cancellation', 'sales_qty', 'sales_value', 'advance_paid', 'conversion_rate', 'iar'].forEach(k => defPerf(p, k));
                } else {
                    this.state.data.performance = {
                        prospect: { plan: 0, actual: 0, achievement: 0 },
                        reservation: { plan: 0, actual: 0, achievement: 0 },
                        cancellation: { plan: 0, actual: 0, achievement: 0 },
                        sales_qty: { plan: 0, actual: 0, achievement: 0 },
                        sales_value: { plan: 0, actual: 0, achievement: 0 },
                        advance_paid: { plan: 0, actual: 0, achievement: 0 },
                        conversion_rate: { plan: 0, actual: 0, achievement: 0 },
                        iar: { plan: 0, actual: 0, achievement: 0 },
                    };
                }
                if (timeseriesResult && timeseriesResult.success && timeseriesResult.data) {
                    this.state.data.timeseries = timeseriesResult.data;
                } else {
                    this.state.data.timeseries = {
                        labels: [],
                        prospects: [],
                        reservations: [],
                        cancellations: [],
                        sales_qty: [],
                        sales_value: [],
                        advance_paid: []
                    };
                }
                if (result.wings) {
                    this.state.wings = result.wings;
                }
                if (result.date_from) this.state.date_from = result.date_from;
                if (result.date_to) this.state.date_to = result.date_to;
                
                // Debug: Log the performance data received
                if (result.data && result.data.performance) {
                    console.log('=== PERFORMANCE DATA RECEIVED ===');
                    console.log('Full performance object:', JSON.stringify(result.data.performance, null, 2));
                    console.log('Prospect:', result.data.performance.prospect);
                    console.log('Prospect actual:', result.data.performance.prospect?.actual, 'Type:', typeof result.data.performance.prospect?.actual);
                    console.log('Sales QTY:', result.data.performance.sales_qty);
                    console.log('Sales QTY actual:', result.data.performance.sales_qty?.actual, 'Type:', typeof result.data.performance.sales_qty?.actual);
                    console.log('Sales Value:', result.data.performance.sales_value);
                    console.log('Sales Value actual:', result.data.performance.sales_value?.actual, 'Type:', typeof result.data.performance.sales_value?.actual);
                } else {
                    console.warn('No performance data in response!');
                    console.log('Result.data:', result.data);
                }
                
                // Load wing data: when All = all wings; when specific wing = that wing only
                if (this.state.wing_id === 'all' && result.wings && result.wings.length > 0) {
                    await this.loadWingComparisonData();
                } else if (this.state.wing_id && this.state.wing_id !== 'all' && result.data && result.data.performance) {
                    const wing = (result.wings || []).find(w => String(w.id) === String(this.state.wing_id));
                    const perf = result.data.performance;
                    const ach = (actual, plan) => (plan > 0 ? Math.round((actual / plan) * 1000) / 10 : 0);
                    this.state.wingComparisonData = [{
                        wing_name: wing ? (wing.name || `Wing ${this.state.wing_id}`) : `Wing ${this.state.wing_id}`,
                        wing_id: this.state.wing_id,
                        prospect: Number(perf.prospect?.actual || 0),
                        reservation: Number(perf.reservation?.actual || 0),
                        sales_qty: Number(perf.sales_qty?.actual || 0),
                        sales_value: Number((perf.sales_value?.actual || 0) / 1000000),
                        advance_paid: Number((perf.advance_paid?.actual || 0) / 1000000),
                        conversion_rate: Number(perf.conversion_rate?.actual || 0),
                        iar: Number(perf.iar?.actual || 0),
                        prospect_plan: Number(perf.prospect?.plan || 0),
                        reservation_plan: Number(perf.reservation?.plan || 0),
                        sales_qty_plan: Number(perf.sales_qty?.plan || 0),
                        sales_value_plan: Number((perf.sales_value?.plan || 0) / 1000000),
                        advance_paid_plan: Number((perf.advance_paid?.plan || 0) / 1000000),
                        conversion_rate_plan: Number(perf.conversion_rate?.plan || 0),
                        iar_plan: Number(perf.iar?.plan || 0),
                        prospect_ach: ach(perf.prospect?.actual || 0, perf.prospect?.plan || 0),
                        reservation_ach: ach(perf.reservation?.actual || 0, perf.reservation?.plan || 0),
                        sales_qty_ach: ach(perf.sales_qty?.actual || 0, perf.sales_qty?.plan || 0),
                        sales_value_ach: ach(perf.sales_value?.actual || 0, perf.sales_value?.plan || 0),
                        advance_paid_ach: ach(perf.advance_paid?.actual || 0, perf.advance_paid?.plan || 0),
                        conversion_rate_ach: ach(perf.conversion_rate?.actual || 0, perf.conversion_rate?.plan || 0),
                        iar_ach: ach(perf.iar?.actual || 0, perf.iar?.plan || 0),
                    }];
                } else {
                    this.state.wingComparisonData = [];
                }
                
                // Force chart re-render after data is loaded
                // Use setTimeout to ensure DOM is updated
                setTimeout(() => {
                    this.renderCharts();
                }, 100);
            } else {
                this.notification.add(
                    result.error || "Error loading report data",
                    { type: "danger" }
                );
            }
        } catch (error) {
            console.error("Error loading sales performance report:", error);
            this.notification.add("Error loading report data", { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }
    
    async loadWingComparisonData() {
        // Load data for each wing to compare
        const wingData = [];
        if (!this.state.wings || this.state.wings.length === 0) {
            this.state.wingComparisonData = [];
            console.log('No wings available for comparison');
            return;
        }
        
        console.log(`Loading wing comparison data for ${this.state.wings.length} wings`);
        
        for (const wing of this.state.wings) {
            try {
                const params = {
                    period_type: 'custom',
                    date_from: this.state.date_from,
                    date_to: this.state.date_to,
                    wing_id: wing.id,
                };
                const result = await this.rpc("/manager_reports/api/sales_performance_data", params);
                if (result && result.success && result.data && result.data.performance) {
                    const perf = result.data.performance;
                    const ach = (actual, plan) => (plan > 0 ? Math.round((actual / plan) * 1000) / 10 : 0);
                    const wingInfo = {
                        wing_name: wing.name || `Wing ${wing.id}`,
                        wing_id: wing.id,
                        prospect: Number(perf.prospect?.actual || 0),
                        reservation: Number(perf.reservation?.actual || 0),
                        sales_qty: Number(perf.sales_qty?.actual || 0),
                        sales_value: Number((perf.sales_value?.actual || 0) / 1000000),
                        advance_paid: Number(perf.advance_paid?.actual || 0) / 1000000,
                        conversion_rate: Number(perf.conversion_rate?.actual || 0),
                        iar: Number(perf.iar?.actual || 0),
                        prospect_plan: Number(perf.prospect?.plan || 0),
                        reservation_plan: Number(perf.reservation?.plan || 0),
                        sales_qty_plan: Number(perf.sales_qty?.plan || 0),
                        sales_value_plan: Number((perf.sales_value?.plan || 0) / 1000000),
                        advance_paid_plan: Number((perf.advance_paid?.plan || 0) / 1000000),
                        conversion_rate_plan: Number(perf.conversion_rate?.plan || 0),
                        iar_plan: Number(perf.iar?.plan || 0),
                        prospect_ach: ach(perf.prospect?.actual || 0, perf.prospect?.plan || 0),
                        reservation_ach: ach(perf.reservation?.actual || 0, perf.reservation?.plan || 0),
                        sales_qty_ach: ach(perf.sales_qty?.actual || 0, perf.sales_qty?.plan || 0),
                        sales_value_ach: ach(perf.sales_value?.actual || 0, perf.sales_value?.plan || 0),
                        advance_paid_ach: ach(perf.advance_paid?.actual || 0, perf.advance_paid?.plan || 0),
                        conversion_rate_ach: ach(perf.conversion_rate?.actual || 0, perf.conversion_rate?.plan || 0),
                        iar_ach: ach(perf.iar?.actual || 0, perf.iar?.plan || 0),
                    };
                    wingData.push(wingInfo);
                    console.log(`Loaded data for ${wingInfo.wing_name}:`, wingInfo);
                } else {
                    console.warn(`No data returned for wing ${wing.name || wing.id}:`, result);
                }
            } catch (error) {
                console.error(`Error loading data for wing ${wing.name || wing.id}:`, error);
            }
        }
        
        this.state.wingComparisonData = wingData;
        console.log('Final wing comparison data:', wingData);
        
        // Trigger chart re-render after data is loaded
        if (this.state.wing_id === 'all') {
            this.renderCharts();
        }
    }
    
    renderCharts() {
        const Chart = window.Chart;
        if (!Chart) {
            console.warn('Chart.js not loaded yet');
            return;
        }
        
        if (!this.state.data) {
            return;
        }
        
        // Destroy existing charts
        if (this._openingStockPieChart) {
            this._openingStockPieChart.destroy();
            this._openingStockPieChart = null;
        }
        Object.values(this._wingCharts || {}).forEach(chart => { if (chart) chart.destroy(); });
        this._wingCharts = {};
        if (this._wingComparisonTimelineChart) { this._wingComparisonTimelineChart.destroy(); this._wingComparisonTimelineChart = null; }
        if (this._activityTimeseriesChart) { this._activityTimeseriesChart.destroy(); this._activityTimeseriesChart = null; }
        
        const baseOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom', labels: { padding: 12, font: { size: 11 } } },
                tooltip: { enabled: true }
            }
        };
        
        // 1. Opening Stock Pie Chart (same as previous)
        if (this.openingStockPieChartRef.el) {
            const stock = this.state.data.opening_stock || {};
            const stockLabels = [];
            const stockValues = [];
            const stockColors = [];
            
            if (stock.residence && stock.residence.qty > 0) {
                stockLabels.push('Residence');
                stockValues.push(stock.residence.qty);
                stockColors.push('#2563eb');
            }
            if (stock.shops && stock.shops.qty > 0) {
                stockLabels.push('Shops');
                stockValues.push(stock.shops.qty);
                stockColors.push('#059669');
            }
            if (stock.mixed_use && stock.mixed_use.qty > 0) {
                stockLabels.push('Mixed use');
                stockValues.push(stock.mixed_use.qty);
                stockColors.push('#7c3aed');
            }
            
            if (stockLabels.length > 0) {
                this._openingStockPieChart = new Chart(this.openingStockPieChartRef.el, {
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
                        ...baseOptions,
                        animation: {
                            duration: 0  // Disable animation to prevent shaking
                        }
                    },
                });
            }
        }
        
        // 2. Per-wing charts (QTY + Money bar charts for each wing)
        const wings = this.state.wingComparisonData || [];
        const container = (this.reportContentRef && this.reportContentRef.el) || document.querySelector('.report_content');
        if (container && wings.length > 0) {
            wings.forEach((wing) => {
                const wid = String(wing.wing_id);
                const qtyCanvas = container.querySelector('#wing-qty-' + wid);
                const moneyCanvas = container.querySelector('#wing-money-' + wid);
                if (qtyCanvas) {
                    const n = (v) => Number(v) || 0;
                    const chart = new Chart(qtyCanvas, {
                        type: "bar",
                        data: {
                            labels: ['Prospects', 'Reservations', 'Sales QTY'],
                            datasets: [
                                { label: "Plan", data: [n(wing.prospect_plan), n(wing.reservation_plan), n(wing.sales_qty_plan)], backgroundColor: '#2e7d32', borderRadius: 8 },
                                { label: "Actual", data: [n(wing.prospect), n(wing.reservation), n(wing.sales_qty)], backgroundColor: '#2563eb', borderRadius: 8 },
                            ],
                        },
                        options: { ...baseOptions, animation: { duration: 0 }, scales: { y: { beginAtZero: true } }, plugins: { ...baseOptions.plugins } },
                    });
                    this._wingCharts['qty-' + wid] = chart;
                }
                if (moneyCanvas) {
                    const chart = new Chart(moneyCanvas, {
                        type: "bar",
                        data: {
                            labels: ['Sales Value', 'Advance Paid'],
                            datasets: [
                                { label: "Plan", data: [Number(wing.sales_value_plan)||0, Number(wing.advance_paid_plan)||0], backgroundColor: '#2e7d32', borderRadius: 8 },
                                { label: "Actual", data: [Number(wing.sales_value)||0, Number(wing.advance_paid)||0], backgroundColor: '#2563eb', borderRadius: 8 },
                            ],
                        },
                        options: {
                            ...baseOptions,
                            animation: { duration: 0 },
                            scales: { y: { beginAtZero: true } },
                            plugins: { ...baseOptions.plugins },
                        },
                    });
                    this._wingCharts['money-' + wid] = chart;
                }
            });
        }
        
        // Wing Comparison Timeline (when Wing = All)
        if (this.wingComparisonTimelineChartRef && this.wingComparisonTimelineChartRef.el) {
            // Only recreate if chart doesn't exist or was destroyed
            if (this._wingComparisonTimelineChart) {
                // Check if chart is still valid before destroying
                try {
                    if (this._wingComparisonTimelineChart.canvas && this._wingComparisonTimelineChart.canvas.parentNode) {
                        // Chart exists and is valid, just update data instead of recreating
                        // Skip recreation to prevent infinite loop
                        return;
                    }
                } catch (e) {
                    // Chart is invalid, destroy it
                }
                this._wingComparisonTimelineChart.destroy();
                this._wingComparisonTimelineChart = null;
            }
            
            // Limit to top 6 wings to keep it simple and clear
            const wingsToShow = (this.state.wings || []).slice(0, 6);
            
            if (wingsToShow.length === 0) {
                return; // No wings to show
            }
            
            // Generate labels from date range first
            const wingTimelineLabels = [];
            if (this.state.date_from && this.state.date_to) {
                const dateFrom = new Date(this.state.date_from);
                const dateTo = new Date(this.state.date_to);
                const daysDiff = Math.ceil((dateTo - dateFrom) / (1000 * 60 * 60 * 24)) + 1;
                if (daysDiff <= 31) {
                    // Daily
                    for (let d = new Date(dateFrom); d <= dateTo; d.setDate(d.getDate() + 1)) {
                        wingTimelineLabels.push(d.toISOString().split('T')[0]);
                    }
                } else if (daysDiff <= 365) {
                    // Weekly
                    for (let d = new Date(dateFrom); d <= dateTo; d.setDate(d.getDate() + 7)) {
                        let weekEnd = new Date(d);
                        weekEnd.setDate(weekEnd.getDate() + 6);
                        if (weekEnd > dateTo) weekEnd = dateTo;
                        wingTimelineLabels.push(`${d.toISOString().split('T')[0]} to ${weekEnd.toISOString().split('T')[0]}`);
                    }
                } else {
                    // Monthly
                    const current = new Date(dateFrom.getFullYear(), dateFrom.getMonth(), 1);
                    while (current <= dateTo) {
                        wingTimelineLabels.push(`${current.getFullYear()}-${String(current.getMonth() + 1).padStart(2, '0')}`);
                        current.setMonth(current.getMonth() + 1);
                    }
                }
            }
            
            // Simple color palette - limit to 6 colors
            const wingTimelineColors = [
                '#2563eb', '#059669', '#f59e0b', '#dc2626', '#8b5cf6', '#ec4899'
            ];
            
            // Create chart with empty data first
            try {
                this._wingComparisonTimelineChart = new Chart(this.wingComparisonTimelineChartRef.el, {
                    type: "line",
                    data: {
                        labels: wingTimelineLabels,
                        datasets: wingsToShow.map((wing, idx) => ({
                            label: wing.name || `Wing ${wing.id}`,
                            data: wingTimelineLabels.map(() => 0),
                            borderColor: wingTimelineColors[idx % wingTimelineColors.length],
                            backgroundColor: 'transparent',
                            fill: false,
                            tension: 0.3,
                            pointRadius: 2,
                            pointHoverRadius: 4,
                            borderWidth: 2,
                        })),
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        animation: {
                            duration: 0  // Disable animation to prevent shaking
                        },
                        interaction: {
                            intersect: false,
                            mode: 'index',
                        },
                        scales: {
                            y: {
                                beginAtZero: true,
                                ticks: {
                                    precision: 0,
                                },
                            },
                            x: {
                                ticks: {
                                    maxRotation: 45,
                                    minRotation: 45,
                                    maxTicksLimit: 12,
                                },
                            },
                        },
                        plugins: {
                            legend: {
                                display: true,
                                position: 'bottom',
                            },
                            title: {
                                display: true,
                                text: "Wing Comparison Timeline - Sales QTY",
                                font: { size: 14, weight: "bold" },
                            },
                            tooltip: {
                                enabled: true,
                            },
                        },
                    },
                });
                
                // Fetch data for all wings with timeout and error handling
                const fetchWingData = async () => {
                    try {
                        const wingDataPromises = wingsToShow.map(async (wing) => {
                            try {
                                // Add timeout to prevent hanging
                                const timeoutPromise = new Promise((_, reject) => 
                                    setTimeout(() => reject(new Error('Timeout')), 10000)
                                );
                                
                                const dataPromise = this.rpc("/manager_reports/api/sales_performance_timeseries", {
                                    date_from: this.state.date_from,
                                    date_to: this.state.date_to,
                                    wing_id: wing.id
                                });
                                
                                const result = await Promise.race([dataPromise, timeoutPromise]);
                                
                                if (result && result.success && result.data && result.data.sales_qty) {
                                    return {
                                        wing_name: wing.name || `Wing ${wing.id}`,
                                        sales_qty: result.data.sales_qty || []
                                    };
                                }
                            } catch (error) {
                                console.warn(`Skipping wing ${wing.name || wing.id} due to error:`, error);
                            }
                            return null;
                        });
                        
                        const wingDataResults = await Promise.all(wingDataPromises);
                        const validWings = wingDataResults.filter(w => w !== null && w.sales_qty && w.sales_qty.length > 0);
                        
                        // Only update if chart still exists and component hasn't been destroyed
                        if (validWings.length > 0 && this._wingComparisonTimelineChart && 
                            this.wingComparisonTimelineChartRef && this.wingComparisonTimelineChartRef.el) {
                            try {
                                // Use labels from first valid wing or generated labels
                                const firstWingLabels = validWings[0].sales_qty.length === wingTimelineLabels.length 
                                    ? wingTimelineLabels 
                                    : wingTimelineLabels;
                                
                                const datasets = validWings.map((wing, idx) => {
                                    const wingIndex = wingsToShow.findIndex(w => w.name === wing.wing_name || w.id === wing.wing_name);
                                    const colorIndex = wingIndex >= 0 ? wingIndex : idx;
                                    
                                    // Ensure data length matches labels
                                    let salesData = wing.sales_qty || [];
                                    if (salesData.length !== firstWingLabels.length) {
                                        salesData = firstWingLabels.map(() => 0);
                                    }
                                    
                                    return {
                                        label: wing.wing_name,
                                        data: salesData,
                                        borderColor: wingTimelineColors[colorIndex % wingTimelineColors.length],
                                        backgroundColor: 'transparent',
                                        fill: false,
                                        tension: 0.3,
                                        pointRadius: 2,
                                        pointHoverRadius: 4,
                                        borderWidth: 2,
                                    };
                                });
                                
                                // Update chart only if it still exists and is valid
                                if (this._wingComparisonTimelineChart && this._wingComparisonTimelineChart.canvas) {
                                    this._wingComparisonTimelineChart.data.labels = firstWingLabels;
                                    this._wingComparisonTimelineChart.data.datasets = datasets;
                                    this._wingComparisonTimelineChart.update('none');
                                }
                            } catch (e) {
                                console.warn("Error updating wing comparison timeline:", e);
                            }
                        } else if (this._wingComparisonTimelineChart && 
                                   this.wingComparisonTimelineChartRef && this.wingComparisonTimelineChartRef.el) {
                            try {
                                // If no valid data, show empty chart with zero data
                                if (this._wingComparisonTimelineChart.canvas) {
                                    this._wingComparisonTimelineChart.data.datasets = wingsToShow.map((wing, idx) => ({
                                        label: wing.name || `Wing ${wing.id}`,
                                        data: wingTimelineLabels.map(() => 0),
                                        borderColor: wingTimelineColors[idx % wingTimelineColors.length],
                                        backgroundColor: 'transparent',
                                        fill: false,
                                        tension: 0.3,
                                        pointRadius: 2,
                                        borderWidth: 2,
                                    }));
                                    this._wingComparisonTimelineChart.update('none');
                                }
                            } catch (e) {
                                console.warn("Error updating empty wing comparison timeline:", e);
                            }
                        }
                    } catch (error) {
                        console.error("Error loading wing timeline data:", error);
                    }
                };
                
                // Delay data fetching slightly to ensure chart is rendered first
                setTimeout(() => {
                    fetchWingData();
                }, 100);
                
            } catch (e) {
                console.error("Error creating wing comparison timeline chart:", e);
            }
        }
        
        // Activity Timeline
        if (this.activityTimeseriesChartRef && this.activityTimeseriesChartRef.el) {
            const ts = this.state.data.timeseries || {
                labels: [],
                prospects: [],
                reservations: [],
                cancellations: [],
                sales_qty: [],
                sales_value: [],
                advance_paid: []
            };
            
            if (this._activityTimeseriesChart) {
                this._activityTimeseriesChart.destroy();
            }
            try {
                // Generate labels if empty (for date range)
                let labels = ts.labels || [];
                if (labels.length === 0 && this.state.date_from && this.state.date_to) {
                    const dateFrom = new Date(this.state.date_from);
                    const dateTo = new Date(this.state.date_to);
                    const daysDiff = Math.ceil((dateTo - dateFrom) / (1000 * 60 * 60 * 24)) + 1;
                    if (daysDiff <= 31) {
                        // Daily
                        for (let d = new Date(dateFrom); d <= dateTo; d.setDate(d.getDate() + 1)) {
                            labels.push(d.toISOString().split('T')[0]);
                        }
                    } else if (daysDiff <= 365) {
                        // Weekly
                        for (let d = new Date(dateFrom); d <= dateTo; d.setDate(d.getDate() + 7)) {
                            const weekEnd = new Date(d);
                            weekEnd.setDate(weekEnd.getDate() + 6);
                            if (weekEnd > dateTo) weekEnd = dateTo;
                            labels.push(`${d.toISOString().split('T')[0]} to ${weekEnd.toISOString().split('T')[0]}`);
                        }
                    } else {
                        // Monthly
                        const current = new Date(dateFrom.getFullYear(), dateFrom.getMonth(), 1);
                        while (current <= dateTo) {
                            labels.push(`${current.getFullYear()}-${String(current.getMonth() + 1).padStart(2, '0')}`);
                            current.setMonth(current.getMonth() + 1);
                        }
                    }
                }
                
                console.log("Creating sales timeline chart with data:", {
                    labels: labels,
                    prospects: ts.prospects || [],
                    reservations: ts.reservations || [],
                    sales_qty: ts.sales_qty || []
                });
                
                this._activityTimeseriesChart = new Chart(this.activityTimeseriesChartRef.el, {
                    type: "line",
                    data: {
                        labels: labels,
                        datasets: [
                            {
                                label: "Prospects",
                                data: ts.prospects || labels.map(() => 0),
                                borderColor: "#2563eb",
                                backgroundColor: "rgba(37, 99, 235, 0.1)",
                                fill: false,
                                tension: 0.4,
                                borderWidth: 3,
                                pointRadius: 4,
                                pointHoverRadius: 6,
                            },
                            {
                                label: "Reservations",
                                data: ts.reservations || labels.map(() => 0),
                                borderColor: "#059669",
                                backgroundColor: "rgba(5, 150, 105, 0.1)",
                                fill: false,
                                tension: 0.4,
                                borderWidth: 3,
                                pointRadius: 4,
                                pointHoverRadius: 6,
                            },
                            {
                                label: "Cancellations",
                                data: ts.cancellations || labels.map(() => 0),
                                borderColor: "#dc2626",
                                backgroundColor: "rgba(220, 38, 38, 0.1)",
                                fill: false,
                                tension: 0.4,
                                borderWidth: 3,
                                pointRadius: 4,
                                pointHoverRadius: 6,
                            },
                            {
                                label: "Sales QTY",
                                data: ts.sales_qty || labels.map(() => 0),
                                borderColor: "#f59e0b",
                                backgroundColor: "rgba(245, 158, 11, 0.1)",
                                fill: false,
                                tension: 0.4,
                                borderWidth: 3,
                                pointRadius: 4,
                                pointHoverRadius: 6,
                            }
                        ],
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        animation: {
                            duration: 0  // Disable animation to prevent shaking
                        },
                        interaction: {
                            intersect: false,
                            mode: 'index',
                        },
                        scales: {
                            y: {
                                beginAtZero: true,
                                ticks: {
                                    font: { size: 12 },
                                    precision: 0,
                                },
                                title: {
                                    display: true,
                                    font: { size: 13, weight: "bold" },
                                },
                            },
                            x: {
                                ticks: {
                                    maxRotation: 45,
                                    minRotation: 45,
                                    font: { size: 11 },
                                    maxTicksLimit: 15,
                                },
                                title: {
                                    display: true,
                                    font: { size: 13, weight: "bold" },
                                },
                            },
                        },
                        plugins: {
                            legend: {
                                display: true,
                                position: 'bottom',
                                labels: {
                                    padding: 15,
                                    font: { size: 12 },
                                    usePointStyle: true,
                                },
                            },
                            tooltip: {
                                enabled: true,
                                titleFont: { size: 13 },
                                bodyFont: { size: 12 },
                            },
                            title: {
                                display: true,
                                text: "Activity Timeline",
                                font: { size: 16, weight: "bold" },
                                padding: { top: 10, bottom: 20 },
                            },
                        },
                    },
                });
                
                // Force chart resize to ensure proper rendering
                setTimeout(() => {
                    if (this._activityTimeseriesChart) {
                        this._activityTimeseriesChart.resize();
                    }
                }, 100);
                
                console.log("Sales timeline chart created successfully");
            } catch (e) {
                console.error("Error creating activity timeseries chart:", e);
            }
        } else {
            console.warn("Sales timeline chart not rendered - missing data or ref");
        }
        
        // Mark charts as rendered and reset rendering flag
        this._chartsRendered = true;
        this._isRenderingCharts = false;
    }
    
    _getChartImages() {
        const safeImg = (chart, chartName) => {
            try {
                if (!chart) {
                    console.warn(`Chart instance is null for ${chartName}`);
                    return "";
                }
                
                // Check if canvas element exists and has dimensions
                const canvas = chart.canvas;
                if (!canvas) {
                    console.warn(`Canvas element not found for ${chartName}`);
                    return "";
                }
                
                // Ensure canvas is visible and has dimensions
                if (canvas.offsetWidth === 0 || canvas.offsetHeight === 0) {
                    console.warn(`Canvas has no dimensions for ${chartName}: ${canvas.offsetWidth}x${canvas.offsetHeight}`);
                    return "";
                }
                
                // Update chart to ensure it's fully rendered
                chart.update('none'); // Update without animation
                
                const img = chart.toBase64Image();
                if (!img || img.length < 100) {
                    console.warn(`Chart image is too small or empty for ${chartName}: ${img ? img.length : 0} bytes`);
                    return "";
                }
                
                console.log(`Successfully captured ${chartName}: ${img.length} bytes`);
                return img;
            } catch (e) {
                console.error(`Error capturing chart image for ${chartName}:`, e);
                return "";
            }
        };
        const images = {
            opening_stock_pie_chart: safeImg(this._openingStockPieChart, "opening_stock"),
            wing_comparison_timeline: safeImg(this._wingComparisonTimelineChart, "wing_comparison_timeline"),
            activity_timeline: safeImg(this._activityTimeseriesChart, "activity_timeline"),
        };
        Object.keys(this._wingCharts || {}).forEach(key => {
            images['wing_chart_' + key] = safeImg(this._wingCharts[key], 'wing_' + key);
        });
        console.log("Chart images captured:", Object.keys(images).map(k => `${k}: ${images[k] ? `Yes (${images[k].length} bytes)` : "No"}`));
        return images;
    }
    
    async exportExcel() {
        if (!this.state.data) {
            this.notification.add("Please load data first", { type: "warning" });
            return;
        }
        
        // Ensure charts are rendered
        this.renderCharts();
        
        // Wait a bit for charts to render, then capture
        await new Promise(resolve => setTimeout(resolve, 800));
        
        // Force chart update
        if (this._openingStockPieChart) this._openingStockPieChart.update('none');
        Object.values(this._wingCharts || {}).forEach(chart => { if (chart) chart.update('none'); });
        if (this._wingComparisonTimelineChart) this._wingComparisonTimelineChart.update('none');
        if (this._activityTimeseriesChart) this._activityTimeseriesChart.update('none');
        
        await new Promise(resolve => requestAnimationFrame(resolve));
        
        const images = this._getChartImages();
        console.log("Exporting Excel - Images captured:", Object.keys(images).map(k => `${k}: ${images[k] ? images[k].length : 0} bytes`));
        
        // Use JSON-RPC instead of form POST for better handling of large images
        try {
            const { date_from, date_to } = this._getEffectiveDates();
            const response = await this.rpc("/manager_reports/api/export_sales_performance_excel", {
                period_type: 'custom',
                date_from,
                date_to,
                wing_id: this.state.wing_id,
                chart_images: images
            });
            
            if (response && response.file_data) {
                // Download the file
                const link = document.createElement('a');
                link.href = 'data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,' + response.file_data;
                link.download = response.filename || 'Sales_Report.xlsx';
                link.click();
            } else {
                this.notification.add("Error generating Excel file", { type: "danger" });
            }
        } catch (error) {
            console.error("Error exporting Excel:", error);
            this.notification.add("Error exporting Excel: " + (error.message || "Unknown error"), { type: "danger" });
        }
    }
    
    async exportPDF() {
        if (!this.state.data) {
            this.notification.add("Please load data first", { type: "warning" });
            return;
        }
        
        // Ensure charts are rendered
        this.renderCharts();
        
        // Wait a bit for charts to render, then capture
        await new Promise(resolve => setTimeout(resolve, 800));
        
        // Force chart update
        if (this._openingStockPieChart) this._openingStockPieChart.update('none');
        Object.values(this._wingCharts || {}).forEach(chart => { if (chart) chart.update('none'); });
        if (this._wingComparisonTimelineChart) this._wingComparisonTimelineChart.update('none');
        if (this._activityTimeseriesChart) this._activityTimeseriesChart.update('none');
        
        await new Promise(resolve => requestAnimationFrame(resolve));
        
        const images = this._getChartImages();
        console.log("Exporting PDF - Images captured:", Object.keys(images).map(k => `${k}: ${images[k] ? images[k].length : 0} bytes`));
        
        // Use JSON-RPC instead of form POST for better handling of large images
        try {
            const { date_from, date_to } = this._getEffectiveDates();
            const response = await this.rpc("/manager_reports/api/export_sales_performance_pdf", {
                period_type: 'custom',
                date_from,
                date_to,
                wing_id: this.state.wing_id,
                chart_images: images
            });
            
            if (response && response.html_content) {
                // Open PDF in new window
                const newWindow = window.open('', '_blank');
                newWindow.document.write(response.html_content);
                newWindow.document.close();
            } else {
                this.notification.add("Error generating PDF file", { type: "danger" });
            }
        } catch (error) {
            console.error("Error exporting PDF:", error);
            this.notification.add("Error exporting PDF: " + (error.message || "Unknown error"), { type: "danger" });
        }
    }
    
    _postDownload(url, payload) {
        const form = document.createElement("form");
        form.method = "POST";
        form.action = url;
        form.style.display = "none";
        Object.entries(payload).forEach(([k, v]) => {
            const input = document.createElement("input");
            input.type = "hidden";
            input.name = k;
            input.value = v === undefined || v === null ? "" : String(v);
        });
        document.body.appendChild(form);
        form.submit();
        document.body.removeChild(form);
    }
    
    formatNumber(num) {
        if (num === null || num === undefined) return '0';
        return Number(num).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
    }

    formatCurrency(amount) {
        if (amount === null || amount === undefined) return '0.00';
        return Number(amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    getOpeningStockQty(section) {
        const os = this.state.data && this.state.data.opening_stock;
        const entry = os && os[section];
        return entry && typeof entry.qty !== 'undefined' ? entry.qty : 0;
    }

    getOpeningStockValue(section) {
        const os = this.state.data && this.state.data.opening_stock;
        const entry = os && os[section];
        return entry && typeof entry.value !== 'undefined' ? entry.value : 0;
    }

    t(key) {
        return _t(key);
    }
}

SalesPerformanceReportClient.template = "manager_reports.SalesPerformanceReportClient";

registry.category("actions").add("manager_reports.sales_performance", SalesPerformanceReportClient);
