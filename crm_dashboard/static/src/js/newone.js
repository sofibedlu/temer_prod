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
        date.setMonth(0);  // January is month 0
        date.setDate(1);   // First day of the month
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
            totalSoldPropertiesSecondary: 0,
            totalCallCenterLeads: 0,
            totalReceptionLeads: 0,
            totalSoldProperties: 0,
            totalWebsiteLeads: 0,
            totalOtherLeads: 0,
            otherLeadDataByStage: [],
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
                office_visit: 0,
                site_visit: 0,
                sms: 0
            },
            isSupervisor: false,
            currentSupervisorId: null,
            currentWingId: null
        });

        // Chart references
        this.barChartRef = useRef("barChart");
        this.pieChartRef = useRef("pieChart");
        this.receptionBarChartRef = useRef("receptionBarChart");
        this.receptionPieChartRef = useRef("receptionPieChart");
        this.sourceChartRef = useRef("sourceChart");
        this.activityTypeChartbarRef = useRef("activityTypeChartBar");
        this.sourceChartpieRef = useRef("sourceChartPie");
        this.sourceChartPieRef = useRef("sourceChartPie");

        this.otherLeadsBarRef = useRef("otherLeadsBar");
        this.otherLeadsPieRef = useRef("otherLeadsPie");

        this.otherLeadStageBarRef = useRef("otherLeadStageBar");
        this.otherLeadStagePieRef = useRef("otherLeadStagePie");

        this.sourceBarChartRef       = useRef("sourceBarChart");
        this.reservationBarChartRef  = useRef("reservationBarChart");
        
        this.stageChartRef = useRef("stageChart");
        this.stageChartPieRef = useRef("stageChartPie");
        this.reservationStatusChartRef = useRef("reservationStatusChart");
        this.wingChartRef = useRef("wingChart");
        this.wingChartPieRef = useRef("wingChartPie");
        this.supervisorChartRef = useRef("supervisorChart");
        this.supervisorChartPieRef = useRef("supervisorChartPie");
        this.websiteChartRef = useRef("websiteChart");
        this.websiteChartPieRef = useRef("websiteChartPie");
        
        this.activityTypeChartRef = useRef("activityTypeChart");
        this.activityTypeChartbarRef = useRef("activityTypeChartBar");
        this.wingPieChartRef = useRef("wingPieChart");

        this.charts = {
            barChart: null,
            pieChart: null,
            receptionBarChart: null,
            receptionPieChart: null,
            sourceChart: null,
            sourceChartpie: null,
            stageChart: null,
            stageChartPie: null,
            reservationStatusChart: null,
            wingChart: null,
            wingChartPie: null,
            supervisorChart: null,
            supervisorChartPie: null,
            websiteChart: null,
            websiteChartPie: null,
            activityTypeChart: null,
            activityTypeBarChart: null,
            otherLeadsBar: null,
            otherLeadsPie: null,
            otherLeadStageBar: null,
            otherLeadStagePie: null,
            sourceBarChart: null,
            reservationBarChart: null
        };

        // Initial setup
        onWillStart(async () => {
            await loadJS(["/web/static/lib/Chart/Chart.js"]);
            await this.checkUserRole();
            await this.fetchStats();
        });

//         onWillStart(async () => {
//     try {
//         await Promise.all([
//             loadJS("https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js"),
//             loadJS("https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0/dist/chartjs-plugin-datalabels.min.js")
//         ]);
//         if (window.Chart) {
//             Chart.register(window.ChartDataLabels);
//         }
//         await this.checkUserRole();
//         await this.fetchStats();
//     } catch (error) {
//         console.error("Error loading chart libraries:", error);
//     }
// });

        onMounted(() => {
            this.renderCharts();
            window.addEventListener('resize', this.handleResize);
        });

        onWillUnmount(() => {
            this.destroyAllCharts();
            window.removeEventListener('resize', this.handleResize);
        });
    }

    checkUserRole = async () => {
        // Check if user is in the property_sales_supervisor group
        const userGroups = await this.user.hasGroup;
        this.stats.isSupervisor = await userGroups('property_sales.group_property_sales_supervisor');
        
        if (this.stats.isSupervisor) {
            // If supervisor, read their assigned supervisor_id and wing_id from res.users
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

        // If not a supervisor, check if the user is a wing manager
        if (!this.stats.currentWingId) {
            const wingAsManager = await this.orm.searchRead(
                "property.sales.wing",
                [['manager_id', '=', this.user.userId]],
                ['id']
            );
            if (wingAsManager.length) {
                this.stats.currentWingId = wingAsManager[0].id;
            }
        }
    };

    getDefaultEndDate = () => {
        return new Date().toISOString().split('T')[0];
    };

    destroyAllCharts = () => {
        Object.values(this.charts).forEach(chart => {
            if (chart) {
                chart.destroy();
            }
        });
        this.charts = {
            barChart: null,
            pieChart: null,
            receptionBarChart: null,
            receptionPieChart: null,
            sourceChart: null,
            sourceChartpie: null,
            stageChart: null,
            stageChartPie: null,
            reservationStatusChart: null,
            wingChart: null,
            wingChartPie: null,
            supervisorChart: null,
            supervisorChartPie: null,
            websiteChart: null,
            websiteChartPie: null,
            activityTypeChart: null,
            activityTypeBarChart: null,
            otherLeadsBar: null,
            otherLeadsPie: null,
            otherLeadStageBar: null,
            otherLeadStagePie: null,
            sourceBarChart: null,
            reservationBarChart: null
        };
    };

    handleResize = () => {
        clearTimeout(this.resizeTimer);
        this.resizeTimer = setTimeout(() => {
            this.renderCharts();
        }, 200);
    };

    fetchStats = async () => {
        try {
            // Get call center, reception and website source IDs
            const [callCenterSource, receptionSource, websiteSource] = await Promise.all([
                this.orm.search("utm.source", [['name', '=', '6033']], { limit: 1 }),
                this.orm.search("utm.source", [['name', '=', 'Walk In']], { limit: 1 }),
                this.orm.search("utm.source", [['name', '=', 'Website']], { limit: 1 })
            ]);

            const totalSoldPropertiesSecondary = await this.orm.searchCount("property.property", [
    ['state', '=', 'sold'],
    // add more filters if needed
]);
this.stats.totalSoldPropertiesSecondary = totalSoldPropertiesSecondary;

            console.log("websiteSourcellllllllllllllllll", websiteSource);

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

            // Prepare domains (call center, reception, website) after applying wing/supervisor filter
            let leadDomain = [...baseLeadDomain];
            let reservationDomain = [...baseReservationDomain];
            let propertyDomain = [...basePropertyDomain];
            propertyDomain.push(['state', '=', 'sold']);
            
            if (this.stats.currentSupervisorId) {
                leadDomain.push(['supervisor_id', '=', this.stats.currentSupervisorId]);
                propertyDomain.push(['supervisor_id', '=', this.stats.currentSupervisorId]);
            }

            if (this.stats.currentWingId) {
                leadDomain.push(['wing_id', '=', this.stats.currentWingId]);
                propertyDomain.push(['wing_id', '=', this.stats.currentWingId]);
                reservationDomain.push(['wing_id', '=', this.stats.currentWingId]);
            }



            // Now build source-specific domains from leadDomain (which is already wing- and supervisor-filtered)
            const callCenterDomain = callCenterSource.length
                ? [...leadDomain, ['source_id', '=', callCenterSource[0]]]
                : [];
            const receptionDomain = receptionSource.length
                ? [...leadDomain, ['source_id', '=', receptionSource[0]]]
                : [];
            const websiteDomain = websiteSource.length
                ? [...leadDomain, ['source_id', '=', websiteSource[0]]]
                : [];

            

            // Build “Other Leads by Stage” from leadDomain
            {
                const excludedSources = [];
                if (callCenterSource.length)   excludedSources.push(['source_id', '!=', callCenterSource[0]]);
                if (receptionSource.length)    excludedSources.push(['source_id', '!=', receptionSource[0]]);
                if (websiteSource.length)      excludedSources.push(['source_id', '!=', websiteSource[0]]);

                const otherLeadsDomain = [...leadDomain];
                excludedSources.forEach(clause => otherLeadsDomain.push(clause));

                const otherLeadDataByStage = await this.orm.readGroup(
                    "crm.lead",
                    otherLeadsDomain,
                    ['stage_id'],
                    ['stage_id']
                );
                this.stats.otherLeadDataByStage = otherLeadDataByStage;
            }






// const [
//     totalCallCenterLeads,
//     totalReceptionLeads,
//     totalWebsiteLeads,
//     wingLeadsData,
//     supervisorLeadsData,
//     totalReservations,
//     reservationDataByStatus,
//     callCenterData,
//     receptionDataByStage,
//     receptionData,
//     leadDataBySource,
//     leadDataByStage,
//     websiteLeadDataByStage,
//     totalSoldProperties // <--- this will be the count
// ] = await Promise.all([
//     callCenterSource.length
//         ? this.orm.searchCount("crm.lead", callCenterDomain)
//         : 0,
//     receptionSource.length
//         ? this.orm.searchCount("crm.lead", receptionDomain)
//         : 0,
//     websiteSource.length
//         ? this.orm.searchCount("crm.lead", websiteDomain)
//         : 0,
   
//     this.orm.readGroup("crm.lead", leadDomain, ['wing_id'], ['wing_id']),
//     this.orm.readGroup("crm.lead", leadDomain, ['supervisor_id'], ['supervisor_id']),
//     this.orm.searchCount("property.reservation", reservationDomain),
//     this.orm.readGroup("property.reservation", reservationDomain, ['status'], ['status']),
//     callCenterSource.length
//         ? this.orm.readGroup("crm.lead", callCenterDomain, ['stage_id'], ['stage_id'])
//         : [],
//     receptionSource.length
//         ? this.orm.readGroup("crm.lead", receptionDomain, ['stage_id'], ['stage_id'])
//         : [],
//     websiteSource.length
//         ? this.orm.readGroup("crm.lead", websiteDomain, ['stage_id'], ['stage_id'])
//         : [],
//     this.orm.readGroup("crm.lead", leadDomain, ['stage_id'], ['stage_id']),
//     this.orm.readGroup("crm.lead", leadDomain, ['source_id'], ['source_id']),
//     websiteSource.length
//         ? this.orm.readGroup("crm.lead", websiteDomain, ['stage_id'], ['stage_id'])
//         : [],
//     propertyDomain.length
//         ? this.orm.searchCount("property.property", propertyDomain) // <--- for sold properties card
//         : 0
// ]);




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
    leadDataByStage,         // <-- all leads by stage
    websiteLeadDataByStage,  // <-- website leads by stage
    totalSoldProperties
] = await Promise.all([
    callCenterSource.length
        ? this.orm.searchCount("crm.lead", callCenterDomain)
        : 0,
    receptionSource.length
        ? this.orm.searchCount("crm.lead", receptionDomain)
        : 0,
    websiteSource.length
        ? this.orm.searchCount("crm.lead", websiteDomain)
        : 0,
    this.orm.readGroup("crm.lead", leadDomain, ['wing_id'], ['wing_id']),
    this.orm.readGroup("crm.lead", leadDomain, ['supervisor_id'], ['supervisor_id']),
    this.orm.searchCount("property.reservation", reservationDomain),
    this.orm.readGroup("property.reservation", reservationDomain, ['status'], ['status']),
    callCenterSource.length
        ? this.orm.readGroup("crm.lead", callCenterDomain, ['stage_id'], ['stage_id'])
        : [],
    receptionSource.length
        ? this.orm.readGroup("crm.lead", receptionDomain, ['stage_id'], ['stage_id'])
        : [],
    this.orm.readGroup("crm.lead", leadDomain, ['stage_id'], ['stage_id']), // receptionData
    this.orm.readGroup("crm.lead", leadDomain, ['source_id'], ['source_id']),
    this.orm.readGroup("crm.lead", leadDomain, ['stage_id'], ['stage_id']), // leadDataByStage
    websiteSource.length
        ? this.orm.readGroup("crm.lead", websiteDomain, ['stage_id'], ['stage_id'])
        : [],
    propertyDomain.length
        ? this.orm.searchCount("property.property", propertyDomain)
        : 0
]);












            // Get total leads count
            const totalLeads = await this.orm.searchCount("crm.lead", leadDomain);
            const totalOtherLeads = totalLeads - totalCallCenterLeads - totalReceptionLeads - totalWebsiteLeads;

            // Activities: filter mail.message by wing via res_id in crm.lead
            const activityDomain = [
                ['model', '=', 'crm.lead'],
                ['date', '>=', this.dateFilters.startDate],
                ['date', '<=', this.dateFilters.endDate + ' 23:59:59'],
                ['subtype_id', '=', 3],
                ['mail_activity_type_id', 'in', [1, 4, 5, 8, 9]]
            ];
            if (this.stats.currentWingId) {
                activityDomain.push(['res_id', 'in',
                    await this.orm.search('crm.lead', [['wing_id', '=', this.stats.currentWingId]])
                ]);
            }
            const activityMessages = await this.orm.searchRead(
                "mail.message",
                activityDomain,
                ['mail_activity_type_id']
            );
            const activityCounts = {
                email: activityMessages.filter(msg =>
                    msg.mail_activity_type_id && msg.mail_activity_type_id[0] === 1
                ).length,
                call: activityMessages.filter(msg =>
                    msg.mail_activity_type_id && msg.mail_activity_type_id[0] === 4
                ).length,
                office_visit: activityMessages.filter(msg =>
                    msg.mail_activity_type_id && msg.mail_activity_type_id[0] === 8
                ).length,
                site_visit: activityMessages.filter(msg =>
                    msg.mail_activity_type_id && msg.mail_activity_type_id[0] === 9
                ).length,
                sms: activityMessages.filter(msg =>
                    msg.mail_activity_type_id && msg.mail_activity_type_id[0] === 5
                ).length
            };

            // Activity type data (all 5 types)
            const activityTypeData = await this.orm.readGroup(
                "mail.message",
                [
                    ['model', '=', 'crm.lead'],
                    ['date', '>=', this.dateFilters.startDate],
                    ['date', '<=', this.dateFilters.endDate + ' 23:59:59'],
                    ['subtype_id', '=', 3],
                    ['mail_activity_type_id', 'in', [1, 4, 5, 8, 9]]
                ],
                ['mail_activity_type_id'],
                ['mail_activity_type_id']
            );
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
            const prospectCount = await this.orm.searchCount("mail.message", [
                ['model', '=', 'crm.lead'],
                ['date', '>=', this.dateFilters.startDate],
                ['date', '<=', this.dateFilters.endDate + ' 23:59:59'],
                ['body', 'ilike', 'Lead/Opportunity created with phone']
            ]);
            if (prospectCount > 0) {
                processedActivityData.push({
                    name: 'Prospect',
                    count: prospectCount
                });
            }

            // Process wing and supervisor aggregates
            const wingLeads = {};
            const supervisorLeads = {};
            const wingIds = wingLeadsData.filter(item => item.wing_id).map(item => item.wing_id[0]);
            const wings = wingIds.length
                ? await this.orm.read("property.sales.wing", wingIds, ['name'])
                : [];
            wingLeadsData.forEach(item => {
                const wingId = item.wing_id ? item.wing_id[0] : 'unassigned';
                const wingName = wingId !== 'unassigned'
                    ? wings.find(w => w.id === wingId)?.name
                    : 'Unassigned';
                wingLeads[wingName || 'Unassigned'] = item.wing_id_count;
            });
            const supervisorIds = supervisorLeadsData.filter(item => item.supervisor_id).map(item => item.supervisor_id[0]);
            const supervisors = supervisorIds.length
                ? await this.orm.read("property.sales.supervisor", supervisorIds, ['name'])
                : [];
            supervisorLeadsData.forEach(item => {
                const supervisorId = item.supervisor_id ? item.supervisor_id[0] : 'unassigned';
                const supervisorName = supervisorId !== 'unassigned'
                    ? supervisors.find(s => s.id === supervisorId)?.name[1]
                    : 'Unassigned';
                supervisorLeads[supervisorName || 'Unassigned'] = item.supervisor_id_count;
            });

            // Update all stats including the new sold properties count
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
            // this.stats.websiteLeadDataByStage = websiteLeadDataByStage;
            this.stats.websiteLeadDataByStage = websiteLeadDataByStage;
           console.log("Website grouped data for chart", this.stats.websiteLeadDataByStage);
            this.stats.activityCounts = activityCounts;
        } catch (error) {
            console.error("Error fetching stats:", error);
        }
    };

    renderCharts = () => {
        this.destroyAllCharts();

        // Call Center Charts
        if (this.stats.callCenterData.length && this.barChartRef.el) {
            try {
                const labels = this.stats.callCenterData.map(item => item.stage_id[1]);
                const data = this.stats.callCenterData.map(item => item.stage_id_count);
                const backgroundColors = labels.map((_, index) => getColor(index));

                // Bar Chart
                this.charts.barChart = new Chart(this.barChartRef.el, {
                    type: "bar",
                    data: {
                        labels: labels,
                        datasets: [{
                            label: 'Call Center Leads by Stage',
                            data: data,
                            backgroundColor: backgroundColors,
                            borderColor: backgroundColors.map(color => color.replace('0.6', '1')),
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: {
                                beginAtZero: true,
                                ticks: {
                                    callback: function(value) {
                                        const total = this.chart.data.datasets[0].data.reduce((a, b) => a + b, 0);
                                        const percentage = ((value / total) * 100).toFixed(1);
                                        return `${value} (${percentage}%)`;
                                    }
                                }
                            }
                        },
                        animation: { duration: 0 },
                        plugins: {
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                        const value = context.raw;
                                        const percentage = ((value / total) * 100).toFixed(1);
                                        return `${context.dataset.label}: ${value} (${percentage}%)`;
                                    }
                                }
                            }
                        }
                    }
                });

                // Pie Chart
                this.charts.pieChart = new Chart(this.pieChartRef.el, {
                    type: "pie",
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
                        animation: { duration: 0 },
                        plugins: {
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                        const value = context.raw;
                                        const percentage = ((value / total) * 100).toFixed(1);
                                        return `${context.label}: ${value} (${percentage}%)`;
                                    }
                                }
                            },
                            datalabels: {
                                formatter: function(value, context) {
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = ((value / total) * 100).toFixed(1);
                                    return `${percentage}%`;
                                },
                                color: '#fff',
                                anchor: 'center',
                                align: 'center',
                                font: { weight: 'bold' }
                            }
                        }
                    }
                });
            } catch (error) {
                console.error("Error rendering call center charts:", error);
            }
        }

        // Reception Charts
        if (this.stats.receptionDataByStage.length && this.receptionBarChartRef.el) {
            try {
                const labels = this.stats.receptionDataByStage.map(item => item.stage_id[1]);
                const data = this.stats.receptionDataByStage.map(item => item.stage_id_count);
                const backgroundColors = labels.map((_, index) => getColor(index + 5));

                // Bar Chart
                this.charts.receptionBarChart = new Chart(this.receptionBarChartRef.el, {
                    type: "bar",
                    data: {
                        labels: labels,
                        datasets: [{
                            label: 'Reception Leads by Stage',
                            data: data,
                            backgroundColor: backgroundColors,
                            borderColor: backgroundColors.map(color => color.replace('0.6', '1')),
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: {
                                beginAtZero: true,
                                ticks: {
                                    callback: function(value) {
                                        const total = this.chart.data.datasets[0].data.reduce((a, b) => a + b, 0);
                                        const percentage = ((value / total) * 100).toFixed(1);
                                        return `${value} (${percentage}%)`;
                                    }
                                }
                            }
                        },
                        animation: { duration: 0 },
                        plugins: {
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                        const value = context.raw;
                                        const percentage = ((value / total) * 100).toFixed(1);
                                        return `${context.dataset.label}: ${value} (${percentage}%)`;
                                    }
                                }
                            }
                        }
                    }
                });

                // Pie Chart
                this.charts.receptionPieChart = new Chart(this.receptionPieChartRef.el, {
                    type: "pie",
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
                        animation: { duration: 0 },
                        plugins: {
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                        const value = context.raw;
                                        const percentage = ((value / total) * 100).toFixed(1);
                                        return `${context.label}: ${value} (${percentage}%)`;
                                    }
                                }
                            },
                            datalabels: {
                                formatter: function(value, context) {
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = ((value / total) * 100).toFixed(1);
                                    return `${percentage}%`;
                                },
                                color: '#fff',
                                anchor: 'center',
                                align: 'center',
                                font: { weight: 'bold' }
                            }
                        }
                    }
                });
            } catch (error) {
                console.error("Error rendering reception charts:", error);
            }
        }


        console.log("Website chart datadfddfdf", this.stats.websiteLeadDataByStage, this.websiteChartRef.el, this.websiteChartPieRef.el);

        // Website Charts
        if (this.stats.websiteLeadDataByStage.length && this.websiteChartRef.el) {
            try {
                const labels = this.stats.websiteLeadDataByStage.map(item => item.stage_id[1]);
                const data = this.stats.websiteLeadDataByStage.map(item => item.stage_id_count);
                const backgroundColors = labels.map((_, index) => getColor(index + 35));

                this.charts.websiteChart = new Chart(this.websiteChartRef.el, {
                    type: "bar",
                    data: {
                        labels: labels,
                        datasets: [{
                            label: 'Website Leads by Stage',
                            data: data,
                            backgroundColor: backgroundColors,
                            borderColor: backgroundColors.map(color => color.replace('0.6', '1')),
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: {
                                beginAtZero: true,
                                ticks: {
                                    callback: function(value) {
                                        const total = this.chart.data.datasets[0].data.reduce((a, b) => a + b, 0);
                                        const percentage = ((value / total) * 100).toFixed(1);
                                        return `${value} (${percentage}%)`;
                                    }
                                }
                            }
                        },
                        animation: { duration: 0 },
                        plugins: {
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                        const value = context.raw;
                                        const percentage = ((value / total) * 100).toFixed(1);
                                        return `${context.dataset.label}: ${value} (${percentage}%)`;
                                    }
                                }
                            }
                        }
                    }
                });
            } catch (error) {
                console.error("Error rendering website chart:", error);
            }
        }

        // 1) “Other Leads” as a BAR chart
        if (
            typeof this.stats.totalOtherLeads === 'number' &&
            this.otherLeadsBarRef &&
            this.otherLeadsBarRef.el
        ) {
            try {
                const label = "Sales Leads";
                const value = this.stats.totalOtherLeads;
                const color = getColor(0);

                this.charts.otherLeadsBar = new Chart(
                    this.otherLeadsBarRef.el,
                    {
                        type: "bar",
                        data: {
                            labels: [label],
                            datasets: [{
                                label: label,
                                data: [value],
                                backgroundColor: [color],
                                borderColor: [color.replace('0.6','1')],
                                borderWidth: 1
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            scales: {
                                y: {
                                    beginAtZero: true,
                                    ticks: {
                                        callback: function(v) {
                                            // Since there's only one bar, percentage = 100%
                                            return `${v} (100%)`;
                                        }
                                    }
                                }
                            },
                            plugins: {
                                tooltip: {
                                    callbacks: {
                                        label: function(ctx) {
                                            const val = ctx.raw;
                                            return `${label}: ${val} (100%)`;
                                        }
                                    }
                                }
                            }
                        }
                    }
                );
            } catch (e) {
                console.error("Error rendering other leads bar chart:", e);
            }
        }

        // 2) “Other Leads” as a PIE chart
        if (
            typeof this.stats.totalOtherLeads === 'number' &&
            this.otherLeadsPieRef &&
            this.otherLeadsPieRef.el
        ) {
            try {
                const label = "Sales Leads";
                const value = this.stats.totalOtherLeads;
                const color = getColor(0);

                this.charts.otherLeadsPie = new Chart(
                    this.otherLeadsPieRef.el,
                    {
                        type: "pie",
                        data: {
                            labels: [label],
                            datasets: [{
                                data: [value],
                                backgroundColor: [color],
                                borderWidth: 1
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                tooltip: {
                                    callbacks: {
                                        label: function(ctx) {
                                            const val = ctx.raw;
                                            return `${label}: ${val} (100%)`;
                                        }
                                    }
                                },
                                datalabels: {
                                    formatter: function(v, c) {
                                        return "100%";
                                    },
                                    color: '#fff',
                                    anchor: 'center',
                                    align: 'center',
                                    font: { weight: 'bold' }
                                }
                            }
                        }
                    }
                );
            } catch (e) {
                console.error("Error rendering other leads pie chart:", e);
            }
        }

        // “Other Leads by Stage” BAR
        if (
            Array.isArray(this.stats.otherLeadDataByStage) &&
            this.stats.otherLeadDataByStage.length &&
            this.otherLeadStageBarRef &&
            this.otherLeadStageBarRef.el
        ) {
            try {
                const labels = this.stats.otherLeadDataByStage.map(item => item.stage_id[1]);
                const data   = this.stats.otherLeadDataByStage.map(item => item.stage_id_count);
                const colors = labels.map((_, idx) => getColor(idx + 50));

                this.charts.otherLeadStageBar = new Chart(
                    this.otherLeadStageBarRef.el,
                    {
                        type: "bar",
                        data: {
                            labels: labels,
                            datasets: [{
                                label: 'Sales Leads by Stage',
                                data: data,
                                backgroundColor: colors,
                                borderColor: colors.map(c => c.replace('0.6', '1')),
                                borderWidth: 1
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            scales: {
                                y: {
                                    beginAtZero: true,
                                    ticks: {
                                        callback: function(value) {
                                            const total = this.chart.data.datasets[0].data.reduce((a, b) => a + b, 0);
                                            const pct = ((value / total) * 100).toFixed(1);
                                            return `${value} (${pct}%)`;
                                        }
                                    }
                                }
                            },
                            plugins: {
                                tooltip: {
                                    callbacks: {
                                        label: function(ctx) {
                                            const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                                            const val = ctx.raw;
                                            const pct = ((val / total) * 100).toFixed(1);
                                            return `${ctx.dataset.label}: ${val} (${pct}%)`;
                                        }
                                    }
                                }
                            }
                        }
                    }
                );
            } catch (error) {
                console.error("Error rendering Other Leads by Stage bar:", error);
            }
        }

        // “Other Leads by Stage” PIE
        if (
            Array.isArray(this.stats.otherLeadDataByStage) &&
            this.stats.otherLeadDataByStage.length &&
            this.otherLeadStagePieRef &&
            this.otherLeadStagePieRef.el
        ) {
            try {
                const labels = this.stats.otherLeadDataByStage.map(item => item.stage_id[1]);
                const data   = this.stats.otherLeadDataByStage.map(item => item.stage_id_count);
                const colors = labels.map((_, idx) => getColor(idx + 50));

                this.charts.otherLeadStagePie = new Chart(
                    this.otherLeadStagePieRef.el,
                    {
                        type: "pie",
                        data: {
                            labels: labels,
                            datasets: [{
                                data: data,
                                backgroundColor: colors,
                                borderWidth: 1
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                tooltip: {
                                    callbacks: {
                                        label: function(ctx) {
                                            const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                                            const val = ctx.raw;
                                            const pct = ((val / total) * 100).toFixed(1);
                                            return `${ctx.label}: ${val} (${pct}%)`;
                                        }
                                    }
                                },
                                datalabels: {
                                    formatter: function(value, context) {
                                        const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                        const pct = ((value / total) * 100).toFixed(1);
                                        return `${pct}%`;
                                    },
                                    color: '#fff',
                                    anchor: 'center',
                                    align: 'center',
                                    font: { weight: 'bold' }
                                }
                            }
                        }
                    }
                );
            } catch (error) {
                console.error("Error rendering Other Leads by Stage pie:", error);
            }
        }

        // Website PIE Chart
        if (this.stats.websiteLeadDataByStage.length && this.websiteChartPieRef.el) {
            try {
                const labels = this.stats.websiteLeadDataByStage.map(item => item.stage_id[1]);
                const data = this.stats.websiteLeadDataByStage.map(item => item.stage_id_count);
                const backgroundColors = labels.map((_, index) => getColor(index + 35));
                this.charts.websiteChartPie = new Chart(this.websiteChartPieRef.el, {
                    type: "pie",
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
                        animation: { duration: 0 },
                        plugins: {
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                        const value = context.raw;
                                        const percentage = ((value / total) * 100).toFixed(1);
                                        return `${context.label}: ${value} (${percentage}%)`;
                                    }
                                }
                            },
                            datalabels: {
                                formatter: function(value, context) {
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = ((value / total) * 100).toFixed(1);
                                    return `${percentage}%`;
                                },
                                color: '#fff',
                                anchor: 'center',
                                align: 'center',
                                font: { weight: 'bold' }
                            }
                        }
                    }
                });
            } catch (error) {
                console.error("Error rendering website pie chart:", error);
            }
        }

        // Activity Type Charts (ordered)
        const desiredOrder = ['Office Visit', 'Site Visit', 'Call', 'Email'];
        const filteredActivityTypeData = desiredOrder
            .map(name => this.stats.activityTypeData.find(item => item.name === name))
            .filter(item => item);
        if (filteredActivityTypeData.length && this.activityTypeChartRef.el) {
            try {
                const labels = filteredActivityTypeData.map(item => item.name);
                const data = filteredActivityTypeData.map(item => item.count);
                const backgroundColors = labels.map((_, index) => getColor(index + 40));

                this.charts.activityTypeChart = new Chart(this.activityTypeChartRef.el, {
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
                        animation: { duration: 0 },
                        plugins: {
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                        const value = context.raw;
                                        const percentage = ((value / total) * 100).toFixed(1);
                                        return `${context.label}: ${value} (${percentage}%)`;
                                    }
                                }
                            },
                            datalabels: {
                                formatter: function(value, context) {
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = ((value / total) * 100).toFixed(1);
                                    return `${percentage}%`;
                                },
                                color: '#fff',
                                anchor: 'center',
                                align: 'center',
                                font: { weight: 'bold' }
                            }
                        }
                    }
                });
            } catch (error) {
                console.error("Error rendering activity type chart:", error);
            }
        }
        if (filteredActivityTypeData.length && this.activityTypeChartbarRef.el) {
            try {
                const labels = filteredActivityTypeData.map(item => item.name);
                const data = filteredActivityTypeData.map(item => item.count);
                const backgroundColors = labels.map((_, index) => getColor(index + 40));

                this.charts.activityTypeBarChart = new Chart(this.activityTypeChartbarRef.el, {
                    type: "bar",
                    data: {
                        labels: labels,
                        datasets: [{
                            label: 'Activity Types',
                            data: data,
                            backgroundColor: backgroundColors,
                            borderColor: backgroundColors.map(color => color.replace('0.6', '1')),
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: {
                                beginAtZero: true,
                                ticks: {
                                    callback: function(value) {
                                        const total = this.chart.data.datasets[0].data.reduce((a, b) => a + b, 0);
                                        const percentage = ((value / total) * 100).toFixed(1);
                                        return `${value} (${percentage}%)`;
                                    }
                                }
                            }
                        },
                        animation: { duration: 0 },
                        plugins: {
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                        const value = context.raw;
                                        const percentage = ((value / total) * 100).toFixed(1);
                                        return `${context.dataset.label}: ${value} (${percentage}%)`;
                                    }
                                }
                            }
                        }
                    }
                });
            } catch (error) {
                console.error("Error rendering activity type bar chart:", error);
            }
        }

        // Wing and Supervisor Charts
        if (Object.keys(this.stats.wingLeads).length && this.wingChartRef.el) {
            try {
                const wingLabels = Object.keys(this.stats.wingLeads);
                const wingData = Object.values(this.stats.wingLeads);
                const wingColors = wingLabels.map((_, index) => getColor(index + 10));

                this.charts.wingChart = new Chart(this.wingChartRef.el, {
                    type: "bar",
                    data: {
                        labels: wingLabels,
                        datasets: [{
                            label: 'Leads by Wing',
                            data: wingData,
                            backgroundColor: wingColors,
                            borderColor: wingColors.map(color => color.replace('0.6', '1')),
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: {
                                beginAtZero: true,
                                ticks: {
                                    callback: function(value) {
                                        const total = this.chart.data.datasets[0].data.reduce((a, b) => a + b, 0);
                                        const percentage = ((value / total) * 100).toFixed(1);
                                        return `${value} (${percentage}%)`;
                                    }
                                }
                            }
                        },
                        animation: { duration: 0 },
                        plugins: {
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                        const value = context.raw;
                                        const percentage = ((value / total) * 100).toFixed(1);
                                        return `${context.dataset.label}: ${value} (${percentage}%)`;
                                    }
                                }
                            }
                        }
                    }
                });
            } catch (error) {
                console.error("Error rendering wing chart:", error);
            }
        }
        if (Object.keys(this.stats.wingLeads).length && this.wingChartPieRef.el) {
            try {
                const wingLabels = Object.keys(this.stats.wingLeads);
                const wingData = Object.values(this.stats.wingLeads);
                const wingColors = wingLabels.map((_, index) => getColor(index + 10));
                this.charts.wingChartPie = new Chart(this.wingChartPieRef.el, {
                    type: "pie",
                    data: {
                        labels: wingLabels,
                        datasets: [{
                            data: wingData,
                            backgroundColor: wingColors,
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        animation: { duration: 0 },
                        plugins: {
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                        const value = context.raw;
                                        const percentage = ((value / total) * 100).toFixed(1);
                                        return `${context.label}: ${value} (${percentage}%)`;
                                    }
                                }
                            },
                            datalabels: {
                                formatter: function(value, context) {
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = ((value / total) * 100).toFixed(1);
                                    return `${percentage}%`;
                                },
                                color: '#fff',
                                anchor: 'center',
                                align: 'center',
                                font: { weight: 'bold' }
                            }
                        }
                    }
                });
            } catch (error) {
                console.error("Error rendering wing pie chart:", error);
            }
        }

        if (Object.keys(this.stats.supervisorLeads).length && this.supervisorChartPieRef.el) {
            try {
                const supervisorLabels = Object.keys(this.stats.supervisorLeads);
                const supervisorData = Object.values(this.stats.supervisorLeads);
                const supervisorColors = supervisorLabels.map((_, index) => getColor(index + 15));

                this.charts.supervisorChartPie = new Chart(this.supervisorChartPieRef.el, {
                    type: "pie",
                    data: {
                        labels: supervisorLabels,
                        datasets: [{
                            data: supervisorData,
                            backgroundColor: supervisorColors,
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        animation: { duration: 0 },
                        plugins: {
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                        const value = context.raw;
                                        const percentage = ((value / total) * 100).toFixed(1);
                                        return `${context.label}: ${value} (${percentage}%)`;
                                    }
                                }
                            },
                            datalabels: {
                                formatter: function(value, context) {
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = ((value / total) * 100).toFixed(1);
                                    return `${percentage}%`;
                                },
                                color: '#fff',
                                anchor: 'center',
                                align: 'center',
                                font: { weight: 'bold' }
                            }
                        }
                    }
                });
            } catch (error) {
                console.error("Error rendering supervisor pie chart:", error);
            }
        }

        if (Object.keys(this.stats.supervisorLeads).length && this.supervisorChartRef.el) {
            try {
                const supervisorLabels = Object.keys(this.stats.supervisorLeads);
                const supervisorData = Object.values(this.stats.supervisorLeads);
                const supervisorColors = supervisorLabels.map((_, index) => getColor(index + 15));

                this.charts.supervisorChart = new Chart(this.supervisorChartRef.el, {
                    type: "bar",
                    data: {
                        labels: supervisorLabels,
                        datasets: [{
                            label: 'Leads by Supervisor',
                            data: supervisorData,
                            backgroundColor: supervisorColors,
                            borderColor: supervisorColors.map(color => color.replace('0.6', '1')),
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: {
                                beginAtZero: true,
                                ticks: {
                                    callback: function(value) {
                                        const total = this.chart.data.datasets[0].data.reduce((a, b) => a + b, 0);
                                        const percentage = ((value / total) * 100).toFixed(1);
                                        return `${value} (${percentage}%)`;
                                    }
                                }
                            }
                        },
                        animation: { duration: 0 },
                        plugins: {
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                        const value = context.raw;
                                        const percentage = ((value / total) * 100).toFixed(1);
                                        return `${context.dataset.label}: ${value} (${percentage}%)`;
                                    }
                                }
                            }
                        }
                    }
                });
            } catch (error) {
                console.error("Error rendering supervisor chart:", error);
            }
        }

        // Reservation Charts
        if (this.stats.reservationDataByStatus.length && this.reservationStatusChartRef.el) {
            try {
                const statusLabels = this.stats.reservationDataByStatus.map(item => item.status);
                const statusData = this.stats.reservationDataByStatus.map(item => item.status_count);
                const statusColors = statusLabels.map((_, index) => getColor(index + 20));

                this.charts.reservationStatusChart = new Chart(this.reservationStatusChartRef.el, {
                    type: "doughnut",
                    data: {
                        labels: statusLabels,
                        datasets: [{
                            data: statusData,
                            backgroundColor: statusColors,
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        animation: { duration: 0 },
                        plugins: {
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                        const value = context.raw;
                                        const percentage = ((value / total) * 100).toFixed(1);
                                        return `${context.label}: ${value} (${percentage}%)`;
                                    }
                                }
                            },
                            datalabels: {
                                formatter: function(value, context) {
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = ((value / total) * 100).toFixed(1);
                                    return `${percentage}%`;
                                },
                                color: '#fff',
                                anchor: 'center',
                                align: 'center',
                                font: { weight: 'bold' }
                            }
                        }
                    }
                });
            } catch (error) {
                console.error("Error rendering reservation status chart:", error);
            }
        }

       

// 1) “Leads by Source” as a BAR chart
if (
    Array.isArray(this.stats.leadDataBySource) &&
    this.stats.leadDataBySource.length &&
    this.sourceBarChartRef &&
    this.sourceBarChartRef.el
) {
    try {
        const srcLabels = this.stats.leadDataBySource.map(item =>
            item.source_id ? item.source_id[1] : 'Undefined'
        );
        const srcData   = this.stats.leadDataBySource.map(item =>
            item.source_id_count
        );
        const srcColors = srcLabels.map((_, idx) =>
            getColor(idx + 25)
        );

        this.charts.sourceBarChart = new Chart(
            this.sourceBarChartRef.el,
            {
                type: "bar",
                data: {
                    labels: srcLabels,
                    datasets: [{
                        label: 'Leads by Source',
                        data: srcData,
                        backgroundColor: srcColors,
                        borderColor: srcColors.map(c => c.replace('0.6','1')),
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                callback: function(value) {
                                    const total = this.chart.data.datasets[0].data
                                        .reduce((a, b) => a + b, 0);
                                    const pct = ((value / total) * 100).toFixed(1);
                                    return `${value} (${pct}%)`;
                                }
                            }
                        }
                    },
                    plugins: {
                        tooltip: {
                            callbacks: {
                                label: function(ctx) {
                                    const total = ctx.dataset.data
                                        .reduce((a, b) => a + b, 0);
                                    const val = ctx.raw;
                                    const pct = ((val / total) * 100).toFixed(1);
                                    return `${ctx.dataset.label}: ${val} (${pct}%)`;
                                }
                            }
                        }
                    }
                }
            }
        );
    } catch (error) {
        console.error("Error rendering Leads by Source bar chart:", error);
    }
}

// 2) “Leads by Source” as a PIE chart
if (
    Array.isArray(this.stats.leadDataBySource) &&
    this.stats.leadDataBySource.length &&
    this.sourceChartRef &&
    this.sourceChartRef.el
) {
    try {
        const srcLabels = this.stats.leadDataBySource.map(item =>
            item.source_id ? item.source_id[1] : 'Undefined'
        );
        const srcData   = this.stats.leadDataBySource.map(item =>
            item.source_id_count
        );
        const srcColors = srcLabels.map((_, idx) =>
            getColor(idx + 25)
        );

        this.charts.sourceChart = new Chart(
            this.sourceChartRef.el,
            {
                type: "pie",
                data: {
                    labels: srcLabels,
                    datasets: [{
                        data: srcData,
                        backgroundColor: srcColors,
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: { duration: 0 },
                    plugins: {
                        tooltip: {
                            callbacks: {
                                label: function(ctx) {
                                    const total = ctx.dataset.data
                                        .reduce((a, b) => a + b, 0);
                                    const val = ctx.raw;
                                    const pct = ((val / total) * 100).toFixed(1);
                                    return `${ctx.label}: ${val} (${pct}%)`;
                                }
                            }
                        },
                        datalabels: {
                            formatter: function(value, context) {
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const pct = ((value / total) * 100).toFixed(1);
                                return `${pct}%`;
                            },
                            color: '#fff',
                            anchor: 'center',
                            align: 'center',
                            font: { weight: 'bold' }
                        }
                    }
                }
            }
        );
    } catch (error) {
        console.error("Error rendering Leads by Source pie chart:", error);
    }
}

// ...existing code...

        // 2) “Reservation by Status” as a BAR chart
        if (
            Array.isArray(this.stats.reservationDataByStatus) &&
            this.stats.reservationDataByStatus.length &&
            this.reservationBarChartRef &&
            this.reservationBarChartRef.el
        ) {
            try {
                const statLabels = this.stats.reservationDataByStatus.map(item =>
                    item.status
                );
                const statData   = this.stats.reservationDataByStatus.map(item =>
                    item.status_count
                );
                const statColors = statLabels.map((_, idx) =>
                    getColor(idx + 20)
                );

                this.charts.reservationBarChart = new Chart(
                    this.reservationBarChartRef.el,
                    {
                        type: "bar",
                        data: {
                            labels: statLabels,
                            datasets: [{
                                label: 'Reservations by Status',
                                data: statData,
                                backgroundColor: statColors,
                                borderColor: statColors.map(c => c.replace('0.6','1')),
                                borderWidth: 1
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            scales: {
                                y: {
                                    beginAtZero: true,
                                    ticks: {
                                        callback: function(value) {
                                            const total = this.chart.data.datasets[0].data
                                                .reduce((a, b) => a + b, 0);
                                            const pct = ((value / total) * 100).toFixed(1);
                                            return `${value} (${pct}%)`;
                                        }
                                    }
                                }
                            },
                            plugins: {
                                tooltip: {
                                    callbacks: {
                                        label: function(ctx) {
                                            const total = ctx.dataset.data
                                                .reduce((a, b) => a + b, 0);
                                            const val = ctx.raw;
                                            const pct = ((val / total) * 100).toFixed(1);
                                            return `${ctx.dataset.label}: ${val} (${pct}%)`;
                                        }
                                    }
                                }
                            }
                        }
                    }
                );
            } catch (error) {
                console.error("Error rendering Reservation by Status bar chart:", error);
            }
        }

        console.log("Pie chart data", this.stats.leadDataByStage, this.stageChartPieRef.el);

        // All Leads Pie (Sources)
     
// All Leads Pie (Stages)
if (this.stats.leadDataByStage.length && this.stageChartPieRef.el) {
    try {
        const stageLabels = this.stats.leadDataByStage.map(item => item.stage_id[1]);
        const stageData = this.stats.leadDataByStage.map(item => item.stage_id_count);
        const stageColors = stageLabels.map((_, index) => getColor(index + 30));

        this.charts.stageChartPie = new Chart(this.stageChartPieRef.el, {
            type: "pie",
            data: {
                labels: stageLabels,
                datasets: [{
                    data: stageData,
                    backgroundColor: stageColors,
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: { duration: 0 },
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const value = context.raw;
                                const percentage = ((value / total) * 100).toFixed(1);
                                return `${context.label}: ${value} (${percentage}%)`;
                            }
                        }
                    },
                    datalabels: {
                        formatter: function(value, context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${percentage}%`;
                        },
                        color: '#fff',
                        anchor: 'center',
                        align: 'center',
                        font: { weight: 'bold' }
                    }
                }
            }
        });
    } catch (error) {
        console.error("Error rendering stage pie chart:", error);
    }
}

        // All Leads Bar (Stages)
        if (this.stats.leadDataByStage.length && this.stageChartRef.el) {
            try {
                const stageLabels = this.stats.leadDataByStage.map(item => item.stage_id[1]);
                const stageData = this.stats.leadDataByStage.map(item => item.stage_id_count);
                const stageColors = stageLabels.map((_, index) => getColor(index + 30));

                this.charts.stageChart = new Chart(this.stageChartRef.el, {
                    type: "bar",
                    data: {
                        labels: stageLabels,
                        datasets: [{
                            label: 'All Leads by Stage',
                            data: stageData,
                            backgroundColor: stageColors,
                            borderColor: stageColors.map(color => color.replace('0.6', '1')),
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: {
                                beginAtZero: true,
                                ticks: {
                                    callback: function(value) {
                                        const total = this.chart.data.datasets[0].data.reduce((a, b) => a + b, 0);
                                        const percentage = ((value / total) * 100).toFixed(1);
                                        return `${value} (${percentage}%)`;
                                    }
                                }
                            }
                        },
                        animation: { duration: 0 },
                        plugins: {
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                        const value = context.raw;
                                        const percentage = ((value / total) * 100).toFixed(1);
                                        return `${context.dataset.label}: ${value} (${percentage}%)`;
                                    }
                                }
                            }
                        }
                    }
                });
            } catch (error) {
                console.error("Error rendering stage chart:", error);
            }
        }
    };

    // Navigation methods
    goToCRMPage = (filter) => {
        const domain = [];
        
        if (filter === 'callcenter') {
            domain.push(["source_id.name", "=", "6033"]);
        } else if (filter === 'reception') {
            domain.push(["source_id.name", "=", "Walk In"]);
        } else if (filter === 'website') {
            domain.push(["source_id.name", "=", "Website"]);
        }
        
        if (this.dateFilters.startDate) {
            domain.push(['create_date', '>=', this.dateFilters.startDate]);
        }
        if (this.dateFilters.endDate) {
            domain.push(['create_date', '<=', this.dateFilters.endDate + ' 23:59:59']);
        }

        // Apply wing and/or supervisor filters
        if (this.stats.currentSupervisorId) {
            domain.push(['supervisor_id', '=', this.stats.currentSupervisorId]);
        }
        if (this.stats.currentWingId) {
            domain.push(['wing_id', '=', this.stats.currentWingId]);
        }

        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "crm.lead",
            view_mode: "list",
            views: [[false, "list"]],
            target: "current",
            domain: domain,
        });
    };

    goToReservationPage = () => {
        const domain = [];
        
        if (this.dateFilters.startDate) {
            domain.push(['create_date', '>=', this.dateFilters.startDate]);
        }
        if (this.dateFilters.endDate) {
            domain.push(['create_date', '<=', this.dateFilters.endDate + ' 23:59:59']);
        }

        // Apply wing filter if present
        if (this.stats.currentWingId) {
            domain.push(['wing_id', '=', this.stats.currentWingId]);
        }

        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "property.reservation",
            view_mode: "list",
            views: [[false, "list"]],
            target: "current",
            domain: domain,
        });
    };

    goToReceptionPage = () => {
        const domain = [];
        
        if (this.dateFilters.startDate) {
            domain.push(['create_date', '>=', this.dateFilters.startDate]);
        }
        if (this.dateFilters.endDate) {
            domain.push(['create_date', '<=', this.dateFilters.endDate + ' 23:59:59']);
        }

        // Apply wing filter if present
        if (this.stats.currentWingId) {
            domain.push(['wing_id', '=', this.stats.currentWingId]);
        }

        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "crm.reception",
            view_mode: "list",
            views: [[false, "list"]],
            target: "current",
            domain: domain,
        });
    };

    goToSoldPropertiesPage = () => {
        const domain = [
            ['state', '=', 'sold']
        ];
        
        if (this.dateFilters.startDate) {
            domain.push(['create_date', '>=', this.dateFilters.startDate]);
        }
        if (this.dateFilters.endDate) {
            domain.push(['create_date', '<=', this.dateFilters.endDate + ' 23:59:59']);
        }

        // Apply supervisor and/or wing filter if present
        if (this.stats.currentSupervisorId) {
            domain.push(['supervisor_id', '=', this.stats.currentSupervisorId]);
        }
        if (this.stats.currentWingId) {
            domain.push(['wing_id', '=', this.stats.currentWingId]);
        }

        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "property.property",
            view_mode: "list",
            views: [[false, "list"]],
            target: "current",
            domain: domain,
        });
    };

    goToWebsiteLeadsPage = () => {
        const domain = [];
        
        if (this.dateFilters.startDate) {
            domain.push(['create_date', '>=', this.dateFilters.startDate]);
        }
        if (this.dateFilters.endDate) {
            domain.push(['create_date', '<=', this.dateFilters.endDate + ' 23:59:59']);
        }
        domain.push(["source_id.name", "=", "Website"]);

        // Apply wing filter if present
        if (this.stats.currentWingId) {
            domain.push(['wing_id', '=', this.stats.currentWingId]);
        }

        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "crm.lead",
            view_mode: "list",
            views: [[false, "list"]],
            target: "current",
            domain: domain,
        });
    };

    goToActivitiesPage = async () => {
        const domain = [
            ['model', '=', 'crm.lead'],
            ['subtype_id', '=', 3] // Activity subtype
        ];
        
        if (this.dateFilters.startDate) {
            domain.push(['date', '>=', this.dateFilters.startDate]);
        }
        if (this.dateFilters.endDate) {
            domain.push(['date', '<=', this.dateFilters.endDate + ' 23:59:59']);
        }

        // Apply wing filter if present
        if (this.stats.currentWingId) {
            domain.push(['res_id', 'in',
                await this.orm.search('crm.lead', [['wing_id', '=', this.stats.currentWingId]])
            ]);
        }

        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "mail.message",
            view_mode: "list",
            views: [[false, "list"]],
            target: "current",
            domain: domain,
            context: {
                search_default_group_by_activity_type: 1,
                search_default_group_by_author: 1
            }
        });
    };

    goToOtherLeadsPage = () => {
        const domain = [];
        
        // Get source IDs to exclude
        const excludedSources = [];
        if (this.stats.totalCallCenterLeads > 0) {
            excludedSources.push(["source_id.name", "!=", "6033"]);
        }
        if (this.stats.totalReceptionLeads > 0) {
            excludedSources.push(["source_id.name", "!=", "Walk In"]);
        }
        if (this.stats.totalWebsiteLeads > 0) {
            excludedSources.push(["source_id.name", "!=", "Website"]);
        }
        
        if (excludedSources.length > 0) {
            domain.push(["|", ...excludedSources]);
        }
        
        if (this.dateFilters.startDate) {
            domain.push(['create_date', '>=', this.dateFilters.startDate]);
        }
        if (this.dateFilters.endDate) {
            domain.push(['create_date', '<=', this.dateFilters.endDate + ' 23:59:59']);
        }

        // Apply supervisor and/or wing filter if present
        if (this.stats.currentSupervisorId) {
            domain.push(['supervisor_id', '=', this.stats.currentSupervisorId]);
        }
        if (this.stats.currentWingId) {
            domain.push(['wing_id', '=', this.stats.currentWingId]);
        }

        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "crm.lead",
            view_mode: "list",
            views: [[false, "list"]],
            target: "current",
            domain: domain,
        });
    };

    onSearchQueryChange = (event) => {
        this.searchQuery.value = event.target.value;
    };

    applyDateFilter = async () => {
        await this.fetchStats();
        this.renderCharts();
    };

    resetDateFilter = async () => {
        this.dateFilters.startDate = this.getDefaultStartDate();
        this.dateFilters.endDate = this.getDefaultEndDate();
        await this.fetchStats();
        this.renderCharts();
    };
}

ChartjsSampleCRM.template = "crm_dashboard.chartjs_sample_crm";
actionRegistry.add("chartjs_sample_crm", ChartjsSampleCRM);

