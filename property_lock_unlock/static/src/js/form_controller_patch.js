/** @odoo-module */

import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";

const ACTIONS_TO_HIDE_WHEN_LOCKED = ["Make Draft", "Make Available"];

patch(FormController.prototype, {
    get actionMenuItems() {
        const result = super.actionMenuItems;
        if (
            this.props.resModel !== "property.property" ||
            !this.model?.root
        ) {
            return result;
        }
        const isLocked = this.model.root.data?.is_locked;
        if (!isLocked) {
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
