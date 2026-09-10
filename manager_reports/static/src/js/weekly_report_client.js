/** @odoo-module **/

import { Component, useState, onWillStart, onPatched, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadBundle } from "@web/core/assets";
import { _t } from "@web/core/l10n/translation";

export class WeeklyReportClient extends Component {
    setup() {
        this.notification = useService("notification");
        this.rpc = useService("rpc");
        this.soldChartRef = useRef("soldUnitsChart");
        this.birrChartRef = useRef("birrChart");
        this.timelineChartRef = useRef("timelineChart");
        this._soldChart = null;
        this._birrChart = null;
        this._timelineChart = null;
        this._chartsRendered = false;

        const today = new Date();
        const formatDate = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
        const month = today.getMonth();
        const year = today.getFullYear();

        this.state = useState({
            loading: true,
            wings: [],
            wing_id: 'all',
            period_type: 'weekly',
            date_from: formatDate(today),
            date_to: formatDate(today),
            week_of: formatDate(today),
            month: String(month + 1),
            year: String(year),
            transactions: [],
            total_sold_unit: [],
            total_units: 0,
            birr_by_team: [],
            grand_total_price: 0,
            grand_total_paid: 0,
            timeseries: { labels: [], sales_count: [], total_price: [], paid_amount: [] },
        });

        onWillStart(async () => {
            await loadBundle("web.chartjs_lib");
            await this.loadData();
        });

        onPatched(() => {
            if (!this.state.loading && !this._chartsRendered) {
                setTimeout(() => this.renderCharts(), 100);
            }
        });
    }

    _getEffectiveDates() {
        const fmt = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
        if (this.state.period_type === 'weekly') {
            const d = new Date(this.state.week_of + 'T12:00:00');
            const day = d.getDay();
            const diff = d.getDate() - day + (day === 0 ? -6 : 1);
            const mon = new Date(d);
            mon.setDate(diff);
            const sun = new Date(mon);
            sun.setDate(mon.getDate() + 6);
            return { date_from: fmt(mon), date_to: fmt(sun) };
        }
        if (this.state.period_type === 'monthly') {
            const y = parseInt(this.state.year, 10) || new Date().getFullYear();
            const m = parseInt(this.state.month, 10) || 1;
            const first = new Date(y, m - 1, 1);
            const last = new Date(y, m, 0);
            return { date_from: fmt(first), date_to: fmt(last) };
        }
        return { date_from: this.state.date_from, date_to: this.state.date_to };
    }

    onPeriodChange() {
        this.loadData();
    }

    onCriteriaChange() {
        this.loadData();
    }

    async loadData() {
        this.state.loading = true;
        this._chartsRendered = false;
        const { date_from, date_to } = this._getEffectiveDates();
        try {
            const [result, tsResult] = await Promise.all([
                this.rpc("/manager_reports/api/weekly_report_data", {
                    date_from,
                    date_to,
                    wing_id: this.state.wing_id,
                }),
                this.rpc("/manager_reports/api/weekly_report_timeseries", {
                    date_from,
                    date_to,
                    wing_id: this.state.wing_id,
                }),
            ]);
            if (result && result.success) {
                this.state.wings = result.wings || [];
                this.state.transactions = result.transactions || [];
                this.state.total_sold_unit = result.total_sold_unit || [];
                this.state.total_units = result.total_units || 0;
                this.state.birr_by_team = result.birr_by_team || [];
                this.state.grand_total_price = result.grand_total_price || 0;
                this.state.grand_total_paid = result.grand_total_paid || 0;
                this.state.date_from = date_from;
                this.state.date_to = date_to;
            } else {
                this.state.transactions = [];
                this.state.total_sold_unit = [];
                this.state.birr_by_team = [];
                this.notification.add(result?.error || "Failed to load report", { type: "danger" });
            }
            if (tsResult && tsResult.success) {
                this.state.timeseries = {
                    labels: tsResult.labels || [],
                    sales_count: tsResult.sales_count || [],
                    total_price: tsResult.total_price || [],
                    paid_amount: tsResult.paid_amount || [],
                };
            } else {
                this.state.timeseries = { labels: [], sales_count: [], total_price: [], paid_amount: [] };
            }
        } catch (e) {
            console.error("Weekly Report loadData:", e);
            this.notification.add("Error loading report data", { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    renderCharts() {
        if (!this.soldChartRef.el || !this.birrChartRef.el || !window.Chart || this._chartsRendered) return;
        if (this._soldChart) {
            this._soldChart.destroy();
            this._soldChart = null;
        }
        if (this._birrChart) {
            this._birrChart.destroy();
            this._birrChart = null;
        }
        if (this._timelineChart) {
            this._timelineChart.destroy();
            this._timelineChart = null;
        }
        const units = this.state.total_sold_unit || [];
        const labels = units.map((u) => u.team_name || "");
        const dataUnits = units.map((u) => Number(u.units) || 0);
        this._soldChart = new window.Chart(this.soldChartRef.el, {
            type: 'bar',
            data: {
                labels,
                datasets: [{ label: 'Sold Units', data: dataUnits, backgroundColor: 'rgba(54, 162, 235, 0.8)' }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: { y: { beginAtZero: true } },
                plugins: { legend: { position: 'top' }, title: { display: true, text: 'Total Sold Unit by Team' } },
            },
        });
        const birr = this.state.birr_by_team || [];
        const birrLabels = birr.map((b) => b.team_name || "");
        const totalPrices = birr.map((b) => Number(b.total_price) || 0);
        const paidAmounts = birr.map((b) => Number(b.paid_amount) || 0);
        this._birrChart = new window.Chart(this.birrChartRef.el, {
            type: 'bar',
            data: {
                labels: birrLabels,
                datasets: [
                    { label: 'Total Price', data: totalPrices, backgroundColor: 'rgba(54, 162, 235, 0.8)', stack: 'birr' },
                    { label: 'Paid Amount', data: paidAmounts, backgroundColor: 'rgba(205, 92, 92, 0.8)', stack: 'birr' },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: { x: { stacked: true }, y: { beginAtZero: true, stacked: true } },
                plugins: { legend: { position: 'top' }, title: { display: true, text: 'In Birr (Total & Paid) by Team' } },
            },
        });
        const ts = this.state.timeseries || {};
        const tsLabels = (ts.labels || []).map((d) => {
            const parts = String(d).split('-');
            if (parts.length === 3) return parts[2] + '/' + parts[1];
            return d;
        });
        if (this.timelineChartRef.el) {
        this._timelineChart = new window.Chart(this.timelineChartRef.el, {
            type: 'line',
            data: {
                labels: tsLabels,
                datasets: [
                    { label: 'Sold Units', data: ts.sales_count || [], borderColor: 'rgb(54, 162, 235)', backgroundColor: 'rgba(54, 162, 235, 0.1)', fill: true, yAxisID: 'y' },
                    { label: 'Total Price (Birr)', data: ts.total_price || [], borderColor: 'rgb(75, 192, 192)', backgroundColor: 'rgba(75, 192, 192, 0.1)', fill: true, yAxisID: 'y1' },
                    { label: 'Paid Amount (Birr)', data: ts.paid_amount || [], borderColor: 'rgb(205, 92, 92)', backgroundColor: 'rgba(205, 92, 92, 0.1)', fill: true, yAxisID: 'y1' },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                scales: {
                    y: { type: 'linear', display: true, position: 'left', beginAtZero: true, title: { display: true, text: 'Units' } },
                    y1: { type: 'linear', display: true, position: 'right', beginAtZero: true, grid: { drawOnChartArea: false }, title: { display: true, text: 'Birr' } },
                },
                plugins: { legend: { position: 'top' }, title: { display: true, text: 'Timeline: Sales & Amount by Date' } },
            },
        });
        }
        this._chartsRendered = true;
    }

    formatNumber(num) {
        if (num === null || num === undefined) return '0';
        return Number(num).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
    }

    formatCurrency(amount) {
        if (amount === null || amount === undefined) return '0.00';
        return Number(amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    get monthOptions() {
        return Array.from({ length: 12 }, (_, i) => ({ value: String(i + 1), label: ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][i] }));
    }

    get yearOptions() {
        const y = new Date().getFullYear();
        return Array.from({ length: 6 }, (_, i) => y - i);
    }

    t(key) {
        return _t(key);
    }
}

WeeklyReportClient.template = "manager_reports.WeeklyReportClient";
registry.category("actions").add("manager_reports.weekly_report", WeeklyReportClient);
