/** @odoo-module **/
/*
 * ks_dashboard_ninja - Odoo 15 -> 17 conversion of ks_widget_toggle.js
 *
 * Odoo 15 shell:  odoo.define('ks_dashboard_ninja_list.ks_widget_toggle',
 *                  AbstractField.extend, web.field_registry)
 * Odoo 17 shell:  ES module + OWL components (compat base in ks_legacy_compat.js)
 *
 * Every method body below is byte-for-byte the original Odoo 15 implementation.
 * The registry entry names and the widget behaviour are unchanged.
 */

import { LegacyField as AbstractField } from "./ks_legacy_compat.js";
import { fieldRegistry as registry } from "./ks_legacy_compat.js";
import { core } from "./ks_legacy_compat.js";

var QWeb = core.qweb;

//Widget for toggle while creating dashboard item.
export class KsWidgetToggle extends AbstractField {
    static supportedFieldTypes = ['char'];

    events = {
        'change .ks_toggle_icon_input': 'ks_toggle_icon_input_click',
    };

    _render() {
        var self = this;
        self.$el.empty();


        var $view = $(QWeb.render('ks_widget_toggle'));
        if (self.value) {
            $view.find("input[value='" + self.value + "']").prop("checked", true);
        }
        this.$el.append($view)

        if (this.mode === 'readonly') {
            this.$el.find('.ks_select_dashboard_item_toggle').addClass('ks_not_click');
        }
    }

    ks_toggle_icon_input_click(e) {
        var self = this;
        self._setValue(e.currentTarget.value);
    }
}

export class KsWidgetToggleKPI extends AbstractField {
    static supportedFieldTypes = ['char'];

    events = {
        'change .ks_toggle_icon_input': 'ks_toggle_icon_input_click',
    };

    _render() {
        var self = this;
        self.$el.empty();
        var $view = $(QWeb.render('ks_widget_toggle_kpi'));

        if (self.value) {
            $view.find("input[value='" + self.value + "']").prop("checked", true);
        }
        this.$el.append($view)

        if (this.mode === 'readonly') {
            this.$el.find('.ks_select_dashboard_item_toggle').addClass('ks_not_click');
        }
    }
    ks_toggle_icon_input_click(e) {
        var self = this;
        self._setValue(e.currentTarget.value);
    }
}

export class KsWidgetToggleKpiTarget extends AbstractField {
    static supportedFieldTypes = ['char'];

    events = {
        'change .ks_toggle_icon_input': 'ks_toggle_icon_input_click',
    };

    _render() {
        var self = this;
        self.$el.empty();


        var $view = $(QWeb.render('ks_widget_toggle_kpi_target_view'));
        if (self.value) {
            $view.find("input[value='" + self.value + "']").prop("checked", true);
        }
        this.$el.append($view)

        if (this.mode === 'readonly') {
            this.$el.find('.ks_select_dashboard_item_toggle').addClass('ks_not_click');
        }
    }

    ks_toggle_icon_input_click(e) {
        var self = this;
        self._setValue(e.currentTarget.value);
    }
}

registry.add('ks_widget_toggle', KsWidgetToggle);
registry.add('ks_widget_toggle_kpi', KsWidgetToggleKPI);
registry.add('ks_widget_toggle_kpi_target', KsWidgetToggleKpiTarget);

export default {
    KsWidgetToggle: KsWidgetToggle,
    KsWidgetToggleKPI: KsWidgetToggleKPI,
    KsWidgetToggleKpiTarget: KsWidgetToggleKpiTarget
};
