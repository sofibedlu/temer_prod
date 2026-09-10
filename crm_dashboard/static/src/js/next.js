// /** @odoo-module **/

// import { registry } from "@web/core/registry";
// import { useService } from "@web/core/utils/hooks";
// import { Component, onWillStart, useRef, onMounted, onWillUnmount, useState } from "@odoo/owl";
// import { loadJS } from "@web/core/assets";
// import { getColor } from "@web/core/colors/colors";

// class UserDashboard extends Component {
//     setup() {
//         this.orm = useService('orm');
//         this.action = useService("action");
//         this.user = useService("user");
        
//         this.state = useState({
//             userId: null,
//             userLeads: 0,
//             userProspects: 0,
//             userActivities: 0,
//             startDate: this.getDefaultStartDate(),
//             endDate: this.getDefaultEndDate(),
//             loading: true
//         });

//         onWillStart(async () => {
//             await loadJS("/web/static/lib/Chart/Chart.js");
//             await this.loadUserData();
//         });
//     }

//     getDefaultStartDate() {
//         const date = new Date();
//         date.setDate(date.getDate() - 30);
//         return date.toISOString().split('T')[0];
//     }

//     getDefaultEndDate() {
//         return new Date().toISOString().split('T')[0];
//     }

//     async loadUserData() {
//         try {
//             this.state.loading = true;
//             this.state.userId = this.user.userId;

//             const [leads, prospects, activities] = await Promise.all([
//                 this.orm.searchCount("crm.lead", this.getUserLeadDomain()),
//                 this.orm.searchCount("crm.lead", this.getUserProspectDomain()),
//                 this.orm.searchCount("mail.activity", this.getUserActivityDomain())
//             ]);

//             this.state.userLeads = leads;
//             this.state.userProspects = prospects;
//             this.state.userActivities = activities;
//         } catch (error) {
//             console.error("Error loading user data:", error);
//         } finally {
//             this.state.loading = false;
//         }
//     }

//     getUserLeadDomain() {
//         const domain = [
//             ['user_id', '=', this.state.userId],
//             ['create_date', '>=', this.state.startDate],
//             ['create_date', '<=', this.state.endDate + ' 23:59:59']
//         ];
//         return domain;
//     }

//     getUserProspectDomain() {
//         return [
//             ...this.getUserLeadDomain(),
//             ['stage_id.name', 'ilike', 'Prospect']
//         ];
//     }

//     getUserActivityDomain() {
//         return [
//             ['res_model', '=', 'crm.lead'],
//             ['user_id', '=', this.state.userId],
//             ['date_deadline', '>=', this.state.startDate],
//             ['date_deadline', '<=', this.state.endDate]
//         ];
//     }

//     goToMyLeads() {
//         this.action.doAction({
//             type: "ir.actions.act_window",
//             res_model: "crm.lead",
//             view_mode: "list,form",
//             domain: this.getUserLeadDomain(),
//             context: {
//                 search_default_filter_my_leads: 1
//             }
//         });
//     }

//     goToMyProspects() {
//         this.action.doAction({
//             type: "ir.actions.act_window",
//             res_model: "crm.lead",
//             view_mode: "list,form",
//             domain: this.getUserProspectDomain(),
//             context: {
//                 search_default_filter_my_prospects: 1
//             }
//         });
//     }

//     goToMyActivities() {
//         this.action.doAction({
//             type: "ir.actions.act_window",
//             res_model: "mail.activity",
//             view_mode: "list,form",
//             domain: this.getUserActivityDomain(),
//             context: {
//                 search_default_filter_my_activities: 1
//             }
//         });
//     }
// }

// UserDashboard.template = "crm_dashboard.UserDashboard";
// UserDashboard.components = {};

// registry.category("actions").add("crm_dashboard.user_dashboard", UserDashboard);



/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useRef, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { loadJS } from "@web/core/assets";
import { getColor } from "@web/core/colors/colors";

class UserDashboard extends Component {
    setup() {
        this.orm = useService('orm');
        this.action = useService("action");
        this.user = useService("user");
        
        this.state = useState({
            userId: null,
            userLeads: 0,
            userProspects: 0,
            userActivities: 0,
            startDate: this.getDefaultStartDate(),
            endDate: this.getDefaultEndDate(),
            loading: true
        });

        onWillStart(async () => {
            await loadJS("/web/static/lib/Chart/Chart.js");
            await this.loadUserData();
        });
    }

    getDefaultStartDate() {
        const date = new Date();
        date.setDate(date.getDate() - 30);
        return date.toISOString().split('T')[0];
    }

    getDefaultEndDate() {
        return new Date().toISOString().split('T')[0];
    }

    async loadUserData() {
        try {
            this.state.loading = true;
            this.state.userId = this.user.userId;

            const [leads, prospects, activities] = await Promise.all([
                this.orm.searchCount("crm.lead", this.getUserLeadDomain()),
                this.orm.searchCount("crm.lead", this.getUserProspectDomain()),
                this.orm.searchCount("mail.activity", this.getUserActivityDomain())
            ]);

            this.state.userLeads = leads;
            this.state.userProspects = prospects;
            this.state.userActivities = activities;
        } catch (error) {
            console.error("Error loading user data:", error);
        } finally {
            this.state.loading = false;
        }
    }

    getUserLeadDomain() {
        const domain = [
            ['user_id', '=', this.state.userId],
            ['create_date', '>=', this.state.startDate],
            ['create_date', '<=', this.state.endDate + ' 23:59:59']
        ];
        return domain;
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
            ['date_deadline', '>=', this.state.startDate],
            ['date_deadline', '<=', this.state.endDate]
        ];
    }

    goToMyLeads() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "crm.lead",
            view_mode: "list,form",
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
            view_mode: "list,form",
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
            view_mode: "list,form",
            domain: this.getUserActivityDomain(),
            context: {
                search_default_filter_my_activities: 1
            }
        });
    }
}

UserDashboard.template = "crm_dashboard.UserDashboard";
UserDashboard.components = {};

registry.category("actions").add("crm_dashboard.user_dashboard", UserDashboard);