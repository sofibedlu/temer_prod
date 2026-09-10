/** @odoo-module **/

import { Component, useState, onWillStart, onPatched, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadBundle } from "@web/core/assets";
import { _t } from "@web/core/l10n/translation";

export class CollectionReportClient extends Component {
    setup() {
        this.notification = useService("notification");
        this.rpc = useService("rpc");
        
        // Chart refs
        this.collectionAmountChartRef = useRef("collectionAmountChart");
        this.collectionClientsChartRef = useRef("collectionClientsChart");
        this.stockDistributionChartRef = useRef("stockDistributionChart");
        this.activityTimeseriesChartRef = useRef("activityTimeseriesChart");
        
        // Chart instances
        this._collectionAmountChart = null;
        this._collectionClientsChart = null;
        this._stockDistributionChart = null;
        this._activityTimeseriesChart = null;
        
        // Guards to prevent re-render loop (same as Sales Report)
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
            use_all_dates: false,
            date_from: formatDate(today),
            date_to: formatDate(today),
            data: {
                total_clients: 0,
                total_sites: 0,
                stock_under_collection: {
                    residences: 0,
                    shops: 0,
                    mixed_use: 0
                },
                total_receivable: 0.0,
                collection_performance: {
                    collected_amount: { plan: 0.0, actual: 0.0, achievement: 0.0 },
                    collected_from_clients: { plan: 0, actual: 0, achievement: 0.0 }
                },
                discount_given: {
                    amount: 0.0,
                    percentage: 0.0
                },
                qty: 0,
                properties_returned: 0,
                timeseries: {
                    labels: [],
                    collected_amount: [],
                    collected_clients: [],
                    discount_amount: []
                }
            }
        });
        
        onWillStart(async () => {
            await loadBundle("web.chartjs_lib");
            await this.loadData();
        });
        
        onPatched(() => {
            if (!this.state.loading && this.state.data && !this._chartsRendered && !this._isRenderingCharts) {
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
    
    async loadData() {
        this._chartsRendered = false;
        this._isRenderingCharts = false;
        this.state.loading = true;
        const { date_from, date_to } = this._getEffectiveDates();
        try {
            const [result, timeseriesResult] = await Promise.all([
                this.rpc("/collection_reports/api/collection_plan", {
                    period_type: 'custom',
                    date_from,
                    date_to
                }),
                this.rpc("/manager_reports/api/collection_timeseries", {
                    date_from,
                    date_to
                })
            ]);
            
            if (result && result.success && result.data) {
                const data = result.data;
                this.state.data = {
                    total_clients: data.total_clients || 0,
                    total_sites: data.no_of_sites || 0,  // Map no_of_sites to total_sites
                    stock_under_collection: {
                        residences: data.stock_residences || 0,
                        shops: data.stock_shops || 0,
                        mixed_use: data.stock_mixed_use || 0
                    },
                    total_receivable: data.total_receivable || 0.0,
                    collection_performance: {
                        collected_amount: {
                            plan: data.collected_amount_plan || 0.0,
                            actual: data.collected_amount_actual || 0.0,
                            achievement: data.collected_amount_achievement || 0.0
                        },
                        collected_from_clients: {
                            plan: data.collected_clients_plan || 0,
                            actual: data.collected_clients_actual || 0,
                            achievement: data.collected_clients_achievement || 0.0
                        }
                    },
                    discount_given: {
                        amount: data.discount_amount || 0.0,
                        percentage: data.discount_percentage || 0.0
                    },
                    qty: (data.stock_residences || 0) + (data.stock_shops || 0) + (data.stock_mixed_use || 0),  // Total QTY
                    properties_returned: 0,  // This field may need to be calculated separately if available
                    timeseries: timeseriesResult && timeseriesResult.success && timeseriesResult.data 
                        ? timeseriesResult.data 
                        : { labels: [], collected_amount: [], collected_clients: [], discount_amount: [] }
                };
                
                // Wait a bit longer for DOM to be ready, then render charts
                setTimeout(() => {
                    this.renderCharts();
                }, 200);
            } else {
                this.notification.add(result?.error || "Error loading data", { type: "danger" });
            }
        } catch (error) {
            console.error("Error loading data:", error);
            this.notification.add("Error loading report data", { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }
    
    renderCharts() {
        if (!window.Chart) {
            console.warn("Chart.js not loaded yet");
            return;
        }
        if (!this.state.data) {
            console.warn("No data available for charts");
            return;
        }
        this._isRenderingCharts = true;
        console.log("Rendering charts with data:", this.state.data);
        
        const baseOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'bottom',
                    labels: {
                        font: { size: 12, family: 'Arial' },
                        padding: 10,
                        usePointStyle: true
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    padding: 10,
                    titleFont: { size: 14 },
                    bodyFont: { size: 12 },
                    cornerRadius: 6
                }
            }
        };
        
        // 1. Stock Distribution Pie Chart
        if (this.stockDistributionChartRef && this.stockDistributionChartRef.el) {
            const residences = this.state.data.stock_under_collection?.residences || 0;
            const shops = this.state.data.stock_under_collection?.shops || 0;
            const mixedUse = this.state.data.stock_under_collection?.mixed_use || 0;
            const labels = [];
            const data = [];
            const colors = [];
            if (residences > 0) { labels.push('Residences'); data.push(residences); colors.push('#2563eb'); }
            if (shops > 0) { labels.push('Shops'); data.push(shops); colors.push('#059669'); }
            if (mixedUse > 0) { labels.push('Mixed use'); data.push(mixedUse); colors.push('#7c3aed'); }
            
            if (labels.length === 0) { labels.push('Residences', 'Shops', 'Mixed use'); data.push(0, 0, 0); colors.push('#2563eb', '#059669', '#7c3aed'); }
            
            if (this._stockDistributionChart) {
                this._stockDistributionChart.destroy();
                this._stockDistributionChart = null;
            }
            
            try {
                this._stockDistributionChart = new Chart(this.stockDistributionChartRef.el, {
                    type: "doughnut",
                    data: {
                        labels: labels,
                        datasets: [{
                            data: data,
                            backgroundColor: colors,
                            borderWidth: 2,
                            borderColor: '#fff',
                            hoverOffset: 0
                        }]
                    },
                    options: {
                        ...baseOptions,
                        animation: { duration: 0 },
                        plugins: {
                            ...baseOptions.plugins,
                            title: {
                                display: true,
                                text: 'Stock Under Collection Distribution',
                                font: { size: 14, weight: 'bold' }
                            }
                        }
                    }
                });
                console.log("Stock distribution chart created successfully");
            } catch (e) {
                console.error("Error creating stock distribution chart:", e);
            }
        } else {
            console.warn("Stock distribution chart ref or element not available");
        }
        
        // 2a. Collected Amount Chart (Plan vs Actual - Birr)
        if (this.collectionAmountChartRef && this.collectionAmountChartRef.el) {
            const collectedAmountPlan = this.state.data.collection_performance?.collected_amount?.plan || 0;
            const collectedAmountActual = this.state.data.collection_performance?.collected_amount?.actual || 0;
            const normalizeCurrency = (val) => Number((val || 0) / 1000000);
            
            if (this._collectionAmountChart) {
                this._collectionAmountChart.destroy();
                this._collectionAmountChart = null;
            }
            try {
                this._collectionAmountChart = new Chart(this.collectionAmountChartRef.el, {
                    type: "bar",
                    data: {
                        labels: ['Collected Amount'],
                        datasets: [
                            { label: "Plan", data: [normalizeCurrency(collectedAmountPlan)], backgroundColor: '#e5e7eb', borderRadius: 8 },
                            { label: "Actual", data: [normalizeCurrency(collectedAmountActual)], backgroundColor: '#2563eb', borderRadius: 8 }
                        ]
                    },
                    options: {
                        ...baseOptions,
                        animation: { duration: 0 },
                        scales: { y: { beginAtZero: true } },
                        plugins: { ...baseOptions.plugins }
                    }
                });
            } catch (e) {
                console.error("Error creating collection amount chart:", e);
            }
        }
        
        // 2b. Collected from Clients Chart (Plan vs Actual - QTY)
        if (this.collectionClientsChartRef && this.collectionClientsChartRef.el) {
            const clientsPlan = this.state.data.collection_performance?.collected_from_clients?.plan || 0;
            const clientsActual = this.state.data.collection_performance?.collected_from_clients?.actual || 0;
            
            if (this._collectionClientsChart) {
                this._collectionClientsChart.destroy();
                this._collectionClientsChart = null;
            }
            try {
                this._collectionClientsChart = new Chart(this.collectionClientsChartRef.el, {
                    type: "bar",
                    data: {
                        labels: ['Collected from Clients'],
                        datasets: [
                            { label: "Plan", data: [clientsPlan], backgroundColor: '#e5e7eb', borderRadius: 8 },
                            { label: "Actual", data: [clientsActual], backgroundColor: '#2563eb', borderRadius: 8 }
                        ]
                    },
                    options: {
                        ...baseOptions,
                        animation: { duration: 0 },
                        scales: { y: { beginAtZero: true } },
                        plugins: { ...baseOptions.plugins }
                    }
                });
            } catch (e) {
                console.error("Error creating collection clients chart:", e);
            }
        }
        
        // Activity Timeseries Chart
        console.log("Timeline chart check:", {
            hasRef: !!this.activityTimeseriesChartRef.el,
            hasTimeseries: !!this.state.data.timeseries,
            hasLabels: !!(this.state.data.timeseries && this.state.data.timeseries.labels),
            labelsLength: this.state.data.timeseries?.labels?.length || 0,
            timeseriesData: this.state.data.timeseries
        });
        
        if (this.activityTimeseriesChartRef.el) {
            const ts = this.state.data.timeseries || {
                labels: [],
                collected_amount: [],
                collected_clients: [],
                discount_amount: []
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
                
                const timelineBaseOptions = {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: true,
                            position: 'bottom',
                            labels: {
                                font: { size: 12, family: 'Arial' },
                                padding: 10,
                                usePointStyle: true
                            }
                        },
                        tooltip: {
                            backgroundColor: 'rgba(0, 0, 0, 0.8)',
                            padding: 10,
                            titleFont: { size: 14 },
                            bodyFont: { size: 12 },
                            cornerRadius: 6
                        },
                        title: {
                            display: true,
                            text: "Activity Timeline",
                            font: { size: 14, weight: "bold" },
                        },
                    }
                };
                
                console.log("Creating timeline chart with data:", {
                    labels: labels,
                    collected_amount: ts.collected_amount || [],
                    collected_clients: ts.collected_clients || [],
                    discount_amount: ts.discount_amount || []
                });
                
                this._activityTimeseriesChart = new Chart(this.activityTimeseriesChartRef.el, {
                    type: "line",
                    data: {
                        labels: labels,
                        datasets: [
                            {
                                label: "Collected Amount (ETB)",
                                data: ts.collected_amount || labels.map(() => 0),
                                borderColor: "#2563eb",
                                backgroundColor: "rgba(37, 99, 235, 0.1)",
                                fill: false,
                                tension: 0.4,
                                borderWidth: 3,
                                pointRadius: 4,
                                pointHoverRadius: 6,
                            },
                            {
                                label: "Collected Clients",
                                data: ts.collected_clients || labels.map(() => 0),
                                borderColor: "#059669",
                                backgroundColor: "rgba(5, 150, 105, 0.1)",
                                fill: false,
                                tension: 0.4,
                                borderWidth: 3,
                                pointRadius: 4,
                                pointHoverRadius: 6,
                            },
                            {
                                label: "Discount Amount (ETB)",
                                data: ts.discount_amount || labels.map(() => 0),
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
                        animation: { duration: 0 },
                        interaction: { intersect: false, mode: 'index' },
                        scales: {
                            y: {
                                beginAtZero: true,
                                ticks: { font: { size: 12 }, precision: 0 },
                                title: { display: true, font: { size: 13, weight: "bold" } },
                            },
                            x: {
                                ticks: {
                                    maxRotation: 45,
                                    minRotation: 45,
                                    font: { size: 11 },
                                    maxTicksLimit: 15,
                                },
                                title: { display: true, font: { size: 13, weight: "bold" } },
                            },
                        },
                        plugins: {
                            legend: {
                                display: true,
                                position: 'bottom',
                                labels: { padding: 15, font: { size: 12 }, usePointStyle: true },
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
                setTimeout(() => {
                    if (this._activityTimeseriesChart) this._activityTimeseriesChart.resize();
                }, 100);
                console.log("Timeline chart created successfully");
            } catch (e) {
                console.error("Error creating activity timeseries chart:", e);
            }
        } else {
            console.warn("Timeline chart not rendered - missing data or ref");
        }
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
                const width = canvas.offsetWidth || canvas.width || 0;
                const height = canvas.offsetHeight || canvas.height || 0;
                
                if (width === 0 || height === 0) {
                    console.warn(`Canvas has no dimensions for ${chartName}: ${width}x${height}`);
                    return "";
                }
                
                // Force chart to render completely
                chart.update('none'); // Update without animation
                
                const img = chart.toBase64Image('image/png', 1.0);
                if (!img || img.length < 100) {
                    console.warn(`Chart image is too small or empty for ${chartName}: ${img ? img.length : 0} bytes`);
                    return "";
                }
                
                console.log(`Successfully captured ${chartName}: ${img.length} bytes, dimensions: ${width}x${height}`);
                return img;
            } catch (e) {
                console.error(`Error capturing chart image for ${chartName}:`, e);
                return "";
            }
        };
        
        // Capture all charts synchronously (like menu 1)
        const images = {
            stock_distribution_chart: safeImg(this._stockDistributionChart, "stock_distribution"),
            collection_amount_chart: safeImg(this._collectionAmountChart, "collection_amount"),
            collection_clients_chart: safeImg(this._collectionClientsChart, "collection_clients"),
            activity_timeseries_chart: safeImg(this._activityTimeseriesChart, "activity_timeseries"),
        };
        console.log("Chart images captured:", {
            stock_distribution: images.stock_distribution_chart ? `Yes` : "No",
            collection_amount: images.collection_amount_chart ? `Yes` : "No",
            collection_clients: images.collection_clients_chart ? `Yes` : "No"
        });
        return images;
    }
    
    async exportExcel() {
        if (!this.state.data) {
            this.notification.add("Please load data first", { type: "warning" });
            return;
        }
        
        console.log("Export Excel - Chart instances:", {
            stockDistribution: !!this._stockDistributionChart,
            collectionAmount: !!this._collectionAmountChart,
            collectionClients: !!this._collectionClientsChart
        });
        
        // Ensure charts are rendered
        this.renderCharts();
        
        // Wait a bit for charts to render, then capture
        await new Promise(resolve => setTimeout(resolve, 800));
        
        // Force chart update
        if (this._stockDistributionChart) this._stockDistributionChart.update('none');
        if (this._collectionAmountChart) this._collectionAmountChart.update('none');
        if (this._collectionClientsChart) this._collectionClientsChart.update('none');
        
        await new Promise(resolve => requestAnimationFrame(resolve));
        
        const images = this._getChartImages();
        console.log("Exporting Excel - Images captured:", Object.keys(images).map(k => `${k}: ${images[k] ? images[k].length : 0} bytes`));
        
        // Use JSON-RPC instead of form POST for better handling of large images
        try {
            const response = await this.rpc("/manager_reports/api/export_collection_excel", {
                date_from: this._getEffectiveDates().date_from,
                date_to: this._getEffectiveDates().date_to,
                chart_images: images
            });
            
            if (response && response.file_data) {
                // Download the file
                const link = document.createElement('a');
                link.href = 'data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,' + response.file_data;
                link.download = response.filename || 'Collection_Report.xlsx';
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
        
        console.log("Export PDF - Chart instances:", {
            stockDistribution: !!this._stockDistributionChart,
            collectionAmount: !!this._collectionAmountChart,
            collectionClients: !!this._collectionClientsChart
        });
        
        // Ensure charts are rendered
        this.renderCharts();
        
        // Wait a bit for charts to render, then capture
        await new Promise(resolve => setTimeout(resolve, 800));
        
        // Force chart update
        if (this._stockDistributionChart) this._stockDistributionChart.update('none');
        if (this._collectionAmountChart) this._collectionAmountChart.update('none');
        if (this._collectionClientsChart) this._collectionClientsChart.update('none');
        
        await new Promise(resolve => requestAnimationFrame(resolve));
        
        const images = this._getChartImages();
        console.log("Exporting PDF - Images captured:", Object.keys(images).map(k => `${k}: ${images[k] ? images[k].length : 0} bytes`));
        
        // Use JSON-RPC instead of form POST for better handling of large images
        try {
            const response = await this.rpc("/manager_reports/api/export_collection_pdf", {
                date_from: this._getEffectiveDates().date_from,
                date_to: this._getEffectiveDates().date_to,
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
    
    formatCurrency(value) {
        if (value === null || value === undefined) return '0.00';
        return Number(value).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }
    
    formatNumber(value) {
        if (value === null || value === undefined) return '0';
        return Number(value).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
    }

    t(key) {
        return _t(key);
    }
}

CollectionReportClient.template = "manager_reports.CollectionReportClient";

registry.category("actions").add("manager_reports.collection", CollectionReportClient);
