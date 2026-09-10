/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useRef, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { loadJS } from "@web/core/assets";
import { getColor } from "@web/core/colors/colors";

const actionRegistry = registry.category("actions");

export class ChartjsSampleCRM extends Component {
    getDefaultStartDate() {
        const date = new Date();
        date.setDate(date.getDate() - 30); // Go back 30 days
        return date.toISOString().split('T')[0]; // Format as YYYY-MM-DD
    }

    getDefaultEndDate() {
        const date = new Date();
        return date.toISOString().split('T')[0]; // Format as YYYY-MM-DD
    }

    setup() {
        this.orm = useService('orm');
        this.action = useService("action");
        this.user = useService("user");
        
        // State management
        this.searchQuery = useState({ value: "" });
        this.dateFilters = useState({
            startDate: this.getDefaultStartDate(),
            endDate: this.getDefaultEndDate()
        });
        this.stats = useState({
            totalCallCenterLeads: 0,
            totalReceptionLeads: 0,
            totalSoldProperties: 0, 
            totalWebsiteLeads: 0,
            totalOtherLeads: 0,
            totalAllLeads: 0,
            wingLeads: {},
            supervisorLeads: {},
            totalReservations: 0,
            reservationDataByStatus: [],
            callCenterData: [],
            receptionDataByStage: [],
            receptionData: [],
            leadDataBySource: [],
            leadDataByStage: [],
            activityTypeData: [],
            websiteLeadDataByStage: [],
            activityCounts: {
                email: 0,
                call: 0,
                meeting: 0,
                todo: 0,
                upload: 0
            },
            isSupervisor: false,
            currentSupervisorId: null,
            currentWingId: null,
            userId: null, // Add userId to state
            userLeads: 0, // Add userLeads count
            userProspects: 0, // Add userProspects count
            userActivities: 0 // Add userActivities count
        });

        // Chart references
        this.barChartRef = useRef("barChart");
        this.pieChartRef = useRef("pieChart");
        this.receptionBarChartRef = useRef("receptionBarChart");
        this.receptionPieChartRef = useRef("receptionPieChart");
        this.sourceChartRef = useRef("sourceChart");
        this.stageChartRef = useRef("stageChart");
        this.reservationStatusChartRef = useRef("reservationStatusChart");
        this.wingChartRef = useRef("wingChart");
        this.supervisorChartRef = useRef("supervisorChart");
        this.websiteChartRef = useRef("websiteChart");
        this.activityTypeChartRef = useRef("activityTypeChart");
        this.userLeadsChartRef = useRef("userLeadsChart"); // Add ref for user leads chart
        
        this.charts = {
            barChart: null,
            pieChart: null,
            receptionBarChart: null,
            receptionPieChart: null,
            sourceChart: null,
            stageChart: null,
            reservationStatusChart: null,
            wingChart: null,
            supervisorChart: null,
            websiteChart: null,
            activityTypeChart: null,
            userLeadsChart: null // Add user leads chart
        };

        // Initial setup
        onWillStart(async () => {
            await loadJS(["/web/static/lib/Chart/Chart.js"]);
            this.stats.userId = this.user.userId; // Set current user ID
            await this.checkUserRole();
            await this.fetchStats();
        });

        onMounted(() => {
            this.renderCharts();
            window.addEventListener('resize', this.handleResize);
        });

        onWillUnmount(() => {
            this.destroyAllCharts();
            window.removeEventListener('resize', this.handleResize);
        });
    }

    // Methods defined as arrow functions to maintain proper 'this' binding
    checkUserRole = async () => {
        const userGroups = await this.user.hasGroup;
        this.stats.isSupervisor = await userGroups('property_sales.group_property_sales_supervisor');
        
        if (this.stats.isSupervisor) {
            const userData = await this.orm.searchRead(
                "res.users",
                [['id', '=', this.user.userId]],
                ['property_sales_supervisor_id', 'property_sales_wing_id']
            );
            if (userData.length) {
                this.stats.currentSupervisorId = userData[0].property_sales_supervisor_id?.[0];
                this.stats.currentWingId = userData[0].property_sales_wing_id?.[0];
            }
        }
    };

    fetchStats = async () => {
        try {
            // Get call center, reception and website source IDs
            const [callCenterSource, receptionSource, websiteSource] = await Promise.all([
                this.orm.search("utm.source", [['name', '=', '6033']], { limit: 1 }),
                this.orm.search("utm.source", [['name', '=', 'Walk In']], { limit: 1 }),
                this.orm.search("utm.source", [['name', '=', 'Website']], { limit: 1 })
            ]);
            
            // Build base domains with date filters
            const baseLeadDomain = [];
            const baseReservationDomain = [];
            const basePropertyDomain = [];
            
            if (this.dateFilters.startDate) {
                baseLeadDomain.push(['create_date', '>=', this.dateFilters.startDate]);
                baseReservationDomain.push(['create_date', '>=', this.dateFilters.startDate]);
                basePropertyDomain.push(['create_date', '>=', this.dateFilters.startDate]);
            }
            if (this.dateFilters.endDate) {
                baseLeadDomain.push(['create_date', '<=', this.dateFilters.endDate + ' 23:59:59']);
                baseReservationDomain.push(['create_date', '<=', this.dateFilters.endDate + ' 23:59:59']);
                basePropertyDomain.push(['create_date', '<=', this.dateFilters.endDate + ' 23:59:59']);
            }

            // Add supervisor/wing filters if user is supervisor
            let leadDomain = [...baseLeadDomain];
            let reservationDomain = [...baseReservationDomain];
            let propertyDomain = [...basePropertyDomain];
            propertyDomain.push(['state', '=', 'sold']);
            
            if (this.stats.isSupervisor) {
                if (this.stats.currentSupervisorId) {
                    leadDomain.push(['supervisor_id', '=', this.stats.currentSupervisorId]);
                    propertyDomain.push(['supervisor_id', '=', this.stats.currentSupervisorId]);
                }
                if (this.stats.currentWingId) {
                    leadDomain.push(['wing_id', '=', this.stats.currentWingId]);
                    propertyDomain.push(['wing_id', '=', this.stats.currentWingId]);
                }
            }

            // Build source-specific domains
            const callCenterDomain = callCenterSource.length ? 
                [...leadDomain, ['source_id', '=', callCenterSource[0]]] : [];
            const receptionDomain = receptionSource.length ? 
                [...leadDomain, ['source_id', '=', receptionSource[0]]] : [];
            const websiteDomain = websiteSource.length ? 
                [...leadDomain, ['source_id', '=', websiteSource[0]]] : [];
            
            // Get user-specific data
            const userLeadDomain = [...leadDomain, ['user_id', '=', this.stats.userId]];
            const userProspectDomain = [...leadDomain, ['user_id', '=', this.stats.userId], ['stage_id.name', 'ilike', 'Prospect']];
            
            // Get counts and data
            const [
                totalCallCenterLeads, 
                totalReceptionLeads,
                totalWebsiteLeads,
                wingLeadsData,
                supervisorLeadsData,
                totalReservations,
                reservationDataByStatus,
                callCenterData, 
                receptionDataByStage,
                receptionData,
                leadDataBySource, 
                leadDataByStage,
                websiteLeadDataByStage,
                totalSoldProperties,
                userLeadsCount,
                userProspectsCount
            ] = await Promise.all([
                callCenterSource.length ? this.orm.searchCount("crm.lead", callCenterDomain) : 0,
                receptionSource.length ? this.orm.searchCount("crm.lead", receptionDomain) : 0,
                websiteSource.length ? this.orm.searchCount("crm.lead", websiteDomain) : 0,
                this.orm.readGroup(
                    "crm.lead",
                    leadDomain,
                    ['wing_id'],
                    ['wing_id']
                ),
                this.orm.readGroup(
                    "crm.lead",
                    leadDomain,
                    ['supervisor_id'],
                    ['supervisor_id']
                ),
                this.orm.searchCount("property.reservation", reservationDomain),
                this.orm.readGroup(
                    "property.reservation",
                    reservationDomain,
                    ['status'],
                    ['status']
                ),
                callCenterSource.length ? this.orm.readGroup(
                    "crm.lead",
                    callCenterDomain,
                    ['stage_id'],
                    ['stage_id']
                ) : [],
                receptionSource.length ? this.orm.readGroup(
                    "crm.lead",
                    receptionDomain,
                    ['stage_id'],
                    ['stage_id']
                ) : [],
                receptionSource.length ? this.orm.readGroup(
                    "crm.reception",
                    [['create_date', '>=', this.dateFilters.startDate],
                     ['create_date', '<=', this.dateFilters.endDate + ' 23:59:59']],
                    ['state'],
                    ['state']
                ) : [],
                this.orm.readGroup(
                    "crm.lead",
                    leadDomain,
                    ['source_id'],
                    ['source_id']
                ),
                this.orm.readGroup(
                    "crm.lead",
                    leadDomain,
                    ['stage_id'],
                    ['stage_id']
                ),
                websiteSource.length ? this.orm.readGroup(
                    "crm.lead",
                    websiteDomain,
                    ['stage_id'],
                    ['stage_id']
                ) : [],
                this.orm.searchCount("property.property", propertyDomain),
                this.orm.searchCount("crm.lead", userLeadDomain),
                this.orm.searchCount("crm.lead", userProspectDomain)
            ]);

            // Get total leads count
            const totalLeads = await this.orm.searchCount("crm.lead", leadDomain);
            const totalOtherLeads = totalLeads - totalCallCenterLeads - totalReceptionLeads - totalWebsiteLeads;

            // Get user activities count
            const userActivitiesCount = await this.orm.searchCount("mail.activity", [
                ['res_model', '=', 'crm.lead'],
                ['user_id', '=', this.stats.userId],
                ['date_deadline', '>=', this.dateFilters.startDate],
                ['date_deadline', '<=', this.dateFilters.endDate]
            ]);

            // Get activity counts from CRM messages
            const activityMessages = await this.orm.searchRead(
                "mail.message",
                [
                    ['model', '=', 'crm.lead'],
                    ['date', '>=', this.dateFilters.startDate],
                    ['date', '<=', this.dateFilters.endDate + ' 23:59:59'],
                    ['author_id', '=', this.stats.userId], // Only current user's activities
                    '|',
                    ['subtype_id', '=', 3], // Activity subtype
                    ['body', 'ilike', 'Lead/Opportunity created with phone']
                ],
                ['mail_activity_type_id', 'subtype_id', 'body']
            );

            // Process activity counts
            const activityCounts = {
                email: activityMessages.filter(msg => 
                    msg.mail_activity_type_id && msg.mail_activity_type_id[0] === 1  // Email
                ).length,
                call: activityMessages.filter(msg => 
                    msg.mail_activity_type_id && msg.mail_activity_type_id[0] === 4  // Call
                ).length,
                meeting: activityMessages.filter(msg => 
                    msg.mail_activity_type_id && msg.mail_activity_type_id[0] === 2  // Meeting
                ).length,
                todo: activityMessages.filter(msg => 
                    msg.mail_activity_type_id && msg.mail_activity_type_id[0] === 3  // To-Do
                ).length,
                upload: activityMessages.filter(msg => 
                    msg.mail_activity_type_id && msg.mail_activity_type_id[0] === 6  // Upload Document
                ).length
            };

            // Get activity type data for the chart
            const activityTypeData = await this.orm.readGroup(
                "mail.message",
                [
                    ['model', '=', 'crm.lead'],
                    ['date', '>=', this.dateFilters.startDate],
                    ['date', '<=', this.dateFilters.endDate + ' 23:59:59'],
                    ['author_id', '=', this.stats.userId], // Only current user's activities
                    ['subtype_id', '=', 3], // Activity subtype
                    ['mail_activity_type_id', 'in', [1, 2, 3, 4, 6]] // Email, Meeting, To-Do, Call, Upload
                ],
                ['mail_activity_type_id'],
                ['mail_activity_type_id']
            );

            // Get activity type names
            const activityTypeIds = activityTypeData
                .filter(item => item.mail_activity_type_id)
                .map(item => item.mail_activity_type_id[0]);
                
            const activityTypes = activityTypeIds.length 
                ? await this.orm.read("mail.activity.type", activityTypeIds, ['name']) 
                : [];

            const processedActivityData = activityTypeData.map(item => {
                const activityTypeId = item.mail_activity_type_id ? item.mail_activity_type_id[0] : null;
                const activityType = activityTypes.find(a => a.id === activityTypeId);
                
                return {
                    name: activityType ? activityType.name : 'Other Activity',
                    count: item.mail_activity_type_id_count
                };
            });

            // Add the "Prospect" type which comes from message body
            const prospectCount = await this.orm.searchCount("mail.message", [
                ['model', '=', 'crm.lead'],
                ['date', '>=', this.dateFilters.startDate],
                ['date', '<=', this.dateFilters.endDate + ' 23:59:59'],
                ['author_id', '=', this.stats.userId], // Only current user's prospects
                ['body', 'ilike', 'Lead/Opportunity created with phone']
            ]);

            if (prospectCount > 0) {
                processedActivityData.push({
                    name: 'Prospect',
                    count: prospectCount
                });
            }

            // Process wing and supervisor data
            const wingLeads = {};
            const supervisorLeads = {};
            
            // Get wing names
            const wingIds = wingLeadsData.filter(item => item.wing_id).map(item => item.wing_id[0]);
            const wings = wingIds.length ? await this.orm.read("property.sales.wing", wingIds, ['name']) : [];
            
            wingLeadsData.forEach(item => {
                const wingId = item.wing_id ? item.wing_id[0] : 'unassigned';
                const wingName = wingId !== 'unassigned' 
                    ? wings.find(w => w.id === wingId)?.name 
                    : 'Unassigned';
                wingLeads[wingName || 'Unassigned'] = item.wing_id_count;
            });
            
            // Get supervisor names
            const supervisorIds = supervisorLeadsData.filter(item => item.supervisor_id).map(item => item.supervisor_id[0]);
            const supervisors = supervisorIds.length ? await this.orm.read("property.sales.supervisor", supervisorIds, ['name']) : [];
            
            supervisorLeadsData.forEach(item => {
                const supervisorId = item.supervisor_id ? item.supervisor_id[0] : 'unassigned';
                const supervisorName = supervisorId !== 'unassigned' 
                    ? supervisors.find(s => s.id === supervisorId)?.name[1] 
                    : 'Unassigned';
                supervisorLeads[supervisorName || 'Unassigned'] = item.supervisor_id_count;
            });

            // Update all stats including the new user-specific counts
            this.stats.totalCallCenterLeads = totalCallCenterLeads;
            this.stats.totalReceptionLeads = totalReceptionLeads;
            this.stats.totalWebsiteLeads = totalWebsiteLeads;
            this.stats.totalOtherLeads = totalOtherLeads;
            this.stats.totalAllLeads = totalLeads;
            this.stats.wingLeads = wingLeads;
            this.stats.supervisorLeads = supervisorLeads;
            this.stats.totalReservations = totalReservations;
            this.stats.totalSoldProperties = totalSoldProperties;
            this.stats.reservationDataByStatus = reservationDataByStatus;
            this.stats.callCenterData = callCenterData;
            this.stats.receptionDataByStage = receptionDataByStage;
            this.stats.receptionData = receptionData;
            this.stats.leadDataBySource = leadDataBySource;
            this.stats.leadDataByStage = leadDataByStage;
            this.stats.activityTypeData = processedActivityData;
            this.stats.websiteLeadDataByStage = websiteLeadDataByStage;
            this.stats.activityCounts = activityCounts;
            this.stats.userLeads = userLeadsCount;
            this.stats.userProspects = userProspectsCount;
            this.stats.userActivities = userActivitiesCount;
        } catch (error) {
            console.error("Error fetching stats:", error);
        }
    };

    renderCharts = () => {
        this.destroyAllCharts();

        // ... (keep all existing chart rendering code)

        // Add new chart for user-specific data
        if (this.userLeadsChartRef.el) {
            try {
                const labels = ['My Leads', 'My Prospects', 'My Activities'];
                const data = [
                    this.stats.userLeads,
                    this.stats.userProspects,
                    this.stats.userActivities
                ];
                const backgroundColors = [
                    getColor(0),
                    getColor(1),
                    getColor(2)
                ];

                this.charts.userLeadsChart = new Chart(this.userLeadsChartRef.el, {
                    type: "doughnut",
                    data: {
                        labels: labels,
                        datasets: [{
                            data: data,
                            backgroundColor: backgroundColors,
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        animation: {
                            duration: 0
                        },
                        plugins: {
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                        const value = context.raw;
                                        const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                                        return `${context.label}: ${value} (${percentage}%)`;
                                    }
                                }
                            },
                            datalabels: {
                                formatter: function(value, context) {
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                                    return `${percentage}%`;
                                },
                                color: '#fff',
                                anchor: 'center',
                                align: 'center',
                                font: {
                                    weight: 'bold'
                                }
                            }
                        }
                    }
                });
            } catch (error) {
                console.error("Error rendering user leads chart:", error);
            }
        }
    };

    // Navigation methods
    goToMyLeadsPage = () => {
        const domain = [];
        
        if (this.dateFilters.startDate) {
            domain.push(['create_date', '>=', this.dateFilters.startDate]);
        }
        if (this.dateFilters.endDate) {
            domain.push(['create_date', '<=', this.dateFilters.endDate + ' 23:59:59']);
        }
        domain.push(['user_id', '=', this.stats.userId]);

        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "crm.lead",
            view_mode: "list",
            views: [[false, "list"]],
            target: "current",
            domain: domain,
        });
    };

    goToMyProspectsPage = () => {
        const domain = [];
        
        if (this.dateFilters.startDate) {
            domain.push(['create_date', '>=', this.dateFilters.startDate]);
        }
        if (this.dateFilters.endDate) {
            domain.push(['create_date', '<=', this.dateFilters.endDate + ' 23:59:59']);
        }
        domain.push(['user_id', '=', this.stats.userId]);
        domain.push(['stage_id.name', 'ilike', 'Prospect']);

        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "crm.lead",
            view_mode: "list",
            views: [[false, "list"]],
            target: "current",
            domain: domain,
        });
    };

    goToMyActivitiesPage = () => {
        const domain = [
            ['res_model', '=', 'crm.lead'],
            ['user_id', '=', this.stats.userId]
        ];
        
        if (this.dateFilters.startDate) {
            domain.push(['date_deadline', '>=', this.dateFilters.startDate]);
        }
        if (this.dateFilters.endDate) {
            domain.push(['date_deadline', '<=', this.dateFilters.endDate]);
        }

        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "mail.activity",
            view_mode: "list",
            views: [[false, "list"]],
            target: "current",
            domain: domain,
            context: {
                search_default_filter_my_activities: 1
            }
        });
    };

    // ... (keep all other existing methods)
}

ChartjsSampleCRM.template = "crm_dashboard.chartjs_sample_crm";
actionRegistry.add("chartjs_sample_crm", ChartjsSampleCRM);