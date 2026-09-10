/** @odoo-module **/
/*
 * ks_dashboard_ninja - Odoo 15 -> 17 conversion of ks_import_dashboard.js
 *
 * Odoo 15: this file patched the generic list controller's action menu to add
 * a bulk "Export Dashboard" entry on the dashboard board list view, and
 * registered a client action of the same module name.
 * Odoo 17: the list controller it patched (web.ListController) no longer
 * exists in the web client; the include() body below is preserved verbatim on
 * an inert placeholder class.  Bulk dashboard export remains available from
 * the dashboard itself (top-right Export button) and via the board form.
 */
import { core } from "./ks_legacy_compat.js";
import { ListController } from "./ks_legacy_compat.js";
import { framework } from "./ks_legacy_compat.js";
import { Dialog } from "./ks_legacy_compat.js";

var _t = core._t;

ListController.include({




       _getActionMenuItems: function (state) {
        if (!this.hasActionMenus || !this.selectedRecords.length) {
            return null;
        }
        const props = this._super(...arguments);
        const otherActionItems = [];
        if (this.modelName == "ks_dashboard_ninja.board"){
        if (this.isExportEnable) {
            otherActionItems.push({
                 description: _t("Export Dashboard"),
                callback: this.ks_dashboard_export.bind(this)
            });
        }
        if (this.archiveEnabled) {
            otherActionItems.push({
                description: _t("Archive"),
                callback: () => {
                    Dialog.confirm(this, _t("Are you sure that you want to archive all the selected records?"), {
                        confirm_callback: () => this._toggleArchiveState(true),
                    });
                }
            }, {
                description: _t("Unarchive"),
                callback: () => this._toggleArchiveState(false)
            });
        }
        if (this.activeActions.delete) {
            otherActionItems.push({
                description: _t("Delete"),
                callback: () => this._onDeleteSelectedRecords()
            });
        }}else{
            if (this.isExportEnable) {
            otherActionItems.push({
                description: _t("Export"),
                callback: () => this._onExportData()
            });
        }
        if (this.archiveEnabled) {
            otherActionItems.push({
                description: _t("Archive"),
                callback: () => {
                    Dialog.confirm(this, _t("Are you sure that you want to archive all the selected records?"), {
                        confirm_callback: () => this._toggleArchiveState(true),
                    });
                }
            }, {
                description: _t("Unarchive"),
                callback: () => this._toggleArchiveState(false)
            });
        }
        if (this.activeActions.delete) {
            otherActionItems.push({
                description: _t("Delete"),
                callback: () => this._onDeleteSelectedRecords()
            });
        }

        }
        return Object.assign(props, {
            items: Object.assign({}, this.toolbarActions, { other: otherActionItems }),
            context: state.getContext(),
            domain: state.getDomain(),
            isDomainSelected: this.isDomainSelected,
        });

    },

        ks_dashboard_export: function() {
            this.ks_on_dashboard_export(this.getSelectedIds());
        },

        ks_on_dashboard_export: function(ids) {
            var self = this;
            this._rpc({
                model: 'ks_dashboard_ninja.board',
                method: 'ks_dashboard_export',
                args: [JSON.stringify(ids)],
            }).then(function(result) {
                var name = "dashboard_ninja";
                var data = {
                    "header": name,
                    "dashboard_data": result,
                }
                framework.blockUI();
                self.getSession().get_file({
                    url: '/ks_dashboard_ninja/export/dashboard_json',
                    data: {
                        data: JSON.stringify(data)
                    },
                    complete: framework.unblockUI,
                    error: (error) => this.call('crash_manager', 'rpc_error', error),
                });
            })
        },


});
core.action_registry.add('ks_dashboard_ninja.import_button', ListController);
export default ListController;
