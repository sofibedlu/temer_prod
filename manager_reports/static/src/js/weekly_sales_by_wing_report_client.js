/** @odoo-module **/

import { Component, useState, onWillStart, onPatched, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadBundle } from "@web/core/assets";
import { _t } from "@web/core/l10n/translation";

export class WeeklySalesByWingReportClient extends Component {
    setup() {
        this.notification = useService("notification");
        this.rpc = useService("rpc");
        this.chartRef = useRef("soldReservedChart");
        this._chart = null;
        this._chartsRendered = false;

        const today = new Date();
        const formatDate = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
        const month = today.getMonth();
        const year = today.getFullYear();

        this.state = useState({
            loading: true,
            wings: [],
            period_type: 'weekly',
            date_from: formatDate(today),
            date_to: formatDate(today),
            week_of: formatDate(today),
            month: String(month + 1),
            year: String(year),
            opening_stock: {
                residence: { qty: 0, value: 0 },
                shops: { qty: 0, value: 0 },
                total: { qty: 0, value: 0 },
            },
            summary_by_wing: [],
            sites: [],
        });

        onWillStart(async () => {
            await loadBundle("web.chartjs_lib");
            await this.loadData();
        });

        onPatched(() => {
            if (!this.state.loading && !this._chartsRendered) {
                setTimeout(() => this.renderChart(), 100);
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
            const result = await this.rpc("/manager_reports/api/weekly_sales_by_wing_data", {
                date_from,
                date_to,
            });

            if (result && result.success) {
                this.state.wings = result.wings || [];
                this.state.sites = result.sites || [];
                this.state.summary_by_wing = result.summary_by_wing || [];
                this.state.date_from = date_from;
                this.state.date_to = date_to;
                const os = result.opening_stock || {};
                const safe = (o, k) => (o && o[k]) ? o[k] : { qty: 0, value: 0 };
                this.state.opening_stock = {
                    residence: safe(os, 'residence'),
                    shops: safe(os, 'shops'),
                    total: safe(os, 'total'),
                };
            } else {
                this.state.sites = [];
                this.state.summary_by_wing = [];
                this.notification.add(result?.error || "Failed to load report", { type: "danger" });
            }
        } catch (e) {
            console.error("Weekly Sales By Wing loadData:", e);
            this.notification.add("Error loading report data", { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    renderChart() {
        if (!this.chartRef.el || !window.Chart || this._chartsRendered) return;
        if (this._chart) {
            this._chart.destroy();
            this._chart = null;
        }
        const rows = this.state.summary_by_wing || [];
        const labels = rows.map((r) => r.wing_name || "");
        const sold = rows.map((r) => Number(r.sold) || 0);
        const reserved = rows.map((r) => Number(r.reserved) || 0);
        this._chart = new window.Chart(this.chartRef.el, {
            type: 'bar',
            data: {
                labels,
                datasets: [
                    { label: 'SOLD', data: sold, backgroundColor: 'rgba(205, 92, 92, 0.8)' },
                    { label: 'RESERVED', data: reserved, backgroundColor: 'rgba(54, 162, 235, 0.8)' },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { beginAtZero: true },
                },
                plugins: {
                    legend: { position: 'top' },
                    title: { display: true, text: 'SOLD vs RESERVED by Wing' },
                },
            },
        });
        this._chartsRendered = true;
    }

    get summaryTotals() {
        const rows = this.state.summary_by_wing || [];
        return {
            sold: rows.reduce((s, r) => s + (Number(r.sold) || 0), 0),
            total: rows.reduce((s, r) => s + (Number(r.total) || 0), 0),
            paid: rows.reduce((s, r) => s + (Number(r.paid) || 0), 0),
            reserved: rows.reduce((s, r) => s + (Number(r.reserved) || 0), 0),
        };
    }

    get sitesTotals() {
        const sites = this.state.sites || [];
        const wings = this.state.wings || [];
        const t = {
            opening_stock: 0,
            available_stock: 0,
            total_reservation: 0,
            total_deals_closed: 0,
        };
        const byWing = {};
        for (const w of wings) {
            byWing[w.id] = { sold: 0, reserved: 0 };
        }
        for (const s of sites) {
            t.opening_stock += Number(s.opening_stock) || 0;
            t.available_stock += Number(s.available_stock) || 0;
            t.total_reservation += Number(s.total_reservation) || 0;
            t.total_deals_closed += Number(s.total_deals_closed) || 0;
            const wingsData = s.wings || {};
            for (const wid of Object.keys(wingsData)) {
                if (byWing[wid]) {
                    byWing[wid].sold += Number(wingsData[wid]?.sold) || 0;
                    byWing[wid].reserved += Number(wingsData[wid]?.reserved) || 0;
                }
            }
        }
        return { ...t, byWing };
    }

    formatNumber(num) {
        if (num === null || num === undefined) return '0';
        return Number(num).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
    }

    formatCurrency(amount) {
        if (amount === null || amount === undefined) return '0.00';
        return Number(amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    reportTitle() {
        const d = this.state.date_to || '';
        return d ? `Weekly Sales Report By Wing as of ${d}` : 'Weekly Sales Report By Wing';
    }

    openingLabel() {
        const d = this.state.date_from || '';
        return d ? `OPENING STOCK ON ${d}` : 'OPENING STOCK';
    }

    availableLabel() {
        const d = this.state.date_to || '';
        return d ? `AVAILABLE STOCK ON ${d}` : 'AVAILABLE STOCK';
    }

    reservationLabel() {
        const d = this.state.date_to || '';
        return d ? `TOTAL RESERVATION ${d}` : 'TOTAL RESERVATION';
    }

    _postDownload(url, payload, openInNewWindow = false) {
        const form = document.createElement("form");
        form.method = "POST";
        form.action = url;
        form.style.display = "none";
        if (openInNewWindow) form.target = "_blank";
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
        this._postDownload("/manager_reports/api/export_weekly_sales_by_wing_excel", { date_from, date_to });
    }

    exportPDF() {
        const { date_from, date_to } = this._getEffectiveDates();
        this._postDownload("/manager_reports/api/export_weekly_sales_by_wing_pdf", { date_from, date_to }, true);
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

WeeklySalesByWingReportClient.template = "manager_reports.WeeklySalesByWingReportClient";
registry.category("actions").add("manager_reports.weekly_sales_by_wing", WeeklySalesByWingReportClient);
