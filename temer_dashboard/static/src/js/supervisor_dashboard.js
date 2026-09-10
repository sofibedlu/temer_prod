/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState } from "@odoo/owl";

class SupervisorDashboard extends Component {
    setup() {
        this.orm = useService('orm');
        this.action = useService("action");
        this.user = useService("user");
        
        this.state = useState({
            loading: false,
            teamLeads: 0,
            teamProspects: 0,
            teamActivities: 0
        });

        this.loadSupervisorData();
    }

    async loadSupervisorData() {
        this.state.loading = true;
        try {
            const [leads, prospects, activities] = await Promise.all([
                this.orm.searchCount("crm.lead", this.getTeamLeadDomain()),
                this.orm.searchCount("crm.lead", this.getTeamProspectDomain()),
                this.orm.searchCount("mail.activity", this.getTeamActivityDomain())
            ]);
            
            this.state.teamLeads = leads;
            this.state.teamProspects = prospects;
            this.state.teamActivities = activities;
        } finally {
            this.state.loading = false;
        }
    }

    getTeamLeadDomain() {
        return [
            ['supervisor_id', '=', this.user.userId],
            ['create_date', '>=', this.props.startDate],
            ['create_date', '<=', this.props.endDate]
        ];
    }

    getTeamProspectDomain() {
        return [
            ...this.getTeamLeadDomain(),
            ['stage_id.name', 'ilike', 'Prospect']
        ];
    }

    getTeamActivityDomain() {
        return [
            ['res_model', '=', 'crm.lead'],
            ['supervisor_id', '=', this.user.userId],
            ['date_deadline', '>=', this.props.startDate],
            ['date_deadline', '<=', this.props.endDate]
        ];
    }

    // Navigation methods
    goToTeamLeads() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "crm.lead",
            views: [[false, "list"], [false, "form"]],
            domain: this.getTeamLeadDomain(),
            context: {
                search_default_filter_team_leads: 1
            }
        });
    }

    goToTeamProspects() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "crm.lead",
            views: [[false, "list"], [false, "form"]],
            domain: this.getTeamProspectDomain(),
            context: {
                search_default_filter_team_prospects: 1
            }
        });
    }

    goToTeamActivities() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "mail.activity",
            views: [[false, "list"], [false, "form"]],
            domain: this.getTeamActivityDomain(),
            context: {
                search_default_filter_team_activities: 1
            }
        });
    }
}

SupervisorDashboard.template = "crm_dashboard.SupervisorDashboard";
SupervisorDashboard.props = {
    startDate: { type: String },
    endDate: { type: String }
};

registry.category("actions").add("supervisor_dashboard", SupervisorDashboard);