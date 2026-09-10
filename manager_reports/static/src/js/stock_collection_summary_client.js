/** @odoo-module **/

import { Component, useState, onWillStart, onPatched, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadBundle } from "@web/core/assets";
import { _t } from "@web/core/l10n/translation";

export class StockCollectionSummaryClient extends Component {
    setup() {
        this.notification = useService("notification");
        this.rpc = useService("rpc");
        this._t = _t;  // Expose translation function to template
        
        // Chart refs
        this.stockAvailableChartRef = useRef("stockAvailableChart");
        this.stockSoldChartRef = useRef("stockSoldChart");
        this.stockSoldTimelineChartRef = useRef("stockSoldTimelineChart");
        
        // Chart instances
        this._stockAvailableChart = null;
        this._stockSoldChart = null;
        this._stockSoldTimelineChart = null;
        
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
            dataLoaded: false,
            use_all_dates: false,
            date_from: formatDate(today),
            date_to: formatDate(today),
            data: {
                stock_available: {
                    residential: { qty: 0, values: 0.0 },
                    commercial: { qty: 0, values: 0.0 },
                    mixed_use: { qty: 0, values: 0.0 },
                    total: { qty: 0, values: 0.0 }
                },
                stock_sold: {
                    residential: { qty: 0, values: 0.0, achievement_percent: 0.0 },
                    commercial: { qty: 0, values: 0.0, achievement_percent: 0.0 },
                    mixed_use: { qty: 0, values: 0.0, achievement_percent: 0.0 },
                    total: { qty: 0, values: 0.0, achievement_percent: 0.0 }
                },
                total_collection: 0.0,
                average_collection_per_day: 0.0,
                average_collection_per_site: 0.0,
                average_achievement_percent: 0.0,
                total_average_progress_compared_to_plan: 0.0,
                sites_ready_for_handover: 0,
                timeseries: {
                    labels: [],
                    stock_sold_residential: [],
                    stock_sold_commercial: [],
                    stock_sold_mixed_use: [],
                    collection_amount: []
                }
            }
        });
        
        onWillStart(async () => {
            await loadBundle("web.chartjs_lib");
            await this.loadData();
        });
        
        onPatched(() => {
            if (!this.state.loading && this.state.dataLoaded && this.state.data &&
                !this._chartsRendered && !this._isRenderingCharts) {
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
        this.state.dataLoaded = false;
        const { date_from, date_to } = this._getEffectiveDates();
        try {
            const [result, timeseriesResult] = await Promise.all([
                this.rpc("/manager_reports/api/stock_collection_summary_data", {
                    date_from,
                    date_to,
                    wing_id: 'all'
                }),
                this.rpc("/manager_reports/api/stock_collection_summary_timeseries", {
                    date_from,
                    date_to,
                    wing_id: 'all'
                })
            ]);
            
            if (result.success) {
                const d = result.data || {};
                const sa = d.stock_available || {};
                const ss = d.stock_sold || {};
                this.state.data = {
                    ...d,
                    stock_available: {
                        residential: sa.residential || { qty: 0, values: 0 },
                        commercial: sa.commercial || { qty: 0, values: 0 },
                        mixed_use: sa.mixed_use || { qty: 0, values: 0 },
                        total: sa.total || { qty: 0, values: 0 }
                    },
                    stock_sold: {
                        residential: ss.residential || { qty: 0, values: 0, achievement_percent: 0 },
                        commercial: ss.commercial || { qty: 0, values: 0, achievement_percent: 0 },
                        mixed_use: ss.mixed_use || { qty: 0, values: 0, achievement_percent: 0 },
                        total: ss.total || { qty: 0, values: 0, achievement_percent: 0 }
                    }
                };
                if (timeseriesResult && timeseriesResult.success && timeseriesResult.data) {
                    this.state.data.timeseries = timeseriesResult.data;
                } else if (!this.state.data.timeseries) {
                    this.state.data.timeseries = {
                        labels: [],
                        stock_sold_residential: [],
                        stock_sold_commercial: [],
                        stock_sold_mixed_use: [],
                        collection_amount: []
                    };
                }
                this.state.dataLoaded = true;  // Mark data as loaded
                
                // Force chart render after data is loaded
                setTimeout(() => {
                    this.renderCharts();
                }, 100);
            } else {
                this.notification.add(result.error || _t("Error loading data"), { type: "danger" });
            }
        } catch (error) {
            console.error("Error loading data:", error);
            this.notification.add(_t("Error loading report data"), { type: "danger" });
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
        
        // 1. Stock Available Pie Chart
        if (this.stockAvailableChartRef && this.stockAvailableChartRef.el) {
            const residential = this.state.data.stock_available?.residential?.qty || 0;
            const commercial = this.state.data.stock_available?.commercial?.qty || 0;
            const mixedUse = this.state.data.stock_available?.mixed_use?.qty || 0;
            const labels = [];
            const data = [];
            const colors = [];
            if (residential > 0) { labels.push('Residential'); data.push(residential); colors.push('#2563eb'); }
            if (commercial > 0) { labels.push('Commercial'); data.push(commercial); colors.push('#059669'); }
            if (mixedUse > 0) { labels.push('Mixed use'); data.push(mixedUse); colors.push('#7c3aed'); }
            if (labels.length === 0) { labels.push('Residential', 'Commercial', 'Mixed use'); data.push(0, 0, 0); colors.push('#2563eb', '#059669', '#7c3aed'); }
            
            if (this._stockAvailableChart) {
                this._stockAvailableChart.destroy();
                this._stockAvailableChart = null;
            }
            
            try {
                this._stockAvailableChart = new Chart(this.stockAvailableChartRef.el, {
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
                            text: 'Stock Available Distribution',
                            font: { size: 14, weight: 'bold' }
                        },
                        tooltip: {
                            ...baseOptions.plugins.tooltip,
                            position: 'average',
                            callbacks: {
                                label: function(context) {
                                    const label = context.label || '';
                                    const value = context.parsed ?? context.raw;
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const pct = total ? ((value / total) * 100).toFixed(1) : 0;
                                    return 'QTY: ' + value + ' (' + pct + '%)';
                                }
                            }
                        }
                    }
                }
            });
            } catch (e) {
                console.error("Error creating stock available chart:", e);
            }
        }
        
        // 2. Available vs Sold comparison (QTY only)
        if (this.stockSoldChartRef && this.stockSoldChartRef.el) {
            const availRes = this.state.data.stock_available?.residential?.qty || 0;
            const availComm = this.state.data.stock_available?.commercial?.qty || 0;
            const availMixed = this.state.data.stock_available?.mixed_use?.qty || 0;
            const soldRes = this.state.data.stock_sold?.residential?.qty || 0;
            const soldComm = this.state.data.stock_sold?.commercial?.qty || 0;
            const soldMixed = this.state.data.stock_sold?.mixed_use?.qty || 0;
            if (this._stockSoldChart) {
                this._stockSoldChart.destroy();
                this._stockSoldChart = null;
            }
            try {
                this._stockSoldChart = new Chart(this.stockSoldChartRef.el, {
                    type: "bar",
                    data: {
                        labels: ['Residential', 'Commercial', 'Mixed use'],
                        datasets: [
                            { label: "Available", data: [availRes, availComm, availMixed], backgroundColor: '#e5e7eb', borderRadius: 8 },
                            { label: "Sold", data: [soldRes, soldComm, soldMixed], backgroundColor: '#2563eb', borderRadius: 8 }
                        ]
                    },
                    options: {
                        ...baseOptions,
                        animation: { duration: 0 },
                        scales: {
                            y: {
                                beginAtZero: true,
                                title: { display: true, text: 'Quantity' }
                            }
                        },
                        plugins: {
                            ...baseOptions.plugins,
                            title: {
                                display: true,
                                text: 'Available vs Sold (QTY)',
                                font: { size: 14, weight: 'bold' }
                            },
                            tooltip: {
                                ...baseOptions.plugins.tooltip,
                                callbacks: {
                                    label: function(context) {
                                        return (context.dataset.label || '') + ': ' + context.parsed.y;
                                    }
                                }
                            }
                        }
                    }
                });
            } catch (e) {
                console.error("Error creating available vs sold chart:", e);
            }
        }
        
        // Stock Sold Over Time (QTY only)
        const ts = this.state.data.timeseries || {
            labels: [], stock_sold_residential: [], stock_sold_commercial: [], stock_sold_mixed_use: [], collection_amount: []
        };
        let labels = ts.labels || [];
        if (labels.length === 0 && this.state.date_from && this.state.date_to) {
            const dateFrom = new Date(this.state.date_from);
            const dateTo = new Date(this.state.date_to);
            const daysDiff = Math.ceil((dateTo - dateFrom) / (1000 * 60 * 60 * 24)) + 1;
            if (daysDiff <= 31) {
                for (let d = new Date(dateFrom); d <= dateTo; d.setDate(d.getDate() + 1)) {
                    labels.push(d.toISOString().split('T')[0]);
                }
            } else if (daysDiff <= 365) {
                for (let d = new Date(dateFrom); d <= dateTo; d.setDate(d.getDate() + 7)) {
                    const weekEnd = new Date(d);
                    weekEnd.setDate(weekEnd.getDate() + 6);
                    if (weekEnd > dateTo) weekEnd = dateTo;
                    labels.push(`${d.toISOString().split('T')[0]} to ${weekEnd.toISOString().split('T')[0]}`);
                }
            } else {
                const current = new Date(dateFrom.getFullYear(), dateFrom.getMonth(), 1);
                while (current <= dateTo) {
                    labels.push(`${current.getFullYear()}-${String(current.getMonth() + 1).padStart(2, '0')}`);
                    current.setMonth(current.getMonth() + 1);
                }
            }
        }
        const timelineOpts = { responsive: true, maintainAspectRatio: false, animation: { duration: 0 }, interaction: { intersect: false, mode: 'index' }, scales: { y: { beginAtZero: true }, x: { ticks: { maxRotation: 45, minRotation: 45, maxTicksLimit: 15 } } }, plugins: { legend: { position: 'bottom' } } };
        
        if (this.stockSoldTimelineChartRef && this.stockSoldTimelineChartRef.el) {
            if (this._stockSoldTimelineChart) this._stockSoldTimelineChart.destroy();
            try {
                this._stockSoldTimelineChart = new Chart(this.stockSoldTimelineChartRef.el, {
                    type: "line",
                    data: {
                        labels: labels,
                        datasets: [
                            { label: "Residential", data: ts.stock_sold_residential || labels.map(() => 0), borderColor: "#2563eb", fill: false, tension: 0.4, borderWidth: 2, pointRadius: 3 },
                            { label: "Commercial", data: ts.stock_sold_commercial || labels.map(() => 0), borderColor: "#059669", fill: false, tension: 0.4, borderWidth: 2, pointRadius: 3 },
                            { label: "Mixed use", data: ts.stock_sold_mixed_use || labels.map(() => 0), borderColor: "#7c3aed", fill: false, tension: 0.4, borderWidth: 2, pointRadius: 3 }
                        ]
                    },
                    options: timelineOpts
                });
            } catch (e) { console.error("Error creating stock sold timeline:", e); }
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
                
                const canvas = chart.canvas;
                if (!canvas) {
                    console.warn(`Canvas element not found for ${chartName}`);
                    return "";
                }
                
                const width = canvas.offsetWidth || canvas.width || 0;
                const height = canvas.offsetHeight || canvas.height || 0;
                
                if (width === 0 || height === 0) {
                    console.warn(`Canvas has no dimensions for ${chartName}: ${width}x${height}`);
                    return "";
                }
                
                chart.update('none');
                
                const img = chart.toBase64Image('image/png', 1.0);
                if (!img || img.length < 100) {
                    console.warn(`Chart image is too small for ${chartName}: ${img ? img.length : 0} bytes`);
                    return "";
                }
                console.log(`Successfully captured ${chartName}: ${img.length} bytes`);
                return img;
            } catch (e) {
                console.error(`Error capturing chart image for ${chartName}:`, e);
                return "";
            }
        };
        
        // Capture all charts synchronously (like menu 1)
        return {
            stock_available_chart: safeImg(this._stockAvailableChart, "stock_available"),
            stock_sold_chart: safeImg(this._stockSoldChart, "stock_sold"),
            stock_sold_timeline_chart: safeImg(this._stockSoldTimelineChart, "stock_sold_timeline"),
        };
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
        if (this._stockAvailableChart) this._stockAvailableChart.update('none');
        if (this._stockSoldChart) this._stockSoldChart.update('none');
        if (this._stockSoldTimelineChart) this._stockSoldTimelineChart.update('none');
        
        await new Promise(resolve => requestAnimationFrame(resolve));
        
        const images = this._getChartImages();
        console.log("Exporting Excel - Images captured:", Object.keys(images).map(k => `${k}: ${images[k] ? images[k].length : 0} bytes`));
        
        // Use JSON-RPC instead of form POST for better handling of large images
        try {
            const { date_from, date_to } = this._getEffectiveDates();
            const response = await this.rpc("/manager_reports/api/export_stock_collection_summary_excel", {
                date_from,
                date_to,
                wing_id: this.state.wing_id,
                chart_images: images
            });
            
            if (response && response.file_data) {
                // Download the file
                const link = document.createElement('a');
                link.href = 'data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,' + response.file_data;
                link.download = 'Consolidate_Report.xlsx';
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
        if (this._stockAvailableChart) this._stockAvailableChart.update('none');
        if (this._stockSoldChart) this._stockSoldChart.update('none');
        if (this._stockSoldTimelineChart) this._stockSoldTimelineChart.update('none');
        
        await new Promise(resolve => requestAnimationFrame(resolve));
        
        const images = this._getChartImages();
        console.log("Exporting PDF - Images captured:", Object.keys(images).map(k => `${k}: ${images[k] ? images[k].length : 0} bytes`));
        
        // Use JSON-RPC instead of form POST for better handling of large images
        try {
            const { date_from, date_to } = this._getEffectiveDates();
            const response = await this.rpc("/manager_reports/api/export_stock_collection_summary_pdf", {
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
    
    formatCurrency(value) {
        return new Intl.NumberFormat('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(value || 0);
    }

    formatAmount(value) {
        return new Intl.NumberFormat('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(value || 0);
    }
    
    formatNumber(value) {
        return new Intl.NumberFormat('en-US').format(value || 0);
    }
    
    // Translation helper method for template
    t(key) {
        return _t(key);
    }
}

StockCollectionSummaryClient.template = "manager_reports.StockCollectionSummaryClient";

registry.category("actions").add("manager_reports.stock_collection_summary", StockCollectionSummaryClient);

