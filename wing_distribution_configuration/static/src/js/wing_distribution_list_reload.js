/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";

/**
 * Reload the Wing Distribution list when multiple rows are created in one save,
 * so all new rows appear immediately without manual refresh.
 */
export const wingDistributionListReloadService = {
    dependencies: ["bus_service", "action"],

    start(env, { bus_service, action }) {
        bus_service.subscribe("wing_distribution_multi_created", () => {
            const controller = action.currentController;
            if (controller?.props?.resModel === "wing.distribution.line") {
                if (typeof controller.model?.load === "function") {
                    controller.model.load();
                } else if (controller.action) {
                    action.doAction(controller.action, { clearBreadcrumbs: false });
                } else {
                    browser.location.reload();
                }
            }
        });
    },
};

registry.category("services").add("wing_distribution_list_reload", wingDistributionListReloadService);
