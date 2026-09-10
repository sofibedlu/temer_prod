/** @odoo-module **/
/*
 * ks_dashboard_ninja - Odoo 15 -> 17 conversion of ks_dashboard_item_theme.js
 *
 * Odoo 15 shell:  odoo.define('ks_dashboard_ninja_list.ks_dashboard_item_theme',
 *                  AbstractField.extend, web.field_registry)
 * Odoo 17 shell:  ES module + OWL component (compat base in ks_legacy_compat.js)
 *
 * Every method body below is byte-for-byte the original Odoo 15 implementation.
 * The registry entry name and the widget behaviour are unchanged.
 */

import { LegacyField as AbstractField } from "./ks_legacy_compat.js";
import { fieldRegistry as registry } from "./ks_legacy_compat.js";
import { core } from "./ks_legacy_compat.js";

var QWeb = core.qweb;

//Widget for dashboard item theme using while creating dashboard item.
export class KsDashboardTheme extends AbstractField {
    static supportedFieldTypes = ["char"];

    events = {
        'click .ks_dashboard_theme_input_container': 'ks_dashboard_theme_input_container_click',
    };

    _render() {
        var self = this;
        self.$el.empty();
        var $view = $(QWeb.render('ks_dashboard_theme_view', {widget: this}));
        if (self.value) {
            $view.find("input[value='" + self.value + "']").prop("checked", true);
        }
        self.$el.append($view)

        if (this.mode === 'readonly') {
            this.$el.find('.ks_dashboard_theme_view_render').addClass('ks_not_click');
        }
    }

    ks_dashboard_theme_input_container_click(e) {
        var self = this;
        var $box = $(e.currentTarget).find(':input');
        if ($box.is(":checked")) {
            self.$el.find('.ks_dashboard_theme_input').prop('checked', false)
            $box.prop("checked", true);
        } else {
            $box.prop("checked", false);
        }
        self._setValue($box[0].value);
    }
}

registry.add('ks_dashboard_item_theme', KsDashboardTheme);

export default {
    KsDashboardTheme: KsDashboardTheme
};