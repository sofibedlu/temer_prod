/** @odoo-module */

import { ListController } from "@web/views/list/list_controller";
import { patch } from "@web/core/utils/patch";
import { onWillStart, onWillUnmount, useState } from "@odoo/owl";
import { session } from "@web/session";

const ACTIONS_TO_HIDE_WHEN_LOCKED = ["Make Draft", "Make Available"];
const UNLOCK_GROUP = "property_lock_unlock.property_unlock_group";
const LOCK_GROUP = "property_lock_unlock.property_lock_group";

patch(ListController.prototype, {
    setup() {
        super.setup(...arguments);
        this.privilegeState = useState({
            hasLockGroup: false,
            hasUnlockGroup: false,
        });
        this._visibilityHandler = null;
        onWillStart(async () => {
            if (this.props.resModel === "property.property") {
                await this._loadPrivileges();
            }
        });
    },

    async _loadPrivileges() {
        if (this.props.resModel !== "property.property") return;
        const context = {
            ...session.user_context,
            uid: session.uid || session.user_id,
        };
        const [hasUnlock, hasLock] = await Promise.all([
            this.rpc("/web/dataset/call_kw/res.users/has_group", {
                model: "res.users",
                method: "has_group",
                args: [UNLOCK_GROUP],
                kwargs: { context },
            }),
            this.rpc("/web/dataset/call_kw/res.users/has_group", {
                model: "res.users",
                method: "has_group",
                args: [LOCK_GROUP],
                kwargs: { context },
            }),
        ]).catch(() => [false, false]);
        this.privilegeState.hasUnlockGroup = hasUnlock;
        this.privilegeState.hasLockGroup = hasLock;
        if (!this._visibilityHandler) {
            this._visibilityHandler = () => {
                if (document.visibilityState === "visible") {
                    this._loadPrivileges();
                }
            };
            document.addEventListener("visibilitychange", this._visibilityHandler);
        }
    },

    onWillUnmount() {
        super.onWillUnmount?.();
        if (this._visibilityHandler) {
            document.removeEventListener(
                "visibilitychange",
                this._visibilityHandler
            );
            this._visibilityHandler = null;
        }
    },

    /**
     * Override evalViewModifier to handle is_locked and state for property.property
     * list view. The list evalContext has no record fields, so we compute from
     * selection. Must handle these modifiers ourselves - super would throw because
     * evalContext lacks is_locked/state.
     */
    evalViewModifier(modifier) {
        if (modifier == null || typeof modifier !== "string") {
            return super.evalViewModifier(...arguments);
        }
        if (this.props.resModel !== "property.property") {
            return super.evalViewModifier(...arguments);
        }
        const isUnlockInvisibleExpr =
            modifier === "is_locked == False" || modifier === "is_locked==False";
        const isPropertyLockModifier =
            modifier === "is_locked" ||
            modifier === "not is_locked" ||
            isUnlockInvisibleExpr ||
            (modifier.includes("is_locked") && modifier.includes("state not in"));
        if (!isPropertyLockModifier) {
            return super.evalViewModifier(...arguments);
        }
        const selection = this.model?.root?.selection ?? [];
        const anyLocked = selection.some((r) => r.data && r.data.is_locked);
        const anyUnlocked = selection.some((r) => !(r.data && r.data.is_locked));
        const anyNotDraftOrAvailable = selection.some(
            (r) => r.data && r.data.state && !["draft", "available"].includes(r.data.state)
        );
        if (modifier === "is_locked") {
            return anyLocked;
        }
        if (modifier === "not is_locked") {
            return !anyLocked;
        }
        if (
            modifier === "is_locked == False" ||
            modifier === "is_locked==False"
        ) {
            if (!this.privilegeState?.hasUnlockGroup) {
                return true;
            }
            return anyUnlocked;
        }
        if (!this.privilegeState?.hasLockGroup) {
            return true;
        }
        return anyLocked || anyNotDraftOrAvailable;
    },

    /**
     * Override actionMenuItems to hide Make Draft and Make Available when
     * selected property records are locked.
     */
    get actionMenuItems() {
        const result = super.actionMenuItems;
        if (
            this.props.resModel !== "property.property" ||
            !this.model?.root?.selection?.length
        ) {
            return result;
        }
        const anyLocked = this.model.root.selection.some(
            (r) => r.data && r.data.is_locked
        );
        if (!anyLocked) {
            return result;
        }
        const filteredAction = (result.action || []).filter((item) => {
            const name = item.action?.name ?? item.description ?? item.name;
            return !ACTIONS_TO_HIDE_WHEN_LOCKED.includes(name);
        });
        return {
            ...result,
            action: filteredAction,
        };
    },
});
