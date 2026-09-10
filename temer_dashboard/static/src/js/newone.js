/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useRef, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { loadJS } from "@web/core/assets";
import { getColor } from "@web/core/colors/colors";

const actionRegistry = registry.category("actions");

export class ChartjsSampleCRM extends Component {
    
    // getDefaultStartDate() {
    //     const date = new Date();
    //     date.setDate(date.getDate() - 30); // Go back 30 days
    //     return date.toISOString().split('T')[0]; // Format as YYYY-MM-DD
    // }

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
            currentWingId: null
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
            activityTypeChart: null
        };

        // Initial setup
        onWillStart(async () => {
            await loadJS(["/web/static/lib/Chart/Chart.js"]);
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

    // getDefaultStartDate = () => {
    //     const date = new Date();
    //     date.setMonth(date.getMonth() - 1);
    //     return date.toISOString().split('T')[0];
    // };

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
            stageChart: null,
            reservationStatusChart: null,
            wingChart: null,
            supervisorChart: null,
            websiteChart: null,
            activityTypeChart: null
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
            totalSoldProperties
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
            this.orm.searchCount("property.property", propertyDomain)
        ]);

        // Get total leads count
        const totalLeads = await this.orm.searchCount("crm.lead", leadDomain);
        const totalOtherLeads = totalLeads - totalCallCenterLeads - totalReceptionLeads - totalWebsiteLeads;

        // Get activity counts from CRM messages
const activityMessages = await this.orm.searchRead(
    "mail.message",
    [
        ['model', '=', 'crm.lead'],
        ['date', '>=', this.dateFilters.startDate],
        ['date', '<=', this.dateFilters.endDate + ' 23:59:59'],
        '|',
        ['subtype_id', '=', 3], // Activity subtype
        ['body', 'ilike', 'Lead/Opportunity created with phone']
    ],
    ['mail_activity_type_id', 'subtype_id', 'body']
);

// Process activity counts for all 5 types
const activityCounts = {
    email: activityMessages.filter(msg => 
        msg.mail_activity_type_id && msg.mail_activity_type_id[0] === 1  // Email
    ).length,
    call: activityMessages.filter(msg => 
        msg.mail_activity_type_id && msg.mail_activity_type_id[0] === 4  // Call
    ).length,
    office_visit: activityMessages.filter(msg => 
        msg.mail_activity_type_id && msg.mail_activity_type_id[0] === 8  // Office Visit
    ).length,
    site_visit: activityMessages.filter(msg => 
        msg.mail_activity_type_id && msg.mail_activity_type_id[0] === 9  // Site Visit
    ).length,
    sms: activityMessages.filter(msg => 
        msg.mail_activity_type_id && msg.mail_activity_type_id[0] === 5  // SMS
    ).length
};

// Get activity type data for the chart (all 5 types)
const activityTypeData = await this.orm.readGroup(
    "mail.message",
    [
        ['model', '=', 'crm.lead'],
        ['date', '>=', this.dateFilters.startDate],
        ['date', '<=', this.dateFilters.endDate + ' 23:59:59'],
        ['subtype_id', '=', 3], // Activity subtype
        ['mail_activity_type_id', 'in', [1, 4, 5, 8, 9]] // Email, Call, SMS, Office Visit, Site Visit
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

// Add prospect count if needed (from message body)
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

        // // Add the "Prospect" type which comes from message body
        // const prospectCount = await this.orm.searchCount("mail.message", [
        //     ['model', '=', 'crm.lead'],
        //     ['date', '>=', this.dateFilters.startDate],
        //     ['date', '<=', this.dateFilters.endDate + ' 23:59:59'],
        //     ['body', 'ilike', 'Lead/Opportunity created with phone']
        // ]);

        // if (prospectCount > 0) {
        //     processedActivityData.push({
        //         name: 'Prospect',
        //         count: prospectCount
        //     });
        // }

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
        this.stats.websiteLeadDataByStage = websiteLeadDataByStage;
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
                        animation: {
                            duration: 0
                        },
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
                        animation: {
                            duration: 0
                        },
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
                                font: {
                                    weight: 'bold'
                                }
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
                        animation: {
                            duration: 0
                        },
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
                        animation: {
                            duration: 0
                        },
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
                                font: {
                                    weight: 'bold'
                                }
                            }
                        }
                    }
                });
            } catch (error) {
                console.error("Error rendering reception charts:", error);
            }
        }

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
                        animation: {
                            duration: 0
                        },
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

        // Activity Type Chart
        if (this.stats.activityTypeData.length && this.activityTypeChartRef.el) {
            try {
                const labels = this.stats.activityTypeData.map(item => item.name);
                const data = this.stats.activityTypeData.map(item => item.count);
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
                        animation: {
                            duration: 0
                        },
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
                                font: {
                                    weight: 'bold'
                                }
                            }
                        }
                    }
                });
            } catch (error) {
                console.error("Error rendering activity type chart:", error);
            }
        }

        // Wing and Supervisor Charts
        if (Object.keys(this.stats.wingLeads).length && this.wingChartRef.el && !this.stats.isSupervisor) {
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
                        animation: {
                            duration: 0
                        },
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

        if (Object.keys(this.stats.supervisorLeads).length && this.supervisorChartRef.el && !this.stats.isSupervisor) {
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
                        animation: {
                            duration: 0
                        },
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
                        animation: {
                            duration: 0
                        },
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
                                font: {
                                    weight: 'bold'
                                }
                            }
                        }
                    }
                });
            } catch (error) {
                console.error("Error rendering reservation status chart:", error);
            }
        }

        // All Leads Charts
        if (this.stats.leadDataBySource.length && this.sourceChartRef.el) {
            try {
                const sourceLabels = this.stats.leadDataBySource.map(item => item.source_id ? item.source_id[1] : 'Undefined');
                const sourceData = this.stats.leadDataBySource.map(item => item.source_id_count);
                const sourceColors = sourceLabels.map((_, index) => getColor(index + 25));

                this.charts.sourceChart = new Chart(this.sourceChartRef.el, {
                    type: "doughnut",
                    data: {
                        labels: sourceLabels,
                        datasets: [{
                            data: sourceData,
                            backgroundColor: sourceColors,
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
                                font: {
                                    weight: 'bold'
                                }
                            }
                        }
                    }
                });
            } catch (error) {
                console.error("Error rendering source chart:", error);
            }
        }

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
                        animation: {
                            duration: 0
                        },
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

        // Add supervisor/wing filters if user is supervisor
        if (this.stats.isSupervisor) {
            if (this.stats.currentSupervisorId) {
                domain.push(['supervisor_id', '=', this.stats.currentSupervisorId]);
            }
            if (this.stats.currentWingId) {
                domain.push(['wing_id', '=', this.stats.currentWingId]);
            }
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

    // Add supervisor/wing filters if user is supervisor
    if (this.stats.isSupervisor) {
        if (this.stats.currentSupervisorId) {
            domain.push(['supervisor_id', '=', this.stats.currentSupervisorId]);
        }
        if (this.stats.currentWingId) {
            domain.push(['wing_id', '=', this.stats.currentWingId]);
        }
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

        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "crm.lead",
            view_mode: "list",
            views: [[false, "list"]],
            target: "current",
            domain: domain,
        });
    };

    goToActivitiesPage = () => {
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

        // Add supervisor/wing filters if user is supervisor
        if (this.stats.isSupervisor) {
            if (this.stats.currentSupervisorId) {
                domain.push(['supervisor_id', '=', this.stats.currentSupervisorId]);
            }
            if (this.stats.currentWingId) {
                domain.push(['wing_id', '=', this.stats.currentWingId]);
            }
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



