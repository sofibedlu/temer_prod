odoo.define('temer_structure.form_view_restriction', function (require) {
    "use strict";

    var FormController = require('web.FormController');

    FormController.include({
        /**
         * Override the method that handles record loading.
         */
        _onRecordLoaded: function (record) {
            // Check if the user is allowed to view the form
            if (!this._checkFormAccess(record)) {
                // Show a warning and redirect to list view
                this.do_warn("Access Denied", "You are not allowed to view this record in the form view.");
                return this.do_action({
                    type: 'ir.actions.act_window',
                    res_model: this.modelName,
                    views: [[false, 'list']],
                    target: 'current'
                });
            }
            // If allowed, proceed as normal
            return this._super(record);
        },

        /**
         * Custom function to determine if form view access is allowed.
         * You can modify this logic as needed.
         */
        _checkFormAccess: function (record) {
            var currentUserId = this.session.uid;
            // Condition 1: Allow if the current user is the record's creator.
            if (record.data.create_uid && record.data.create_uid[0] === currentUserId) {
                return true;
            }
            // Condition 2: Allow if the current user belongs to a specific group.
            // Replace 'your_module.group_special' with your actual group external ID.
            if (this.session.group_ids && this.session.group_ids.indexOf(
                this.env.models['res.groups'].prototype.get_group_id('ahadubit_crm.crm_res_groups_view_all_activity1')
            ) !== -1) {
                return true;
            }
            // Otherwise, access is not allowed.
            return false;
        },
    });
});
