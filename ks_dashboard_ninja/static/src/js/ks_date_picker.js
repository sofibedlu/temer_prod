/** @odoo-module **/
/*
 * ks_dashboard_ninja - Odoo 15 -> 17 conversion of ks_date_picker.js
 *
 * Odoo 15: patched web.datepicker's DateWidget so the popup date picker in the
 * dashboard does not hijack window scroll events.
 * Odoo 17: the module's date pickers are backed by native inputs (see the
 * datepicker shim in ks_legacy_compat.js), so the scroll-hijack no longer
 * exists; the patch below is kept to preserve the module structure.  The
 * hook body is the original implementation.
 */
import { datepicker } from "./ks_legacy_compat.js";

datepicker.DateWidget.include({
    _onDateTimePickerShow: function() {
        this._super.apply(this, arguments);

        if (this.name === "ks_dashboard") {
            window.removeEventListener('scroll', this._onScroll, true);
        }
    },
});

export default datepicker;
