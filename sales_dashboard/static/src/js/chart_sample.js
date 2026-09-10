/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

export class SupervisorDashboard extends Component {
    static template = "sales_dashboard.supervisor_dashboard_jjokacha";

    setup() {
        this.orm = useService("orm");
        this.user = useService("user");
        this.state = useState({
            loading: true,
            filters: {
                date_from: this.getDefaultDateFrom(),
                date_to: this.getDefaultDateTo(),
                supervisor_id: null,
                supervisor_name: "",
            },
            combinedStatusCounts: {
                prospect: 0,
                followUp: 0,
                reservation: 0,
                won: 0,
                expired: 0,
                lost: 0,
                total: 0,
            },
            detailedSalesPerformance: [],
            activitiesPerformance: [], // New state for activities performance
        });

        onWillStart(async () => {
            try {
                const [userData] = await this.orm.read("res.users", [this.user.userId], ["name"]);
                console.log("User Data:", userData);
                const supervisorRecords = await this.orm.searchRead(
                    "property.sales.supervisor",
                    [],
                    ["id", "name"]
                );
                console.log("Supervisor Records:", supervisorRecords);
                const userSupervisor = supervisorRecords.find(s => s.name && s.name.includes(userData.name));
                if (userSupervisor) {
                    this.state.filters.supervisor_id = userSupervisor.id;
                    this.state.filters.supervisor_name = userSupervisor.name;
                } else {
                    this.state.filters.supervisor_name = userData.name;
                }
                await this.loadDashboardData();
            } catch (error) {
                console.error("Error in setup:", error);
                this.state.filters.supervisor_name = this.user.name;
            }
        });
    }

    getDefaultDateFrom() {
        const date = new Date();
        date.setMonth(0);
        date.setDate(1);
        return this.formatDate(date);
    }

    getDefaultDateTo() {
        const date = new Date();
        date.setMonth(11);
        date.setDate(31);
        return this.formatDate(date);
    }

    formatDate(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    async loadDashboardData() {
        this.state.loading = true;
        try {
            let domain = [
                ["create_date", ">=", this.state.filters.date_from],
                ["create_date", "<=", this.state.filters.date_to]
            ];
            if (this.state.filters.supervisor_id) {
                domain.push(["supervisor_id", "=", this.state.filters.supervisor_id]);
            }

            const leads = await this.orm.searchRead(
                "crm.lead",
                domain,
                ["id", "stage_id", "user_id", "supervisor_id", "wing_id", "create_date"]
            );
            console.log("Leads Retrieved:", leads.length, leads);

            if (leads.length === 0) {
                console.warn("No leads found for the given filters.");
                this.state.detailedSalesPerformance = [];
                this.state.activitiesPerformance = [];
                this.resetCounts();
                return;
            }

            const leadIds = leads.map(lead => lead.id);
            const stageIds = [...new Set(leads.map(lead => lead.stage_id[0]))];
            const userIds = [...new Set(leads.map(lead => lead.user_id[0]))];
            const supervisorIds = [...new Set(leads.filter(lead => lead.supervisor_id).map(lead => lead.supervisor_id[0]))];
            const wingIds = [...new Set(leads.filter(lead => lead.wing_id).map(lead => lead.wing_id[0]))];

            const [
                stages,
                users,
                supervisors,
                wings,
                activities,
                messages,
                reservations
            ] = await Promise.all([
                this.orm.read("crm.stage", stageIds, ["id", "name"]),
                this.orm.read("res.users", userIds, ["id", "name", "partner_id"]),
                this.orm.read("property.sales.supervisor", supervisorIds, ["id", "name"]),
                this.orm.read("property.sales.wing", wingIds, ["id", "name", "manager_id"]),
                this.orm.searchRead(
                    "mail.activity",
                    [
                        ["res_model", "=", "crm.lead"],
                        ["res_id", "in", leadIds],
                        ["date_deadline", ">=", this.state.filters.date_from],
                        ["date_deadline", "<=", this.state.filters.date_to]
                    ],
                    ["id", "activity_type_id", "res_id", "date_deadline"]
                ),
                this.orm.searchRead(
                    "mail.message",
                    [
                        ["model", "=", "crm.lead"],
                        ["res_id", "in", leadIds],
                        ["date", ">=", this.state.filters.date_from],
                        ["date", "<=", this.state.filters.date_to]
                    ],
                    ["id", "subtype_id", "res_id", "date", "mail_activity_type_id"]
                ),
                this.orm.searchRead(
                    "property.reservation",
                    [["crm_lead_id", "in", leadIds]],
                    ["id", "crm_lead_id"]
                )
            ]);

            console.log("Stages:", stages.length);
            console.log("Users:", users.length);
            console.log("Supervisors:", supervisors.length);
            console.log("Wings:", wings.length);
            console.log("Activities:", activities.length);
            console.log("Messages:", messages.length);
            console.log("Reservations:", reservations.length);

            const stageMap = Object.fromEntries(stages.map(s => [s.id, s]));
            const userMap = Object.fromEntries(users.map(u => [u.id, u]));
            const supervisorMap = Object.fromEntries(supervisors.map(s => [s.id, s]));
            const wingMap = Object.fromEntries(wings.map(w => [w.id, w]));

            const processedData = this.processData(
                leads,
                stageMap,
                userMap,
                supervisorMap,
                wingMap,
                activities,
                messages,
                reservations
            );

            this.updateDashboardData(processedData);
        } catch (error) {
            console.error("Error loading dashboard data:", error);
            this.state.detailedSalesPerformance = [];
            this.state.activitiesPerformance = [];
            this.resetCounts();
        } finally {
            this.state.loading = false;
        }
    }

    processData(leads, stageMap, userMap, supervisorMap, wingMap, activities, messages, reservations) {
        const groupedData = {};

        // Process leads for status counts
        leads.forEach(lead => {
            const stage = stageMap[lead.stage_id[0]];
            const user = userMap[lead.user_id[0]];
            const supervisor = lead.supervisor_id ? supervisorMap[lead.supervisor_id[0]] : null;
            const wing = lead.wing_id ? wingMap[lead.wing_id[0]] : null;

            let stageName = "";
            try {
                if (stage && stage.name) {
                    if (typeof stage.name === 'string') {
                        try {
                            const parsed = JSON.parse(stage.name);
                            stageName = parsed.en_US || stage.name;
                        } catch {
                            stageName = stage.name;
                        }
                    } else if (typeof stage.name === 'object') {
                        stageName = stage.name.en_US || "";
                    }
                }
            } catch (e) {
                console.error("Error parsing stage name:", e);
            }

            let eventType = "";
            stageName = stageName.toLowerCase();
            if (stageName.includes('expired')) {
                eventType = "Expired";
            } else if (stageName.includes('won')) {
                eventType = "Won";
            } else if (stageName.includes('reservation')) {
                eventType = "Reservation";
            } else if (stageName.includes('lost')) {
                eventType = "Lost";
            } else if (stageName.includes('follow')) {
                eventType = "Follow Up";
            } else if (stageName.includes('prospect')) {
                eventType = "Prospect";
            }

            const key = `${wing?.name || "No Wing"}|${supervisor?.name || "No Supervisor"}|${user?.name || "Unknown"}`;

            if (!groupedData[key]) {
                groupedData[key] = {
                    wing_name: wing?.name || "No Wing",
                    supervisor_name: supervisor?.name || "No Supervisor",
                    sales_person: user?.name || "Unknown",
                    reservation_count: 0,
                    won_count: 0,
                    expired_count: 0,
                    lost_count: 0,
                    follow_up_count: 0,
                    prospect_count: 0,
                    office_visit_count: 0,
                    site_visit_count: 0,
                    email_count: 0,
                    sms_count: 0,
                    call_count: 0,
                    total_events: 0,
                    total_key_events: 0
                };
            }

            if (eventType) {
                switch (eventType) {
                    case "Reservation": groupedData[key].reservation_count++; break;
                    case "Won": groupedData[key].won_count++; break;
                    case "Expired": groupedData[key].expired_count++; break;
                    case "Lost": groupedData[key].lost_count++; break;
                    case "Follow Up": groupedData[key].follow_up_count++; break;
                    case "Prospect": groupedData[key].prospect_count++; break;
                }
                groupedData[key].total_events++;
            }
        });

        // Process activities and messages for activity counts
        const unionedEvents = [...activities, ...messages];
        console.log("Unioned Events:", unionedEvents.length);
        unionedEvents.forEach(event => {
            const lead = leads.find(l => l.id === event.res_id);
            if (!lead) {
                console.warn("No lead found for event res_id:", event.res_id);
                return;
            }

            const user = userMap[lead.user_id[0]];
            const supervisor = lead.supervisor_id ? supervisorMap[lead.supervisor_id[0]] : null;
            const wing = lead.wing_id ? wingMap[lead.wing_id[0]] : null;

            const key = `${wing?.name || "No Wing"}|${supervisor?.name || "No Supervisor"}|${user?.name || "Unknown"}`;

            if (!groupedData[key]) {
                groupedData[key] = {
                    wing_name: wing?.name || "No Wing",
                    supervisor_name: supervisor?.name || "No Supervisor",
                    sales_person: user?.name || "Unknown",
                    reservation_count: 0,
                    won_count: 0,
                    expired_count: 0,
                    lost_count: 0,
                    follow_up_count: 0,
                    prospect_count: 0,
                    office_visit_count: 0,
                    site_visit_count: 0,
                    email_count: 0,
                    sms_count: 0,
                    call_count: 0,
                    total_events: 0,
                    total_key_events: 0
                };
            }

            let eventType = null;
            if (event.activity_type_id) { // From mail.activity
                console.log("Activity event:", event.activity_type_id[0]);
                switch (event.activity_type_id[0]) {
                    case 1: eventType = "Email"; break;
                    case 2: eventType = "SMS"; break;
                    case 4: eventType = "Call"; break;
                    case 8: eventType = "Office Visit"; break;
                    case 9: eventType = "Site Visit"; break;
                }
            } else if (event.subtype_id) { // From mail.message
                console.log("Message event:", event.subtype_id[0], event.mail_activity_type_id);
                if (event.subtype_id[0] === 3 && event.mail_activity_type_id) {
                    switch (event.mail_activity_type_id[0]) {
                        case 1: eventType = "Email"; break;
                        case 2: eventType = "SMS"; break;
                        case 4: eventType = "Call"; break;
                        case 8: eventType = "Office Visit"; break;
                        case 9: eventType = "Site Visit"; break;
                    }
                }
            }

            if (eventType) {
                console.log("Event Type Assigned:", eventType, "for key:", key);
                switch (eventType) {
                    case "Office Visit": groupedData[key].office_visit_count++; break;
                    case "Site Visit": groupedData[key].site_visit_count++; break;
                    case "Email": groupedData[key].email_count++; break;
                    case "SMS": groupedData[key].sms_count++; break;
                    case "Call": groupedData[key].call_count++; break;
                }
                groupedData[key].total_key_events++;
            }
        });

        // Process reservations
        console.log("Processing Reservations:", reservations.length);
        reservations.forEach(reservation => {
            const lead = leads.find(l => l.id === reservation.crm_lead_id);
            if (!lead) {
                console.warn("No lead found for reservation crm_lead_id:", reservation.crm_lead_id);
                return;
            }

            const user = userMap[lead.user_id[0]];
            const supervisor = lead.supervisor_id ? supervisorMap[lead.supervisor_id[0]] : null;
            const wing = lead.wing_id ? wingMap[lead.wing_id[0]] : null;

            const key = `${wing?.name || "No Wing"}|${supervisor?.name || "No Supervisor"}|${user?.name || "Unknown"}`;

            if (!groupedData[key]) {
                groupedData[key] = {
                    wing_name: wing?.name || "No Wing",
                    supervisor_name: supervisor?.name || "No Supervisor",
                    sales_person: user?.name || "Unknown",
                    reservation_count: 0,
                    won_count: 0,
                    expired_count: 0,
                    lost_count: 0,
                    follow_up_count: 0,
                    prospect_count: 0,
                    office_visit_count: 0,
                    site_visit_count: 0,
                    email_count: 0,
                    sms_count: 0,
                    call_count: 0,
                    total_events: 0,
                    total_key_events: 0
                };
            }

            groupedData[key].reservation_count++;
            groupedData[key].total_events++;
        });

        // Calculate total_key_events for activities
        Object.values(groupedData).forEach(row => {
            row.total_key_events = (
                row.office_visit_count +
                row.site_visit_count +
                row.email_count +
                row.sms_count +
                row.call_count
            );
        });

        console.log("Processed Data:", Object.values(groupedData));
        return Object.values(groupedData);
    }

    updateDashboardData(data) {
        this.state.detailedSalesPerformance = data.map(item => {
            return {
                wing_name: item.wing_name,
                supervisor_name: item.supervisor_name,
                sales_person: item.sales_person,
                reservation_count: item.reservation_count,
                won_count: item.won_count,
                expired_count: item.expired_count,
                lost_count: item.lost_count,
                follow_up_count: item.follow_up_count,
                prospect_count: item.prospect_count,
                office_visit_count: item.office_visit_count,
                site_visit_count: item.site_visit_count,
                email_count: item.email_count,
                sms_count: item.sms_count,
                call_count: item.call_count,
                total_events: item.total_events,
                total_key_events: item.total_key_events
            }
        });
        const counts = {
            prospect: 0,
            followUp: 0,
            reservation: 0,
            won: 0,
            expired: 0,
            lost: 0,
            total: 0,
        };

        data.forEach(row => {
            counts.prospect += row.prospect_count || 0;
            counts.followUp += row.follow_up_count || 0;
            counts.reservation += row.reservation_count || 0;
            counts.won += row.won_count || 0;
            counts.expired += row.expired_count || 0;
            counts.lost += row.lost_count || 0;
        });

        counts.total = counts.prospect + counts.followUp + counts.reservation +
                      counts.won + counts.expired + counts.lost;

        this.state.combinedStatusCounts = counts;
        console.log("Combined Status Counts:", counts);
    }

    resetCounts() {
        this.state.combinedStatusCounts = {
            prospect: 0,
            followUp: 0,
            reservation: 0,
            won: 0,
            expired: 0,
            lost: 0,
            total: 0,
        };
    }

    setDateFrom(ev) {
        this.state.filters.date_from = ev.target.value;
        this.loadDashboardData();
    }

    setDateTo(ev) {
        this.state.filters.date_to = ev.target.value;
        this.loadDashboardData();
    }
}

registry.category("actions").add("supervisor_dashboard_jjokacha", SupervisorDashboard);