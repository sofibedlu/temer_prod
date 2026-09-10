/** @odoo-module **/
/*
 * ks_dashboard_ninja - Odoo 15 -> 17 conversion of ks_image_basic_widget.js
 *
 * Odoo 15 shell:  odoo.define('ks_dashboard_ninja_list.ks_image_basic_widget',
 *                  basic_fields.FieldBinaryImage.extend, web.field_registry)
 * Odoo 17 shell:  ES module + OWL component (compat base in ks_legacy_compat.js)
 *
 * Odoo 17 removed the whole basic_fields.FieldBinaryImage machinery.  This
 * widget only ever used a tiny slice of it (the icon-name field ks_default_icon
 * is a Char field, so the binary upload path was dead even in Odoo 15 - the
 * module's own template replaced the file input and only kept the "Select
 * Icons" + "Clear" buttons).  The v15 API surface that is reproduced here:
 *   - placeholder  -> the classic /web/static/img/placeholder.png (class
 *                     default of FieldBinaryImage) shown while no icon chosen
 *   - template     -> KsFieldBinaryImage is rendered as the legacy root
 *                     template by the compat base (this.legacyTemplate),
 *                     exactly like the Odoo 15 framework did
 *   - .o_clear_file_button  -> inherited from FieldBinary events in v15
 *                     ('_onClearClick'), implemented as _onClearClick below
 *
 * Documented v15 -> v17 adaptations (no functional change):
 *   - init(): v15 initialised ksSelectedIcon / ks_icon_set after _super().
 *     Same values are now plain class fields.
 *   - ks_image_widget_icon_container(): v15 opened the modal with the jQuery
 *     bootstrap plugin $().modal().  Odoo 17 has no jQuery modal plugin, so
 *     the (bootstrap 5 markup compatible) modal is shown/hidden by the new
 *     _ksShowIconModal/_ksHideIconModal helpers: show/display classes, a
 *     backdrop, Escape and backdrop-click closing, and the existing
 *     data-dismiss="modal" buttons of the template.
 *   - ks_icon_container_list(): v15 used the underscore _.each() on the
 *     jQuery collection; Odoo 17 does not load underscore, so the native
 *     toArray().forEach() equivalent is used (element is still the first
 *     callback argument, identical behaviour).
 *   - template: renamed legacyTemplate so it does not shadow the OWL
 *     Component.template concept; legacyRootClass keeps the v15 root class
 *     (.o_field_image) so the module's CSS selectors still apply.
 *   - supportedFieldTypes: FieldBinaryImage inherited ['binary'] but the
 *     widget is used on the Char field ks_default_icon - declared as the
 *     Char type it really supports.
 *   - FieldBinaryImage-img was an Odoo 15 core web template; Odoo 17 core no
 *     longer ships it, so it is re-declared in the module XML (same markup).
 *
 * All remaining method bodies (_render, ks_icon_container_list,
 * ks_icon_container_open_button, ks_fa_icon_search, ks_modal_icon_input_enter)
 * are byte-for-byte the original Odoo 15 implementation.
 */

import { LegacyField as AbstractField } from "./ks_legacy_compat.js";
import { fieldRegistry as registry } from "./ks_legacy_compat.js";
import { core } from "./ks_legacy_compat.js";
import { onWillUnmount } from "@odoo/owl";

var QWeb = core.qweb;

// Minimal stand-in for the slice of Odoo 15 basic_fields.FieldBinaryImage that
// this widget actually used (see header comment).
export class KsImageFieldBinaryBase extends AbstractField {
    placeholder = "/web/static/img/placeholder.png";
}

export class KsImageWidget extends KsImageFieldBinaryBase {
    static supportedFieldTypes = ['char'];

    // legacy root template rendered by the compat base before _render()
    legacyTemplate = 'KsFieldBinaryImage';
    legacyRootClass = 'o_field_image';

    ksSelectedIcon = false;
    ks_icon_set = ['home', 'puzzle-piece', 'clock-o', 'comments-o', 'car', 'calendar', 'calendar-times-o', 'bar-chart', 'commenting-o', 'star-half-o', 'address-book-o', 'tachometer', 'search', 'money', 'line-chart', 'area-chart', 'pie-chart', 'check-square-o', 'users', 'shopping-cart', 'truck', 'user-circle-o', 'user-plus', 'sun-o', 'paper-plane', 'rss', 'gears', 'check', 'book'];

    events = {
        'click .ks_icon_container_list': 'ks_icon_container_list',
        'click .ks_image_widget_icon_container': 'ks_image_widget_icon_container',
        'click .ks_icon_container_open_button': 'ks_icon_container_open_button',
        'click .ks_fa_icon_search': 'ks_fa_icon_search',
        'keyup .ks_modal_icon_input': 'ks_modal_icon_input_enter',
        // v15 inherited these two from basic_fields.FieldBinary / the
        // bootstrap plugin: clear button handler + data-dismiss close buttons.
        'click .o_clear_file_button': '_onClearClick',
        'click [data-dismiss="modal"]': '_onModalDismiss',
    };

    setup() {
        super.setup();
        onWillUnmount(() => this._ksCleanupModal());
    }

    _render() {
        var ks_self = this;
        var url = this.placeholder;
        if (ks_self.value) {
            ks_self.$('> img').remove();
            ks_self.$('> span').remove();
            $('<span>').addClass('fa fa-' + ks_self.recordData.ks_default_icon + ' fa-5x').appendTo(ks_self.$el).css('color', 'black');
        } else {
            var $img = $(QWeb.render("FieldBinaryImage-img", {
                widget: this,
                url: url
            }));
            ks_self.$('> img').remove();
            ks_self.$('> span').remove();
            ks_self.$el.prepend($img);
        }

        var $ks_icon_container_modal = $(QWeb.render('ks_icon_container_modal_template', {
            ks_fa_icons_set: ks_self.ks_icon_set
        }));

        $ks_icon_container_modal.prependTo(ks_self.$el);
    }

    //This will show modal box on clicking on open icon button.
    ks_image_widget_icon_container(e) {
        // v15: $('#ks_icon_container_modal_id').modal({show: true});
        // Odoo 17 has no jQuery bootstrap plugin - see header comment.
        this._ksShowIconModal();
    }


    ks_icon_container_list(e) {
        var self = this;
        self.ksSelectedIcon = $(e.currentTarget).find('span').attr('id').split('.')[1]
        // v15: _.each($('.ks_icon_container_list'), function(selected_icon) {
        $('.ks_icon_container_list').toArray().forEach(function(selected_icon) {
            $(selected_icon).removeClass('ks_icon_selected');
        });

        $(e.currentTarget).addClass('ks_icon_selected')
        $('.ks_icon_container_open_button').show()
    }

    //Imp :  Hardcoded for svg file only. If different file, change this code to dynamic.
    ks_icon_container_open_button(e) {
        var ks_self = this;
        ks_self._setValue(ks_self.ksSelectedIcon);
    }

    ks_fa_icon_search(e) {
        var self = this
        self.$el.find('.ks_fa_search_icon').remove()
        var ks_fa_icon_name = self.$el.find('.ks_modal_icon_input')[0].value
        if (ks_fa_icon_name.slice(0, 3) === "fa-") {
            ks_fa_icon_name = ks_fa_icon_name.slice(3)
        }
        var ks_fa_icon_render = $('<div>').addClass('ks_icon_container_list ks_fa_search_icon')
        $('<span>').attr('id', 'ks.' + ks_fa_icon_name.toLocaleLowerCase()).addClass("fa fa-" + ks_fa_icon_name.toLocaleLowerCase() + " fa-4x").appendTo($(ks_fa_icon_render))
        $(ks_fa_icon_render).appendTo(self.$el.find('.ks_icon_container_grid_view'))
    }

    ks_modal_icon_input_enter(e) {
        var ks_self = this
        if (e.keyCode == 13) {
            ks_self.$el.find('.ks_fa_icon_search').click()
        }
    }

    // ----------------------------------------------------------------------
    // v17 additions reproducing Odoo 15 inherited core behaviours
    // ----------------------------------------------------------------------
    // v15 FieldBinary._onClearClick -> _clearFile -> _setValue(false)
    _onClearClick(ev) {
        this._setValue(false);
    }

    // v15: bootstrap modal data-dismiss="modal" buttons close the dialog
    _onModalDismiss(ev) {
        this._ksHideIconModal();
    }

    _ksShowIconModal() {
        var $modal = this.$el.find('#ks_icon_container_modal_id');
        if (!$modal.length || $modal.hasClass('show')) {
            return;
        }
        $modal.addClass('show');
        $modal.css('display', 'block');
        document.body.classList.add('modal-open');
        var self = this;
        if (!this._ksBackdrop) {
            var backdrop = document.createElement('div');
            backdrop.className = 'modal-backdrop fade show';
            backdrop.addEventListener('click', function () {
                self._ksHideIconModal();
            });
            document.body.appendChild(backdrop);
            this._ksBackdrop = backdrop;
        }
        this._ksKeyHandler = function (e) {
            if (e.key === 'Escape') {
                self._ksHideIconModal();
            }
        };
        $(document).on('keydown.ks_icon_modal', this._ksKeyHandler);
    }

    _ksHideIconModal() {
        var $modal = this.$el.find('#ks_icon_container_modal_id');
        $modal.removeClass('show');
        $modal.css('display', '');
        document.body.classList.remove('modal-open');
        this._ksCleanupModal();
    }

    _ksCleanupModal() {
        if (this._ksBackdrop) {
            this._ksBackdrop.remove();
            this._ksBackdrop = false;
        }
        if (this._ksKeyHandler) {
            $(document).off('keydown.ks_icon_modal', this._ksKeyHandler);
            this._ksKeyHandler = false;
        }
    }
}

registry.add('ks_image_widget', KsImageWidget);

export default {
    KsImageWidget: KsImageWidget,
};
