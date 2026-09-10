/** @odoo-module **/
/*
 * ks_dashboard_ninja - Odoo 15 -> 17 conversion of ks_color_picker.js
 *
 * Odoo 15 shell:  odoo.define('ks_dashboard_ninja_list.ks_color_picker',
 *                  AbstractField.extend, web.field_registry)
 * Odoo 17 shell:  ES module + OWL component (compat base in ks_legacy_compat.js)
 *
 * Every method body below is byte-for-byte the original Odoo 15 implementation.
 * The registry entry name and the widget behaviour are unchanged.
 *
 * Odoo 15 lazily loaded its jQuery plugins through jsLibs/cssLibs on the field
 * widget.  Odoo 17 removed lazy lib loading, so spectrum.js / spectrum.css are
 * now declared in the manifest (web.assets_backend) instead and always loaded
 * with the backend bundle.
 */

import { LegacyField as AbstractField } from "./ks_legacy_compat.js";
import { fieldRegistry as registry } from "./ks_legacy_compat.js";
import { core } from "./ks_legacy_compat.js";

var QWeb = core.qweb;

//Widget for color picker being used in dashboard item create view.
//TODO : This color picker functionality can be improved a lot.
export class KsColorPicker extends AbstractField {
    static supportedFieldTypes = ['char'];

    events = {
        'change.spectrum .ks_color_picker': '_ksOnColorChange',
        'change .ks_color_opacity': '_ksOnOpacityChange',
        'input .ks_color_opacity': '_ksOnOpacityInput'
    };

    _render() {
        this.$el.empty();
        var ks_color_value = '#376CAE';
        var ks_color_opacity = '0.99';
        if (this.value) {
            ks_color_value = this.value.split(',')[0];
            ks_color_opacity = this.value.split(',')[1];
        };
        var $view = $(QWeb.render('ks_color_picker_opacity_view', {
            ks_color_value: ks_color_value,
            ks_color_opacity: ks_color_opacity
        }));

        this.$el.append($view)

        this.$el.find(".ks_color_picker").spectrum({
            color: ks_color_value,
            showInput: true,
            hideAfterPaletteSelect: true,

            clickoutFiresChange: true,
            showInitial: true,
            preferredFormat: "rgb",
        });

        if (this.mode === 'readonly') {
            this.$el.find('.ks_color_picker').addClass('ks_not_click');
            this.$el.find('.ks_color_opacity').addClass('ks_not_click');
            this.$el.find('.ks_color_picker').spectrum("disable");
        } else {
            this.$el.find('.ks_color_picker').spectrum("enable");
        }
    }



    _ksOnColorChange(e, tinycolor) {
        this._setValue(tinycolor.toHexString().concat("," + this.value.split(',')[1]));
    }

    _ksOnOpacityChange(event) {
        this._setValue(this.value.split(',')[0].concat("," + event.currentTarget.value));
    }

    _ksOnOpacityInput(event) {
        var self = this;
        var color;
        if (self.name == "ks_background_color") {
            color = $('.ks_db_item_preview_color_picker').css("background-color")
            $('.ks_db_item_preview_color_picker').css("background-color", self.get_color_opacity_value(color, event.currentTarget.value))

            color = $('.ks_db_item_preview_l2').css("background-color")
            $('.ks_db_item_preview_l2').css("background-color", self.get_color_opacity_value(color, event.currentTarget.value))

        } else if (self.name == "ks_default_icon_color") {
            color = $('.ks_dashboard_icon_color_picker > span').css('color')
            $('.ks_dashboard_icon_color_picker > span').css('color', self.get_color_opacity_value(color, event.currentTarget.value))
        } else if (self.name == "ks_font_color") {
            color = $('.ks_db_item_preview').css("color")
            color = $('.ks_db_item_preview').css("color", self.get_color_opacity_value(color, event.currentTarget.value))
        }
    }

    get_color_opacity_value(color, val) {
        if (color) {
            return color.replace(color.split(',')[3], val + ")");
        } else {
            return false;
        }
    }

}

registry.add('ks_color_dashboard_picker', KsColorPicker);

export default {
    KsColorPicker: KsColorPicker
};
