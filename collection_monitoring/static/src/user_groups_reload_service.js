/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { UPDATE_METHODS } from "@web/core/orm_service";

/**
 * Reload the interface when the current user's groups (groups_id) are updated.
 * This ensures menu visibility (e.g. Collection Monitoring) updates immediately
 * without requiring a manual page refresh.
 */
export const userGroupsReloadService = {
    dependencies: ["action", "user"],
    start(env, { action }) {
        env.bus.addEventListener("RPC:RESPONSE", (ev) => {
            const { data, error } = ev.detail;
            const { model, method, args } = data?.params || {};
            if (error || model !== "res.users" || !UPDATE_METHODS.includes(method)) {
                return;
            }
            const userId = session.uid || session.user_id;
            if (!userId) return;

            const ids = args?.[0];
            const vals = args?.[1] || {};
            const idsList = Array.isArray(ids) ? ids : ids ? [ids] : [];
            const currentUserAffected = idsList.includes(userId);
            const groupsChanged = "groups_id" in vals;

            if (currentUserAffected && groupsChanged && !browser.localStorage.getItem("running_tour")) {
                action.doAction("reload_context");
            }
        });
    },
};

registry.category("services").add("user_groups_reload", userGroupsReloadService);
