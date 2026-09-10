/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { useRef, useEffect } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

const DUPLICATE_PHONE_MODELS = [
    "crm.reception",
    "crm.website",
    "crm.callcenter",
];

patch(FormController.prototype, {
    setup() {
        super.setup(...arguments);
        this.actionService = useService("action");
        this._duplicateWizardShownForResId = useRef(null);

        useEffect(
            () => {
                this._maybeOpenDuplicateWizard();
            },
            () => [
                this.model?.root?.data?.quota_duplicate_popup_pending,
                this.model?.root?.data?.phone_number_message,
                this.model?.root?.data?.status,
                this.model?.root?.data?.existing_salesperson_id,
                this.model?.root?.resId,
                this.props.resModel,
            ]
        );
    },

    async save(params) {
        const res = await super.save(...arguments);
        await this._maybeOpenDuplicateWizard();
        return res;
    },

    async _maybeOpenDuplicateWizard() {
        if (!DUPLICATE_PHONE_MODELS.includes(this.props.resModel)) {
            return;
        }
        const root = this.model?.root;
        if (!root?.data?.quota_duplicate_popup_pending) {
            return;
        }
        if (root.data.wing_duplicate_popup_pending) {
            return;
        }
        const msg = root.data.phone_number_message;
        const status = root.data.status;
        const hasMessage =
            (typeof msg === "string" && msg.trim()) ||
            (typeof status === "string" && status.trim()) ||
            !!root.data.existing_salesperson_id;
        if (!hasMessage) {
            return;
        }
        const resId = root.resId;
        if (typeof resId !== "number") {
            return;
        }
        const popupKey = `${this.props.resModel}-${resId}`;
        if (this._duplicateWizardShownForResId.current === popupKey) {
            return;
        }
        this._duplicateWizardShownForResId.current = popupKey;

        await new Promise((resolve) => setTimeout(resolve, 200));

        const inactive = !!root.data.reassign_lead;
        await this.actionService.doAction({
            type: "ir.actions.act_window",
            name: inactive
                ? _t("Inactive salesperson — use Reassign")
                : _t("Existing customer"),
            res_model: "crm.lead.duplicate.message.wizard",
            views: [[false, "form"]],
            target: "new",
            context: {
                default_lead_model: this.props.resModel,
                default_lead_res_id: resId,
            },
        });
    },
});
