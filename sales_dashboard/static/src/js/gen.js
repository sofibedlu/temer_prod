/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, onMounted, useState, useRef } from "@odoo/owl";
import { loadJS } from "@web/core/assets";

class SupervisorDashboard extends Component {

setup() {
    this.orm = useService("orm");
    this.action = useService("action");
    this.user = useService("user");
    this.chartRef = useRef("chart");
    
    this.state = useState({
        loading: true,
        rawData: [],
        wingSummary: [],
        supervisorSummary: [],
        salesPersonData: [],
        eventTypes: [],
        filters: {
            wing: null,
            supervisor: "", // Initially empty; will set below
            dateRange: '30days'
        },
        chart: null
    });

    this.isSupervisor = false;
    this.supervisorName = null;

    // Helper function accessible in templates
    this.getEventColor = (eventType) => {
        const colors = {
            'Won': 'success',
            'Reservation': 'info',
            'Follow Up': 'warning',
            'Prospect': 'primary',
            'Expired': 'danger',
            'Email': 'secondary',
            'Call': 'dark',
            'Site Visit': 'success',
            'Office Visit': 'info',
            'SMS': 'primary',
            'To Do': 'warning'
        };
        return colors[eventType] || 'light';
    };



    onWillStart(async () => {
        await loadJS("/web/static/lib/Chart/Chart.js");

        this.isSupervisor = await this.user.hasGroup('property_sales.access_property_sales_supervisor_group');

        const userData = await this.orm.searchRead(
            "res.users",
            [['id', '=', this.user.userId]],
            ['partner_id']
        );

        if (userData.length) {
            this.supervisorName = userData[0].partner_id[1];
            // Always set the supervisor filter to the logged-in supervisor's name
            this.state.filters.supervisor = this.supervisorName;
        }

        await this.loadDashboardData();

        // Ensure supervisorSummary always contains the logged-in supervisor for display
        if (
            this.supervisorName &&
            !this.state.supervisorSummary.some(s => s.name === this.supervisorName)
        ) {
            this.state.supervisorSummary.push({
                wing: '', // Optionally set wing if available
                name: this.supervisorName,
                totalLeads: 0,
                keyEvents: 0,
                salesPersons: 0
            });
        }
    });


    onMounted(() => {
        this.renderChart();
    });
}

    async loadDashboardData() {
        this.state.loading = true;
        try {
            const results = await this.orm.call(
                'crm.lead',
                'get_supervisor_dashboard_data',
                [this.getDateCondition()],
                {}
            );
            this.processDashboardData(results);
        } finally {
            this.state.loading = false;
        }
    }

    getDateCondition() {
        return this.state.filters.dateRange;
    }

    processDashboardData(results) {
        if (this.isSupervisor && this.supervisorName) {
            results = results.filter(row => row.supervisor_name === this.supervisorName);
        }
        this.state.rawData = results;
        this.state.eventTypes = [...new Set(results.map(row => row.event_type))];
        this.recomputeSummaries();
        this.updateFilteredData();
        this.updateDashboardCards();
        this.renderChart();
    }

    recomputeSummaries() {
        const filtered = this.state.rawData.filter(row =>
            (!this.state.filters.wing || row.wing_name === this.state.filters.wing) &&
            (!this.state.filters.supervisor || row.supervisor_name === this.state.filters.supervisor)
        );

        const wingMap = new Map();
        const supervisorMap = new Map();

        filtered.forEach(row => {
            const wing = wingMap.get(row.wing_name) || {
                name: row.wing_name, totalLeads: 0, keyEvents: 0, supervisors: new Set(), salesPersons: new Set()
            };
            wing.totalLeads += row.count;
            if (['Reservation', 'Won', 'Expired'].includes(row.event_type)) wing.keyEvents += row.count;
            wing.supervisors.add(row.supervisor_name);
            wing.salesPersons.add(row.sales_person);
            wingMap.set(row.wing_name, wing);

            const supervisorKey = `${row.wing_name}|${row.supervisor_name}`;
            const supervisor = supervisorMap.get(supervisorKey) || {
                wing: row.wing_name, name: row.supervisor_name, totalLeads: 0, keyEvents: 0, salesPersons: new Set()
            };
            supervisor.totalLeads += row.count;
            if (['Reservation', 'Won', 'Expired'].includes(row.event_type)) supervisor.keyEvents += row.count;
            supervisor.salesPersons.add(row.sales_person);
            supervisorMap.set(supervisorKey, supervisor);
        });

        this.state.wingSummary = Array.from(wingMap.values()).map(w => ({ ...w, supervisors: w.supervisors.size, salesPersons: w.salesPersons.size }));
        this.state.supervisorSummary = Array.from(supervisorMap.values()).map(s => ({ ...s, salesPersons: s.salesPersons.size }));
    }

    updateDashboardCards() {
        const data = this.state.salesPersonData;
        this.state.totalLeads = data.reduce((a, b) => a + b.count, 0);
        this.state.totalKeyEvents = data.filter(r => ['Reservation', 'Won', 'Expired'].includes(r.event_type)).reduce((a, b) => a + b.count, 0);
        this.state.uniqueSalesPersons = [...new Set(data.map(r => r.sales_person))];
        this.state.uniqueSupervisors = [...new Set(data.map(r => r.supervisor_name))];
    }

    updateFilteredData() {
        this.state.salesPersonData = this.state.rawData.filter(row =>
            (!this.state.filters.wing || row.wing_name === this.state.filters.wing) &&
            (!this.state.filters.supervisor || row.supervisor_name === this.state.filters.supervisor)
        );
    }

    renderChart() {
        if (this.state.chart) {
            this.state.chart.destroy();
        }

        if (!this.chartRef.el) return;

        const eventCounts = {};
        this.state.eventTypes.forEach(event => {
            eventCounts[event] = this.getEventCount(event);
        });

        const ctx = this.chartRef.el.getContext('2d');
        this.state.chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: Object.keys(eventCounts),
                datasets: [{
                    label: 'Event Counts',
                    data: Object.values(eventCounts),
                    backgroundColor: Object.keys(eventCounts).map(event => 
                        `var(--bs-${this.getEventColor(event)})`
                    ),
                    borderColor: Object.keys(eventCounts).map(event => 
                        `var(--bs-${this.getEventColor(event)})`
                    ),
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (context) => `${context.dataset.label}: ${context.raw}`
                        }
                    }
                },
                scales: {
                    y: { beginAtZero: true }
                }
            }
        });

        // Pie Chart: Event Type Distribution
        if (this.chartPieRef && this.chartPieRef.el) {
            // Use filtered data for the pie chart (not rawData)
            const filtered = this.state.rawData.filter(row =>
                (!this.state.filters.wing || row.wing_name === this.state.filters.wing) &&
                (!this.state.filters.supervisor || row.supervisor_name === this.state.filters.supervisor)
            );
            const eventCounts = {};
            filtered.forEach(row => {
                if (!eventCounts[row.event_type]) eventCounts[row.event_type] = 0;
                eventCounts[row.event_type] += row.count;
            });
            const pieLabels = Object.keys(eventCounts);
            const pieData = Object.values(eventCounts);
            const pieColors = pieLabels.map((event, i) => `var(--bs-${this.getEventColor(event)})`);
            if (this.chartPie) this.chartPie.destroy();
            this.chartPie = new Chart(this.chartPieRef.el, {
                type: 'pie',
                data: {
                    labels: pieLabels,
                    datasets: [{
                        data: pieData,
                        backgroundColor: pieColors,
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: true },
                        tooltip: {
                            callbacks: {
                                label: (context) => `${context.label}: ${context.raw}`
                            }
                        }
                    }
                }
            });
        }

        // Bar Chart: Key Events by Sales Person
        if (this.chartBarRef && this.chartBarRef.el) {
            const keyEvents = ['Reservation', 'Won', 'Expired'];
            const filtered = this.state.rawData.filter(row =>
                (!this.state.filters.wing || row.wing_name === this.state.filters.wing) &&
                (!this.state.filters.supervisor || row.supervisor_name === this.state.filters.supervisor)
            );
            const salesPersons = [...new Set(filtered.map(r => r.sales_person))];
            const barLabels = salesPersons;
            const barData = salesPersons.map(sp =>
                filtered
                    .filter(r => r.sales_person === sp && keyEvents.includes(r.event_type))
                    .reduce((a, b) => a + b.count, 0)
            );
            const barColors = barLabels.map((_, i) => `var(--bs-primary)`);
            if (this.chartBar) this.chartBar.destroy();
            this.chartBar = new Chart(this.chartBarRef.el, {
                type: 'bar',
                data: {
                    labels: barLabels,
                    datasets: [{
                        label: 'Key Events',
                        data: barData,
                        backgroundColor: barColors,
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                label: (context) => `${context.label}: ${context.raw}`
                            }
                        }
                    },
                    scales: {
                        y: { beginAtZero: true }
                    }
                }
            });
        }
    }

    setSupervisorFilter(ev) {
        const value = ev.target.value;
        this.state.filters.supervisor = this.isSupervisor ? this.supervisorName : value;
        this.recomputeSummaries();
        this.updateFilteredData();
        this.updateDashboardCards();
        this.renderChart();
    }

    viewSupervisorDetails(supervisorName) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: `${supervisorName} Team Details`,
            res_model: "crm.lead",
            views: [[false, "list"], [false, "form"]],
            domain: [['supervisor_id.name', '=', supervisorName]],
            context: { search_default_group_by_user: true }
        });
    }
}

SupervisorDashboard.template = "crm_dashboard.SupervisorDashboard";
registry.category("actions").add("supervisor_dashboard_new", SupervisorDashboard);






