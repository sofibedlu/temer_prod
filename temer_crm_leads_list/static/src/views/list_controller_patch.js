/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";

const INSITE_ACTION_NAME = "Insite all lead";

patch(ListController.prototype, {
    get actionMenuItems() {
        const result = super.actionMenuItems;
        const controller = this.actionService.currentController;
        const actionName = controller?.action?.name;
        if (actionName === INSITE_ACTION_NAME) {
            return { ...result, print: [] };
        }
        return result;
    },
});
