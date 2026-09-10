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
                supervisor: null,
                dateRange: '30days'
            },
            chart: null
        });
        this.isSupervisor = false;
        this.supervisorName = null;

        onWillStart(async () => {
            await loadJS("/web/static/lib/Chart/Chart.js");
            // Check if user is supervisor and get their name
            this.isSupervisor = await this.user.hasGroup('property_sales.access_property_sales_supervisor_group');
            if (this.isSupervisor) {
                const userData = await this.orm.searchRead(
                    "res.users",
                    [['id', '=', this.user.userId]],
                    ['partner_id']
                );
                if (userData.length) {
                    this.supervisorName = userData[0].partner_id[1];
                    // Set default supervisor filter for supervisors
                    this.state.filters.supervisor = this.supervisorName;
                }
            }
            await this.loadDashboardData();
        });

        onMounted(() => {
            if (this.chartRef.el) {
                this.renderChart();
            }
        });
    }

    async loadDashboardData() {
        try {
            this.state.loading = true;
            const results = await this.orm.call(
                'crm.lead',
                'get_supervisor_dashboard_data',
                [this.getDateCondition()],
                {}
            );
            this.processDashboardData(results);
        } catch (error) {
            console.error("Error loading dashboard data:", error);
        } finally {
            this.state.loading = false;
        }
    }

    getDateCondition() {
        switch(this.state.filters.dateRange) {
            case '30days': return '30days';
            case '90days': return '90days';
            case 'alltime': return 'alltime';
            default: return '30days';
        }
    }

    processDashboardData(results) {
        // If supervisor, only show their team and salespersons
        let filteredResults = results;
        if (this.isSupervisor && this.supervisorName) {
            filteredResults = results.filter(row =>
                row.supervisor_name === this.supervisorName
            );
        }
        this.state.rawData = filteredResults;
        this.state.eventTypes = [...new Set(filteredResults.map(row => row.event_type))];
        this.recomputeSummaries();
        this.updateFilteredData();
        this.updateDashboardCards(); // <-- add this
        this.renderChart();
    }

    recomputeSummaries() {
        // Filter rawData according to current filters
        const filtered = this.state.rawData.filter(row =>
            (!this.state.filters.wing || row.wing_name === this.state.filters.wing) &&
            (!this.state.filters.supervisor || row.supervisor_name === this.state.filters.supervisor)
        );

        // Wing summary
        const wingMap = new Map();
        // Supervisor summary
        const supervisorMap = new Map();

        filtered.forEach(row => {
            // Wing summary
            if (!wingMap.has(row.wing_name)) {
                wingMap.set(row.wing_name, {
                    name: row.wing_name,
                    totalLeads: 0,
                    keyEvents: 0,
                    supervisors: new Set(),
                    salesPersons: new Set()
                });
            }
            const wing = wingMap.get(row.wing_name);
            wing.totalLeads += row.count;
            if (['Reservation', 'Won', 'Expired'].includes(row.event_type)) {
                wing.keyEvents += row.count;
            }
            wing.supervisors.add(row.supervisor_name);
            wing.salesPersons.add(row.sales_person);

            // Supervisor summary
            const supervisorKey = `${row.wing_name}|${row.supervisor_name}`;
            if (!supervisorMap.has(supervisorKey)) {
                supervisorMap.set(supervisorKey, {
                    wing: row.wing_name,
                    name: row.supervisor_name,
                    totalLeads: 0,
                    keyEvents: 0,
                    salesPersons: new Set()
                });
            }
            const supervisor = supervisorMap.get(supervisorKey);
            supervisor.totalLeads += row.count;
            if (['Reservation', 'Won', 'Expired'].includes(row.event_type)) {
                supervisor.keyEvents += row.count;
            }
            supervisor.salesPersons.add(row.sales_person);
        });

        this.state.wingSummary = Array.from(wingMap.values()).map(wing => ({
            ...wing,
            supervisors: wing.supervisors.size,
            salesPersons: wing.salesPersons.size
        }));

        this.state.supervisorSummary = Array.from(supervisorMap.values()).map(supervisor => ({
            ...supervisor,
            salesPersons: supervisor.salesPersons.size
        }));
    }

    updateDashboardCards(filteredData) {
        // Use filteredData if provided, else use filtered by current filters
        const data = filteredData || this.state.rawData.filter(row =>
            (!this.state.filters.wing || row.wing_name === this.state.filters.wing) &&
            (!this.state.filters.supervisor || row.supervisor_name === this.state.filters.supervisor)
        );
        this.state.totalLeads = data.reduce((a, b) => a + b.count, 0);
        this.state.totalKeyEvents = data.filter(r => ['Reservation','Won','Expired'].includes(r.event_type)).reduce((a, b) => a + b.count, 0);
        this.state.uniqueSalesPersons = Array.from(new Set(data.map(r => r.sales_person)));
        this.state.uniqueSupervisors = Array.from(new Set(data.map(r => r.supervisor_name)));
    }

    updateFilteredData() {
        // Filter detailed sales person data according to current filters
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

    // Helper Functions
    getEventCount(eventType) {
        return this.state.rawData
            .filter(row => row.event_type === eventType)
            .reduce((total, row) => total + row.count, 0);
    }

    getTopPerformers() {
        const salesPersonMap = {};
        
        this.state.rawData.forEach(row => {
            if (!salesPersonMap[row.sales_person]) {
                salesPersonMap[row.sales_person] = {
                    name: row.sales_person,
                    totalLeads: 0,
                    keyEvents: 0
                };
            }
            salesPersonMap[row.sales_person].totalLeads += row.count;
            if (['Reservation', 'Won', 'Expired'].includes(row.event_type)) {
                salesPersonMap[row.sales_person].keyEvents += row.count;
            }
        });
        
        return Object.values(salesPersonMap)
            .map(sp => ({
                ...sp,
                conversion: sp.totalLeads ? Math.round((sp.keyEvents / sp.totalLeads) * 100) : 0
            }))
            .sort((a, b) => b.keyEvents - a.keyEvents)
            .slice(0, 5);
    }

    getEventColor(eventType) {
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
    }

    // Filter handlers
    setWingFilter = (ev) => {
        const value = ev.target.value;
        this.state.filters.wing = value;
        if (this.isSupervisor && this.supervisorName) {
            this.state.filters.supervisor = this.supervisorName;
        } else {
            this.state.filters.supervisor = null;
        }
        this.recomputeSummaries();
        this.updateFilteredData();
        this.renderChart();
    }

    setSupervisorFilter = (ev) => {
        const value = ev.target.value;
        if (this.isSupervisor && this.supervisorName) {
            this.state.filters.supervisor = this.supervisorName;
        } else {
            this.state.filters.supervisor = value;
        }
        this.recomputeSummaries();
        this.updateFilteredData();
        this.renderChart();
    }

    setDateFilter = (evOrValue) => {
        // Accept both event and direct value for flexibility
        let value;
        if (evOrValue && evOrValue.target) {
            value = evOrValue.target.value;
        } else {
            value = evOrValue;
        }
        this.state.filters.dateRange = value;
        this.loadDashboardData();
    }

    viewSupervisorDetails = (supervisorName) => {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: `${supervisorName} Team Details`,
            res_model: "crm.lead",
            views: [[false, "list"], [false, "form"]],
            domain: [
                ['supervisor_id.name', '=', supervisorName],
                ['create_date', '>=', this.getStartDate()],
                ['create_date', '<=', this.getEndDate()]
            ],
            context: {
                search_default_group_by_user: true,
                search_default_filter_my_team: true
            }
        });
    }
    
    getStartDate() {
        switch(this.state.filters.dateRange) {
            case '30days': return new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
            case '90days': return new Date(Date.now() - 90 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
            default: return false;
        }
    }
    
    getEndDate() {
        return new Date().toISOString().split('T')[0];
    }
}

SupervisorDashboard.template = "crm_dashboard.SupervisorDashboard";
registry.category("actions").add("supervisor_dashboard", SupervisorDashboard);