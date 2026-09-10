/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, onMounted, useState, useRef } from "@odoo/owl";
import { loadJS } from "@web/core/assets";
import { DateTimePicker } from "@web/core/datetime/datetime_picker";
import { DateTimePickerPopover } from "@web/core/datetime/datetime_picker_popover";
import { DateTimeInput } from "@web/core/datetime/datetime_input";

class TajDashboard extends Component {
    setup() {
        console.log("Initializing WingDashboard component...");
        
        this.orm = useService("orm");
        this.action = useService("action");
        this.user = useService("user");
        this.notification = useService("notification");
        this.chartRef = useRef("chart");

        this.state = useState({
            loading: true,
            detailedSalesPerformance: [],
            wingSummary: [],
            supervisorSummary: [],
            startDate:null,
            endDate:null,
            filters: {
                wing: "",
                supervisor: "",
                dateRange: '30days',
                startDate: '2025-01-01',
                endDate: new Date().toISOString().split('T')[0]
            },
            chart: null,
            isManager: false,
        });

        
        const { DateTime } = luxon;
        this.state.startDate = DateTime.fromObject({ year: 2025, month: 1, day: 1 }).startOf('day');


        onWillStart(async () => {
            console.log("Fetching current user's managed wing...");
            const wings = await this.orm.searchRead(
                'property.wing.config',
                [['manager_id', '=', this.user.id]],
                ['name']
            );
            if (wings.length) {
                this.state.filters.wing = wings[0].name;
                this.state.isManager = true;
                console.log("Manager's wing auto-detected:", wings[0].name);
            } else {
                // Custom fallbacks by user ID
                if (this.user.id === 13) {
                    this.state.filters.wing = "Wing 1";
                    this.state.isManager = true;
                    console.log("User 13 defaulting to Wing 1");
                }
                else if (this.user.id === 15) {
                    this.state.filters.wing = "Wing 2";
                    this.state.isManager = true;
                    console.log("User 15 defaulting to Wing 2");
                } else {
                    console.log("No managed wing found for the user");
                }
            }
            console.log("Loading Chart.js library...");
            await loadJS("/web/static/lib/Chart/Chart.js");
            console.log("Chart.js loaded successfully");
            await this.loadDashboardData();
        });

        onMounted(() => {
            console.log("Component mounted, rendering chart...");
            this.renderChart();
        });
    }

    async loadDashboardData() {
        console.log("Starting data loading...");
        this.state.loading = true;
        
        try {
            console.log("Current filters:", JSON.parse(JSON.stringify(this.state.filters)));
            const startDateFormat =this.state.startDate; // Convert to 'YYYY-MM-DD'
            const endDateFormat = this.state.endDate; // Convert to 'YYYY-MM-DD'
            let startDate = new Date(this.state.filters.startDate);
            const endDate = new Date(this.state.filters.endDate);
            
            // Handle date range presets
            if (this.state.filters.dateRange === '7days') {
                startDate = new Date(endDate);
                startDate.setDate(startDate.getDate() - 7);
            } else if (this.state.filters.dateRange === '30days') {
                startDate = new Date(endDate);
                startDate.setDate(startDate.getDate() - 30);
            } else if (this.state.filters.dateRange === '90days') {
                startDate = new Date(endDate);
                startDate.setDate(startDate.getDate() - 90);
            }
            
            const formattedStartDate = startDate.toISOString().split('T')[0];
            const formattedEndDate = endDate.toISOString().split('T')[0];

            // Validate dates
            if (new Date(formattedStartDate) > new Date(formattedEndDate)) {
                console.error("Invalid date range - start date after end date");
                this.notification.add("Start date cannot be after end date", {
                    type: "danger",
                    title: "Invalid Date Range"
                });
                return;
            }

            console.log("Fetching data with date range:", formattedStartDate, "to", formattedEndDate);
            
            const data = await this.orm.call(
                "crm.lead",
                "get_wing_dashboard_data_taj",
                [formattedStartDate, formattedEndDate],
                {}
            );
            
            console.log("Raw data received from server:", data);
            
            let filteredData = data;
            if (this.state.filters.wing) {
                console.log("Filtering by wing:", this.state.filters.wing);
                filteredData = filteredData.filter(row => row.wing_name === this.state.filters.wing);
            }
            // apply multi supervisor filter
            const supFilter = this.state.filters.supervisor;
            if (Array.isArray(supFilter) && supFilter.length) {
                filteredData = filteredData.filter(r => supFilter.includes(r.supervisor_name));
            } else if (supFilter) {
                filteredData = filteredData.filter(r => r.supervisor_name === supFilter);
            }
            
            console.log("Data after filtering:", filteredData);
            
            const transformedData = filteredData.map(row => ({
                wing_name: row.wing_name,
                wing_manager_name: row.wing_manager_name,
                supervisor_name: row.supervisor_name,
                sales_person: row.sales_person,
                prospect_count: row.prospect || 0,
                follow_up_count: row.follow_up || 0,
                won_count: row.won || 0,
                expired_count: row.expired || 0,
                reservation_count: row.reservation_count || 0,
                sold_reservation_count: row.sold_reservation_count || 0,
                data_flag: row.data_flag || '✅ OK'
            }));
            
            console.log("Transformed data:", transformedData);
            
            this.state.detailedSalesPerformance = transformedData;
            this.processSummaryData(transformedData);
            this.renderChart();
        } catch (err) {
            console.error("Error loading data:", err);
            this.notification.add("Failed to load dashboard data", {
                type: "danger",
                title: "Error"
            });
            // Clear data on error
            this.state.detailedSalesPerformance = [];
            this.state.wingSummary = [];
            this.state.supervisorSummary = [];
            this.renderChart();
        } finally {
            this.state.loading = false;
            console.log("Data loading completed");
        }
    }

    processSummaryData(data) {
        console.log("Processing summary data - input:", data);
        
        const wingMap = new Map();
        const supervisorMap = new Map();

        data.forEach(row => {
            if (!row.wing_name) {
                console.warn("Row missing wing_name:", row);
                return;
            }

            // Process wing summary
            const wing = wingMap.get(row.wing_name) || { 
                name: row.wing_name,
                totalLeads: 0,
                supervisors: new Set(),
                totalWon: 0,
                totalExpired: 0,
                totalProspect: 0,
                totalReservation: 0,
                has_issue: row.data_flag?.includes('Missing') || false
            };

            wing.totalLeads += (row.won_count || 0) + (row.expired_count || 0) + 
                             (row.prospect_count || 0) + (row.reservation_count || 0);
            wing.totalWon += row.won_count || 0;
            wing.totalExpired += row.expired_count || 0;
            wing.totalProspect += row.prospect_count || 0;
            wing.totalReservation += row.reservation_count || 0;
            wing.supervisors.add(row.supervisor_name);
            wingMap.set(row.wing_name, wing);

            // Process supervisor summary
            if (row.supervisor_name) {
                const supervisorKey = row.supervisor_name;
                const supervisor = supervisorMap.get(supervisorKey) || { 
                    name: supervisorKey,
                    totalLeads: 0,
                    wing_name: row.wing_name,
                    totalWon: 0,
                    totalExpired: 0,
                    totalProspect: 0,
                    totalReservation: 0
                };
                supervisor.totalLeads += (row.won_count || 0) + (row.expired_count || 0) + 
                                       (row.prospect_count || 0) + (row.reservation_count || 0);
                supervisor.totalWon += row.won_count || 0;
                supervisor.totalExpired += row.expired_count || 0;
                supervisor.totalProspect += row.prospect_count || 0;
                supervisor.totalReservation += row.reservation_count || 0;
                supervisorMap.set(supervisorKey, supervisor);
            }
        });

        this.state.wingSummary = Array.from(wingMap.values()).map(w => ({
            ...w,
            supervisors: w.supervisors.size
        }));

        this.state.supervisorSummary = Array.from(supervisorMap.values());

        console.log("Generated wing summary:", this.state.wingSummary);
        console.log("Generated supervisor summary:", this.state.supervisorSummary);
    }

    renderChart() {
        console.log("Attempting to render chart...");
        
        if (this.state.chart) {
            console.log("Destroying existing chart...");
            this.state.chart.destroy();
        }
        
        if (!this.chartRef.el) {
            console.error("Chart canvas element not found!");
            return;
        }

        console.log("Preparing chart data...");
        const ctx = this.chartRef.el.getContext('2d');
        const labels = ['Won', 'Expired', 'Prospect', 'Reservation', 'Follow Up'];
        
        const data = [
            this.sumByCategory('won_count'),
            this.sumByCategory('expired_count'),
            this.sumByCategory('prospect_count'),
            this.sumByCategory('reservation_count'),
            this.sumByCategory('follow_up_count')
        ];

        console.log("Chart data prepared:", { labels, data });

        try {
            this.state.chart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels,
                    datasets: [{
                        label: 'Leads by Status',
                        data,
                        backgroundColor: [
                            '#28a745', '#dc3545', '#007bff', '#17a2b8', '#ffc107'
                        ]
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                }
            });
            console.log("Chart rendered successfully");
        } catch (error) {
            console.error("Error rendering chart:", error);
        }
    }

    sumByCategory(field) {
        const sum = this.state.detailedSalesPerformance.reduce(
            (sum, row) => sum + (row[field] || 0), 
            0
        );
        console.log(`Sum for ${field}:`, sum);
        return sum;
    }


setWingFilter = (ev) => {
    const wing = ev.target.value;
    this.state.filters.supervisor = "";
    this.setFilter('wing', wing);
};

setSupervisorFilter = (ev) => {
    // collect all selected supervisors
    const selected = Array.from(ev.target.selectedOptions).map(opt => opt.value);
    this.setFilter('supervisor', selected);
};


    setFilter = (type, value) => {
        this.state.filters[type] = value;
        if (type === 'dateRange') {
            const endDate = new Date();
            let startDate = new Date(endDate);
            if (value === '7days') startDate.setDate(endDate.getDate() - 7);
            else if (value === '30days') startDate.setDate(endDate.getDate() - 30);
            else if (value === '90days') startDate.setDate(endDate.getDate() - 90);
            this.state.filters.startDate = startDate.toISOString().split('T')[0];
            this.state.filters.endDate = endDate.toISOString().split('T')[0];
        }
        this.loadDashboardData();
    };

    openRelatedSales(salesPerson, stage = null) {
        console.log(`Opening related sales for ${salesPerson}`, stage ? `(stage: ${stage})` : '');
        const domain = [["user_id.name", "=", salesPerson]];
        if (stage) {
            domain.push(["stage_id.name", "=", stage]);
        }

        

        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "crm.lead",
            domain,
            view_mode: "list",
            views: [[false, "list"]],
            context: { search_default_group_by_stage_id: true },
        });
    }
    async set_date_from(date) {
        this.state.startDate=date
        await this.loadDashboardData()
    }
    async set_date_to(date) {
            this.state.endDate=date
            await this.loadDashboardData()
    
        }
}

// Register DateTimeInput and related components for template usage
TajDashboard.components = { DateTimePicker, DateTimePickerPopover, DateTimeInput };

TajDashboard.template = "team_dashboard.wing_dashboard_jjokachabc";
registry.category("actions").add("wing_dashboard_jjokachabc", TajDashboard);