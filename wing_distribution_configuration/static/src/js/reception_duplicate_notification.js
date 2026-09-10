/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { useRef, useEffect } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

const DEFAULT_DUPLICATE_MESSAGE = _t("Customer already registered.");

// Same "already registered" popup for Reception, Website, Call Center, and Affiliate
const DUPLICATE_PHONE_MODELS = [
    "crm.reception",
    "crm.website",
    "crm.callcenter",
    "crm.affilater",
];

function getShownStorageKey(resModel, resId) {
    return `wing_duplicate_popup_shown:${resModel}:${resId}`;
}

function wasShownBefore(resModel, resId) {
    try {
        return window.localStorage.getItem(getShownStorageKey(resModel, resId)) === "1";
    } catch (e) {
        return false;
    }
}

function markShown(resModel, resId) {
    try {
        window.localStorage.setItem(getShownStorageKey(resModel, resId), "1");
    } catch (e) {}
}

patch(FormController.prototype, {
    setup() {
        super.setup(...arguments);
        this.dialog = useService("dialog");
        this.orm = useService("orm");
        this._duplicatePopupShownForResId = useRef(null);

        useEffect(
            () => {
                if (!DUPLICATE_PHONE_MODELS.includes(this.props.resModel)) {
                    return;
                }
                const root = this.model?.root;
                if (!root?.data) {
                    return;
                }
                const pending = !!root.data.wing_duplicate_popup_pending;
                if (!pending) {
                    return;
                }
                const msg = root.data.phone_number_message;
                const hasDuplicate =
                    (msg && typeof msg === "string" && msg.trim()) ||
                    !!root.data.existing_salesperson_id ||
                    !!root.data.existing_temer_lead_id;
                if (!hasDuplicate) {
                    return;
                }
                const resId = root.resId != null ? root.resId : null;
                const popupKey = resId ? `${this.props.resModel}-${resId}` : `${this.props.resModel}-new`;
                if (this._duplicatePopupShownForResId.current === popupKey) {
                    return;
                }
                this._duplicatePopupShownForResId.current = popupKey;

                const timer = setTimeout(() => {
                    const normalized =
                        msg && typeof msg === "string" ? msg.trim() : "";
                    let body = DEFAULT_DUPLICATE_MESSAGE;
                    if (normalized) {
                        const base = DEFAULT_DUPLICATE_MESSAGE;
                        const hasBase =
                            normalized.toLowerCase().indexOf(base.toLowerCase()) !== -1;
                        body = hasBase ? normalized : `${base}\n${normalized}`;
                    }
                    this.dialog.add(AlertDialog, {
                        title: _t("Already registered"),
                        body: body,
                        confirmLabel: _t("Close"),
                        confirm: async () => {
                            try {
                                if (typeof resId === "number") {
                                    await this.orm.write(this.props.resModel, [resId], {
                                        wing_duplicate_popup_pending: false,
                                    });
                                }
                            } catch (e) {
                                // ignore
                            }
                        },
                    });
                }, 150);

                return () => clearTimeout(timer);
            },
            () => [
                this.model?.root?.data?.wing_duplicate_popup_pending,
                this.model?.root?.data?.phone_number_message,
                this.model?.root?.data?.existing_salesperson_id,
                this.model?.root?.data?.existing_temer_lead_id,
                this.model?.root?.resId,
                this.props.resModel,
            ]
        );
    },

    async saveRecord() {
        const res = await this._super(...arguments);
        // After saving, show the duplicate popup if the backend marked it pending.
        const root = this.model?.root;
        if (root?.data) {
            const pending = !!root.data.wing_duplicate_popup_pending;
            const msg = root.data.phone_number_message;
            const hasDuplicate =
                pending &&
                ((msg && typeof msg === "string" && msg.trim()) ||
                    !!root.data.existing_salesperson_id ||
                    !!root.data.existing_temer_lead_id);
            if (hasDuplicate) {
                const resId = root.resId != null ? root.resId : null;
                const popupKey = resId ? `${this.props.resModel}-${resId}` : `${this.props.resModel}-new`;
                if (this._duplicatePopupShownForResId.current !== popupKey) {
                    this._duplicatePopupShownForResId.current = popupKey;
                    const normalized =
                        msg && typeof msg === "string" ? msg.trim() : "";
                    let body = DEFAULT_DUPLICATE_MESSAGE;
                    if (normalized) {
                        const base = DEFAULT_DUPLICATE_MESSAGE;
                        const hasBase =
                            normalized.toLowerCase().indexOf(base.toLowerCase()) !== -1;
                        body = hasBase ? normalized : `${base}\n${normalized}`;
                    }
                    this.dialog.add(AlertDialog, {
                        title: _t("Already registered"),
                        body: body,
                        confirmLabel: _t("Close"),
                        confirm: async () => {
                            try {
                                if (typeof resId === "number") {
                                    await this.orm.write(this.props.resModel, [resId], {
                                        wing_duplicate_popup_pending: false,
                                    });
                                }
                            } catch (e) {
                                // ignore
                            }
                        },
                    });
                }
            }
        }
        return res;
    },
});
