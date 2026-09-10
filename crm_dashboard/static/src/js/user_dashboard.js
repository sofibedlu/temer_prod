/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState } from "@odoo/owl";

class UserDashboard extends Component {
    setup() {
        this.orm = useService('orm');
        this.action = useService("action");
        this.user = useService("user");
        
        this.state = useState({
            userId: this.user.userId,
            userLeads: 0,
            userProspects: 0,
            userActivities: 0,
            loading: false
        });

        this.loadUserData();
    }

    async loadUserData() {
        this.state.loading = true;
        try {
            const [leads, prospects, activities] = await Promise.all([
                this.orm.searchCount("crm.lead", this.getUserLeadDomain()),
                this.orm.searchCount("crm.lead", this.getUserProspectDomain()),
                this.orm.searchCount("mail.activity", this.getUserActivityDomain())
            ]);
            
            this.state.userLeads = leads;
            this.state.userProspects = prospects;
            this.state.userActivities = activities;
        } finally {
            this.state.loading = false;
        }
    }

    getUserLeadDomain() {
        return [
            ['user_id', '=', this.state.userId],
            ['create_date', '>=', this.props.startDate],
            ['create_date', '<=', this.props.endDate]
        ];
    }

    getUserProspectDomain() {
        return [
            ...this.getUserLeadDomain(),
            ['stage_id.name', 'ilike', 'Prospect']
        ];
    }

    getUserActivityDomain() {
        return [
            ['res_model', '=', 'crm.lead'],
            ['user_id', '=', this.state.userId],
            ['date_deadline', '>=', this.props.startDate],
            ['date_deadline', '<=', this.props.endDate]
        ];
    }

    // Navigation methods
    goToMyLeads() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "crm.lead",
            views: [[false, "list"], [false, "form"]],
            domain: this.getUserLeadDomain(),
            context: {
                search_default_filter_my_leads: 1
            }
        });
    }

    goToMyProspects() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "crm.lead",
            views: [[false, "list"], [false, "form"]],
            domain: this.getUserProspectDomain(),
            context: {
                search_default_filter_my_prospects: 1
            }
        });
    }

    goToMyActivities() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "mail.activity",
            views: [[false, "list"], [false, "form"]],
            domain: this.getUserActivityDomain(),
            context: {
                search_default_filter_my_activities: 1
            }
        });
    }
}

UserDashboard.template = "crm_dashboard.UserDashboard";
UserDashboard.props = {
    startDate: { type: String },
    endDate: { type: String }
};

registry.category("actions").add("user_dashboard", UserDashboard);