/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";

/**
 * Reload the page when the current user's groups are updated (e.g. privilege
 * granted or removed) so the menu updates without a manual refresh.
 */
export const groupsReloadService = {
    dependencies: ["bus_service"],

    start(env, { bus_service }) {
        bus_service.subscribe("res_users_groups_updated", () => {
            browser.location.reload();
        });
    },
};

registry.category("services").add("groups_reload_service", groupsReloadService);
