/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, onMounted, useState, useRef } from "@odoo/owl";
import { loadJS } from "@web/core/assets";

class TeamRahaDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.user = useService("user");
        this.chartRef = useRef("chart");
        this.pieChartRef = useRef("pieChart");
        this.funnelChartRef = useRef("funnelChart");

        this.state = useState({
            loading: true,
            dashboardData: [],
            allSupervisors: [],
            filteredData: [],
            filters: {
                date_from: '',
                date_to: '',
                supervisor_id: null,
            },
            totals: {
                prospects: 0,
                follow_ups: 0,
                reservations: 0,
                won: 0,
                expired: 0,
                sold_reservations: 0,
                leads_count: 0 // Added leads_count
            },
            originalTotals: {
                prospects: 0,
                follow_ups: 0,
                reservations: 0,
                won: 0,
                expired: 0,
                sold_reservations: 0,
                leads_count: 0 // Added leads_count
            },
            chart: null,
            pieChart: null,
            funnelChart: null,
            showSupervisorTotals: false,
            errorMessage: null
        });

        onWillStart(async () => {
            try {
                await loadJS("/web/static/lib/Chart/Chart.js");
                console.log('Chart.js loaded successfully');
                
                const today = new Date();
                const yearStart = new Date(today.getFullYear(), 0, 1);

                const formatDate = (date) => {
                    const yyyy = date.getFullYear();
                    const mm = String(date.getMonth() + 1).padStart(2, '0');
                    const dd = String(date.getDate()).padStart(2, '0');
                    return `${yyyy}-${mm}-${dd}`;
                };

                this.state.filters.date_from = formatDate(yearStart);
                this.state.filters.date_to = formatDate(today);

                await this.loadDashboardData();
            } catch (error) {
                console.error('Failed to initialize dashboard:', error);
                this.state.errorMessage = `Failed to initialize dashboard: ${error.message}`;
                this.state.loading = false;
            }
        });

        onMounted(() => {
            this.renderChartsWithRetry();
        });
    }

    cleanSupervisorName(name) {
        try {
            const strName = typeof name === 'string' ? name : String(name || '');
            const cleanedName = strName.includes(',') ? strName.split(',')[1].trim() : strName;
            return typeof cleanedName === 'string' 
                ? cleanedName.replace('(Team Total)', '').trim() 
                : 'No Supervisor';
        } catch (error) {
            console.error('Error cleaning supervisor name:', error, 'Original name:', name);
            return 'No Supervisor';
        }
    }

    renderChartsWithRetry(attempt = 0) {
        if (attempt > 3) {
            console.error('Failed to render charts after multiple attempts');
            return;
        }

        if (!this.chartRef.el || !this.pieChartRef.el) {
            console.warn(`Chart containers not found (attempt ${attempt + 1}), retrying...`);
            setTimeout(() => this.renderChartsWithRetry(attempt + 1), 500);
            return;
        }

        this.renderCharts();
    }

    renderCharts() {
        try {
            if (this.state.chart) {
                this.state.chart.destroy();
                this.state.chart = null;
            }
            if (this.state.pieChart) {
                this.state.pieChart.destroy();
                this.state.pieChart = null;
            }
            if (this.state.funnelChart) {
                this.state.funnelChart.destroy();
                this.state.funnelChart = null;
            }

            this.renderBarChart();
            this.renderPieChart();
            this.renderFunnelChart();
        } catch (error) {
            console.error('Error in renderCharts:', error);
        }
    }

    renderBarChart() {
        try {
            if (!this.chartRef.el) {
                console.warn('Bar chart container not found in DOM');
                return;
            }

            const ctx = this.chartRef.el.getContext('2d');
            if (!ctx) {
                console.warn('Could not get 2D context for bar chart');
                return;
            }

            const labels = ['Leads', 'Prospects', 'Follow Ups', 'Reservations', 'Sold', 'Expired'];
            const data = [
                this.state.totals.leads_count,
                this.state.totals.prospects,
                this.state.totals.follow_ups,
                this.state.totals.reservations,
                this.state.totals.won,
                this.state.totals.expired
            ];

            this.state.chart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Lead Status Count',
                        data: data,
                        backgroundColor: [
                            'rgba(153, 102, 255, 0.7)', // Color for leads_count
                            'rgba(54, 162, 235, 0.7)',
                            'rgba(255, 206, 86, 0.7)',
                            'rgba(75, 192, 192, 0.7)',
                            'rgba(75, 192, 75, 0.7)',
                            'rgba(255, 99, 132, 0.7)'
                        ],
                        borderColor: [
                            'rgba(153, 102, 255, 1)',
                            'rgba(54, 162, 235, 1)',
                            'rgba(255, 206, 86, 1)',
                            'rgba(75, 192, 192, 1)',
                            'rgba(75, 192, 75, 1)',
                            'rgba(255, 99, 132, 1)'
                        ],
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        title: {
                            display: true,
                            text: 'Team Raha - Lead Status Distribution'
                        },
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Number of Leads'
                            }
                        },
                        x: {
                            title: {
                                display: true,
                                text: 'Lead Status'
                            }
                        }
                    }
                }
            });
        } catch (error) {
            console.error('Error rendering bar chart:', error);
        }
    }

    renderPieChart() {
        try {
            if (!this.pieChartRef.el) {
                console.warn('Pie chart container not found in DOM');
                return;
            }

            const ctx = this.pieChartRef.el.getContext('2d');
            if (!ctx) {
                console.warn('Could not get 2D context for pie chart');
                return;
            }

            const labels = ['Prospects', 'Follow Ups', 'Reservations', 'Sold', 'Expired'];
            const data = [
                this.state.totals.prospects,
                this.state.totals.follow_ups,
                this.state.totals.reservations,
                this.state.totals.won,
                this.state.totals.expired
            ];

            this.state.pieChart = new Chart(ctx, {
                type: 'pie',
                data: {
                    labels: labels,
                    datasets: [{
                        data: data,
                        backgroundColor: [
                            'rgba(54, 162, 235, 1)',
                            'rgba(255, 206, 86, 1)',
                            'rgba(75, 192, 192, 1)',
                            'rgba(75, 192, 75, 1)',
                            'rgba(255, 99, 132, 1)'
                        ],
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        title: {
                            display: true,
                            text: 'Team Raha - Lead Status Distribution (Pie)'
                        },
                        legend: {
                            position: 'right'
                        }
                    }
                }
            });
        } catch (error) {
            console.error('Error rendering pie chart:', error);
        }
    }

    renderFunnelChart() {
        // Placeholder for funnel chart if needed
    }

    async loadDashboardData() {
        console.log("Loading dashboard data...");
        this.state.loading = true;
        this.state.errorMessage = null;
        try {
            const { date_from, date_to } = this.state.filters;

            if (!date_from) {
                throw new Error("Start date is required");
            }

            const endDate = date_to || new Date().toISOString().split('T')[0];
            console.log("Fetching data for date range:", date_from, "to", endDate);

            let leads = await this.orm.call(
                'crm.lead',
                'search_read',
                [[
                    ['create_date', '>=', date_from],
                    ['create_date', '<=', endDate]
                ]],
                { fields: ['id', 'create_date', 'stage_id', 'user_id', 'supervisor_id', 'wing_id'] }
            );

            const stageIds = [...new Set(leads.map(l => l.stage_id ? l.stage_id[0] : null).filter(id => id))];
            let stages = stageIds.length ? await this.orm.call('crm.stage', 'search_read', [[['id', 'in', stageIds]]], { fields: ['id', 'name'] }) : [];
            const stageMap = new Map(stages.map(s => [s.id, s.name || 'Unknown Stage']));

            let reservations = await this.orm.call(
                'property.reservation',
                'search_read',
                [[
                    ['create_date', '>=', date_from],
                    ['create_date', '<=', endDate]
                ]],
                { fields: ['id', 'crm_lead_id', 'status', 'create_date'] }
            );

            const userIds = [...new Set(leads.map(l => l.user_id ? l.user_id[0] : null).filter(id => id))];
            const supervisorIds = [...new Set(leads.map(l => l.supervisor_id ? l.supervisor_id[0] : null).filter(id => id))];
            const wingIds = [...new Set(leads.map(l => l.wing_id ? l.wing_id[0] : null).filter(id => id))];

            let users = userIds.length ? await this.orm.call('res.users', 'search_read', [[['id', 'in', userIds]]], { fields: ['id', 'name'] }) : [];
            let supervisors = supervisorIds.length ? await this.orm.call('property.sales.supervisor', 'search_read', [[['id', 'in', supervisorIds]]], { fields: ['id', 'name'] }) : [];
            let wings = wingIds.length ? await this.orm.call('property.sales.wing', 'search_read', [[['id', 'in', wingIds]]], { fields: ['id', 'name'] }) : [];
            
            const userMap = new Map(users.map(u => [u.id, u.name || 'Unknown User']));
            const supervisorMap = new Map(supervisors.map(s => [s.id, s.name || 'Unknown Supervisor']));
            const wingMap = new Map(wings.map(w => [w.id, w.name || 'Unknown Wing']));

            const filteredLeads = leads.filter(lead => wingMap.get(lead.wing_id ? lead.wing_id[0] : 0) === 'Team - Raha');

            const leadEvents = filteredLeads.map(lead => {
                let event_type = null;
                const stageName = lead.stage_id ? (stageMap.get(lead.stage_id[0]) || '').toLowerCase() : '';
                if (stageName) {
                    if (stageName.includes('expired')) event_type = 'Expired';
                    else if (stageName.includes('won')) event_type = 'Won';
                    else if (stageName.includes('reservation')) event_type = 'Reservation';
                    else if (stageName.includes('follow')) event_type = 'Follow Up';
                    else if (stageName.includes('prospect')) event_type = 'Prospect';
                }
                return {
                    lead_id: lead.id,
                    sales_person: lead.user_id ? userMap.get(lead.user_id[0]) || 'No Sales Person' : 'No Sales Person',
                    supervisor_name: lead.supervisor_id ? this.cleanSupervisorName(supervisorMap.get(lead.supervisor_id[0])) || 'No Supervisor' : 'No Supervisor',
                    supervisor_id: lead.supervisor_id ? lead.supervisor_id[0] : 0,
                    wing_name: lead.wing_id ? wingMap.get(lead.wing_id[0]) || 'Team - Raha' : 'Team - Raha',
                    wing_manager_name: '',
                    event_type
                };
            });

            const activityEvents = filteredLeads
                .filter(lead => lead.stage_id && stageMap.get(lead.stage_id[0])?.toLowerCase().includes('won'))
                .map(lead => ({
                    lead_id: lead.id,
                    sales_person: lead.user_id ? userMap.get(lead.user_id[0]) || 'No Sales Person' : 'No Sales Person',
                    supervisor_name: lead.supervisor_id ? this.cleanSupervisorName(supervisorMap.get(lead.supervisor_id[0])) || 'No Supervisor' : 'No Supervisor',
                    supervisor_id: lead.supervisor_id ? lead.supervisor_id[0] : 0,
                    wing_name: lead.wing_id ? wingMap.get(lead.wing_id[0]) || 'Team - Raha' : 'Team - Raha',
                    wing_manager_name: '',
                    event_type: 'Won'
                }));

            const unionedEvents = [...leadEvents, ...activityEvents];

            const eventCounts = {};
            unionedEvents.forEach(event => {
                const key = `${event.wing_name}|${event.wing_manager_name}|${event.supervisor_name}|${event.sales_person}`;
                if (!eventCounts[key]) {
                    eventCounts[key] = {
                        wing_name: event.wing_name,
                        wing_manager_name: event.wing_manager_name,
                        supervisor_name: event.supervisor_name || 'No Supervisor',
                        supervisor_id: event.supervisor_id,
                        sales_person: event.sales_person,
                        prospect: 0,
                        follow_up: 0,
                        won: 0,
                        expired: 0
                    };
                }
                if (event.event_type === 'Prospect') eventCounts[key].prospect += 1;
                if (event.event_type === 'Follow Up') eventCounts[key].follow_up += 1;
                if (event.event_type === 'Won') eventCounts[key].won += 1;
                if (event.event_type === 'Expired') eventCounts[key].expired += 1;
            });

            const reservationCounts = {};
            reservations.forEach(res => {
                const lead = filteredLeads.find(l => l.id === (res.crm_lead_id ? res.crm_lead_id[0] : null));
                if (!lead) return;
                const key = `${lead.wing_id ? wingMap.get(lead.wing_id[0]) || 'Team - Raha' : 'Team - Raha'}||${lead.supervisor_id ? this.cleanSupervisorName(supervisorMap.get(lead.supervisor_id[0])) || 'No Supervisor' : 'No Supervisor'}|${lead.user_id ? userMap.get(lead.user_id[0]) || 'No Sales Person' : 'No Sales Person'}`;
                if (!reservationCounts[key]) {
                    reservationCounts[key] = {
                        wing_name: lead.wing_id ? wingMap.get(lead.wing_id[0]) || 'Team - Raha' : 'Team - Raha',
                        wing_manager_name: '',
                        supervisor_name: lead.supervisor_id ? this.cleanSupervisorName(supervisorMap.get(lead.supervisor_id[0])) || 'No Supervisor' : 'No Supervisor',
                        supervisor_id: lead.supervisor_id ? lead.supervisor_id[0] : 0,
                        sales_person: lead.user_id ? userMap.get(lead.user_id[0]) || 'No Sales Person' : 'No Sales Person',
                        reservation_count: 0,
                        sold_reservation_count: 0
                    };
                }
                reservationCounts[key].reservation_count += 1;
                if (res.status === 'sold') reservationCounts[key].sold_reservation_count += 1;
            });

            const data = [];
            const allKeys = new Set([...Object.keys(eventCounts), ...Object.keys(reservationCounts)]);
            allKeys.forEach(key => {
                const ec = eventCounts[key] || {};
                const rc = reservationCounts[key] || {};
                const record = {
                    wing_name: String(ec.wing_name || rc.wing_name || 'Team - Raha'),
                    wing_manager_name: String(ec.wing_manager_name || rc.wing_manager_name || ''),
                    supervisor_name: this.cleanSupervisorName(String(ec.supervisor_name || rc.supervisor_name || 'No Supervisor')),
                    supervisor_id: ec.supervisor_id || rc.supervisor_id || 0,
                    sales_person: String(ec.sales_person || rc.sales_person || 'No Sales Person'),
                    prospect: ec.prospect || 0,
                    follow_up: ec.follow_up || 0,
                    won: ec.won || 0,
                    expired: ec.expired || 0,
                    reservation_count: rc.reservation_count || 0,
                    sold_reservation_count: rc.sold_reservation_count || 0,
                    leads_count: (ec.prospect || 0) + (ec.follow_up || 0) + (rc.reservation_count || 0) + (ec.won || 0) + (ec.expired || 0),
                    data_flag: (ec.wing_name === 'No Wing' || rc.wing_name === 'No Wing') && (ec.wing_manager_name || rc.wing_manager_name) ? '🟡 Missing wing_name' : '✅ OK'
                };
                data.push(record);
            });

            data.sort((a, b) => {
                try {
                    if (a.data_flag !== b.data_flag) return a.data_flag === '✅ OK' ? -1 : 1;
                    const wingA = String(a.wing_name || '');
                    const wingB = String(b.wing_name || '');
                    if (wingA !== wingB) return wingA.localeCompare(wingB);
                    const supA = String(a.supervisor_name || '');
                    const supB = String(b.supervisor_name || '');
                    if (supA !== supB) return supA.localeCompare(supB);
                    const salesA = String(a.sales_person || '');
                    const salesB = String(b.sales_person || '');
                    return salesA.localeCompare(salesB);
                } catch (error) {
                    console.error("Error during sorting:", error, { a, b });
                    return 0;
                }
            });

            const supervisorSet = new Map();
            data.forEach(item => {
                const supId = item.supervisor_id || 0;
                if (!supervisorSet.has(supId)) {
                    supervisorSet.set(supId, {
                        id: supId,
                        name: this.cleanSupervisorName(String(item.supervisor_name || 'No Supervisor'))
                    });
                }
            });

            this.state.allSupervisors = Array.from(supervisorSet.values());

            const totals = {
                prospects: 0,
                follow_ups: 0,
                reservations: 0,
                won: 0,
                expired: 0,
                sold_reservations: 0,
                leads_count: 0
            };

            const filteredData = data.map(record => {
                const row_sum = record.prospect + record.follow_up + record.reservation_count + record.won + record.expired + record.sold_reservation_count;
                return { ...record, row_sum };
            });

            filteredData.forEach(record => {
                totals.prospects += record.prospect;
                totals.follow_ups += record.follow_up;
                totals.reservations += record.reservation_count;
                totals.won += record.won;
                totals.expired += record.expired;
                totals.sold_reservations += record.sold_reservation_count;
                totals.leads_count += record.leads_count;
            });

            this.state.dashboardData = filteredData;
            this.state.filteredData = filteredData;
            this.state.totals = totals;
            this.state.originalTotals = { ...totals };

            if (filteredData.length === 0) {
                this.state.errorMessage = "No data found for the selected date range and filters.";
            }

            this.applyFilters();
        } catch (error) {
            console.error("Error loading dashboard data:", error);
            this.state.errorMessage = `Error loading data: ${error.message}`;
        } finally {
            this.state.loading = false;
            this.renderCharts();
        }
    }

    applyFilters() {
        let filteredData = [...this.state.dashboardData];
        
        if (this.state.filters.supervisor_id) {
            filteredData = filteredData.filter(
                item => item.supervisor_id === this.state.filters.supervisor_id
            );
        }
        
        const filteredTotals = {
            prospects: 0,
            follow_ups: 0,
            reservations: 0,
            won: 0,
            expired: 0,
            sold_reservations: 0,
            leads_count: 0
        };
        
        filteredData.forEach(record => {
            filteredTotals.prospects += record.prospect;
            filteredTotals.follow_ups += record.follow_up;
            filteredTotals.reservations += record.reservation_count;
            filteredTotals.won += record.won;
            filteredTotals.expired += record.expired;
            filteredTotals.sold_reservations += record.sold_reservation_count;
            filteredTotals.leads_count += record.leads_count;
        });
        
        this.state.filteredData = filteredData;
        this.state.totals = filteredTotals;
        
        if (this.state.filters.supervisor_id) {
            this.state.showSupervisorTotals = true;
        } else {
            this.state.showSupervisorTotals = false;
        }
    }

    onDateChange(ev) {
        const { name, value } = ev.target;
        this.state.filters[name] = value;
        if (this.state.filters.date_from && this.state.filters.date_to) {
            if (new Date(this.state.filters.date_from) > new Date(this.state.filters.date_to)) {
                this.state.errorMessage = "Start date cannot be after end date";
                return;
            }
            this.state.errorMessage = null;
            this.loadDashboardData();
        }
    }

    setSupervisorFilter(ev) {
        const value = ev.target.value === "0" ? null : parseInt(ev.target.value);
        this.state.filters.supervisor_id = value;
        this.applyFilters();
        this.renderCharts();
    }

    toggleSupervisorTotals() {
        this.state.showSupervisorTotals = !this.state.showSupervisorTotals;
    }

    getSupervisorGroups() {
        const groups = {};
        this.state.filteredData.forEach(record => {
            const supervisorId = record.supervisor_id || 'none';
            const supervisorName = this.cleanSupervisorName(String(record.supervisor_name || 'No Supervisor'));
            
            if (!groups[supervisorId]) {
                groups[supervisorId] = {
                    name: supervisorName,
                    rows: [],
                    totals: {
                        prospect: 0,
                        follow_up: 0,
                        reservation_count: 0,
                        won: 0,
                        expired: 0,
                        sold_reservation_count: 0,
                        leads_count: 0,
                        row_sum: 0
                    }
                };
            }
            
            groups[supervisorId].rows.push(record);
            groups[supervisorId].totals.prospect += record.prospect;
            groups[supervisorId].totals.follow_up += record.follow_up;
            groups[supervisorId].totals.reservation_count += record.reservation_count;
            groups[supervisorId].totals.won += record.won;
            groups[supervisorId].totals.expired += record.expired;
            groups[supervisorId].totals.sold_reservation_count += record.sold_reservation_count;
            groups[supervisorId].totals.leads_count += record.leads_count;
            groups[supervisorId].totals.row_sum += record.row_sum;
        });
        
        return groups;
    }

    getSupervisorSummary() {
        const summary = [];
        const supervisorGroups = this.getSupervisorGroups();
        
        Object.entries(supervisorGroups).forEach(([id, group]) => {
            const conversionRate = group.totals.reservation_count 
                ? Math.round((group.totals.won / group.totals.reservation_count) * 100)
                : 0;
                
            summary.push({
                id: id === 'none' ? 0 : parseInt(id),
                name: group.name,
                team_size: group.rows.length,
                prospects: group.totals.prospect,
                follow_ups: group.totals.follow_up,
                reservations: group.totals.reservation_count,
                won: group.totals.won,
                expired: group.totals.expired,
                sold_reservations: group.totals.sold_reservation_count,
                leads_count: group.totals.leads_count,
                conversion_rate: conversionRate
            });
        });
        
        return summary.sort((a, b) => String(a.name || '').localeCompare(String(b.name || '')));
    }

    setSupervisorFilterFromLink(supervisorId) {
        this.state.filters.supervisor_id = supervisorId === 0 ? null : supervisorId;
        this.applyFilters();
        this.renderCharts();
        
        const dashboardEl = document.querySelector('.o_team_raha_dashboard');
        if (dashboardEl) {
            dashboardEl.scrollTo({ top: 0, behavior: 'smooth' });
        }
    }

    viewSalesPersonLeads(salesPerson, eventType) {
        let domain = [["user_id.name", "=", salesPerson]];
        if (eventType && eventType !== 'Leads') {
            domain.push(["stage_id.name", "ilike", eventType]);
        }
        
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "crm.lead",
            domain: domain,
            views: [[false, "list"], [false, "form"]],
            context: {
                search_default_group_by_stage_id: true,
            },
        });
    }
}

TeamRahaDashboard.template = "team_dashboard.TeamRahaDashboardTemplate";
registry.category("actions").add("TeamRahaDashboardTemplate", TeamRahaDashboard);