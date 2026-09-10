/** @odoo-module **/
/*
 * ks_dashboard_ninja - Odoo 15 -> 17 conversion of ks_quick_edit_view.js
 *
 * Odoo 15: the "quick edit" dropdown on each dashboard item embedded a legacy
 * QuickCreateFormView inline so the user could edit an item's core settings
 * (name, colors, icon, layout, count) without leaving the dashboard.
 * Odoo 17: QuickCreateFormView / web.data.DataSet / widget controllers were
 * removed from the web client.  The quick-edit flow is reproduced with the
 * Odoo 17 equivalent: the item record opens in a form dialog (target 'new')
 * and the dashboard item is refreshed once the dialog is closed.  The full
 * item form (navigation to the item form page) works exactly as before via
 * the 'openFullItemForm' event.
 *
 * The API surface used by the main dashboard action is unchanged:
 *   new QuickEditView(dashboardController, {item}) / .appendTo($menu)
 *   .on('canBeDestroyed'|'canBeRendered'|'openFullItemForm') / .destroy()
 */
import { _t } from "@web/core/l10n/translation";
import { renderToString } from "@web/core/utils/render";

export class QuickEditView {
    constructor(parent, options) {
        this.ksDashboardController = parent;
        this.ksOriginalItemData = $.extend({}, options.item);
        this.item = options.item;
        this.item_name = options.item ? options.item.name : false;
        this._events = {};
        this._destroyed = false;
    }

    // --- tiny event emitter (legacy widget .on/.trigger) -------------------
    on(eventName, obj, cb) {
        if (typeof obj === "function") {
            cb = obj;
        }
        (this._events[eventName] = this._events[eventName] || []).push(cb);
        return this;
    }

    trigger(eventName, payload) {
        (this._events[eventName] || []).forEach((cb) => {
            try {
                cb.call(this, payload);
            } catch (e) {
                console.error("ks quick edit handler error", e);
            }
        });
        return this;
    }

    appendTo($container) {
        const self = this;
        const title = this.item_name || _t("Quick edit");
        const tpl =
            '<div class="o_ks_quick_edit">' +
            '<div class="o_ks_quick_edit_title px-2 pt-2 pb-1"><strong>' + title + "</strong></div>" +
            '<div class="list-group list-group-flush">' +
            '<a href="#" class="list-group-item list-group-item-action o_ks_qe_edit">' +
            '<i class="fa fa-pencil"/> ' + _t("Edit in a form") + "</a>" +
            '<a href="#" class="list-group-item list-group-item-action o_ks_qe_full">' +
            '<i class="fa fa-external-link"/> ' + _t("Open full item form") + "</a>" +
            "</div></div>";
        this.$el = $(tpl);
        $container.append(this.$el);

        this.$el.find(".o_ks_qe_edit").on("click", function (e) {
            e.preventDefault();
            e.stopPropagation();
            self._ksOpenEditDialog();
        });
        this.$el.find(".o_ks_qe_full").on("click", function (e) {
            e.preventDefault();
            e.stopPropagation();
            self.destroy();
            self.trigger("openFullItemForm", {});
        });

        // mirror the legacy widget lifecycle: content is rendered
        this.trigger("canBeRendered", {});
        return Promise.resolve(this);
    }

    _ksOpenEditDialog() {
        const self = this;
        const controller = this.ksDashboardController;
        if (!controller || typeof controller.do_action !== "function") {
            this.ksDiscardChanges();
            return;
        }
        const action = {
            type: "ir.actions.act_window",
            name: _t("Edit Dashboard Item"),
            res_model: "ks_dashboard_ninja.item",
            res_id: this.item.id,
            views: [[false, "form"]],
            view_mode: "form",
            target: "new",
            context: {
                form_view_ref: "ks_dashboard_ninja.item_quick_edit_form_view",
            },
        };
        controller
            .do_action(action, {})
            .finally(function () {
                // refresh the dashboard item after the dialog is closed so the
                // edited values (name, colors, icon, layout, count) show up
                if (typeof controller.ksFetchUpdateItem === "function") {
                    controller.ksFetchUpdateItem(self.item.id).catch(() => {});
                } else if (typeof controller.ksUpdateDashboardItem === "function") {
                    controller.ksUpdateDashboardItem([self.item.id]);
                }
                self.ksDiscardChanges();
            });
    }

    ksDiscardChanges() {
        const controller = this.ksDashboardController;
        if (controller && typeof controller.ksFetchUpdateItem === "function") {
            try {
                controller.ksFetchUpdateItem(this.item.id);
            } catch (e) {
                console.error("ks quick edit refresh error", e);
            }
        }
        this.destroy();
    }

    destroy() {
        if (this._destroyed) {
            return;
        }
        this._destroyed = true;
        if (this.$el) {
            this.$el.remove();
            this.$el = null;
        }
        this.trigger("canBeDestroyed", {});
    }
}

export default {
    QuickEditView: QuickEditView,
};
