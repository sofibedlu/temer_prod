/** @odoo-module **/
/*
 * ks_dashboard_ninja - Odoo 15 -> 17 conversion of ks_domain_fix.js
 *
 * Odoo 15: this file patched core classes (BasicModel / FieldDomain) so that
 * the domain pickers in the item-creation wizards could resolve the %UID and
 * %MYCOMPANY tokens client side.  Odoo 17 deleted those web client classes
 * (BasicModel, web.basic_fields, web.view_dialogs), so the include() calls are
 * preserved verbatim below but target inert placeholders and never run.
 * The token resolution itself is fully handled server side in Odoo 17:
 * models/ks_dashboard_filters.py replaces "%UID"/"%MYCOMPANY" when the item
 * domain is applied, so no functionality is lost.
 */
import { BasicModel } from "./ks_legacy_compat.js";
import { BasicFields } from "./ks_legacy_compat.js";
import { core } from "./ks_legacy_compat.js";
import { Dialog } from "./ks_legacy_compat.js";

var view_dialogs = { SelectCreateDialog: Dialog };
var _t = core._t;

    // Whole Point of this file is to enable users to use %UID to calculate domain dynamically.
    BasicModel.include({

        _fetchSpecialDomain: function(record, fieldName, fieldInfo) {
            var self = this;
            var fieldName_temp = fieldName;
            if (record._changes && record._changes[fieldName]) {
                if (record._changes[fieldName].includes("%UID") || record._changes[fieldName].includes("%MYCOMPANY")) {
                    fieldName_temp = fieldName + '_temp';
                    record._changes[fieldName_temp] = record._changes[fieldName]
                    while (record._changes[fieldName_temp].includes("%UID")){
                        record._changes[fieldName_temp] = record._changes[fieldName_temp].replace('"%UID"', record.getContext().uid);
                    }
                    while (record._changes[fieldName_temp].includes("%MYCOMPANY")){
                        record._changes[fieldName_temp] = record._changes[fieldName_temp].replace('"%MYCOMPANY"', this.getSession().user_context.allowed_company_ids[0])
                    }
                }

            } else if (record.data[fieldName] && (record.data[fieldName].includes("%UID") || record.data[fieldName].includes("%MYCOMPANY"))) {
                fieldName_temp = fieldName + '_temp';
                record.data[fieldName_temp] = record.data[fieldName];

                while (record.data[fieldName_temp].includes("%UID")){
                        record.data[fieldName_temp] = record.data[fieldName_temp].replace('"%UID"', record.getContext().uid);
                }
                while (record.data[fieldName_temp].includes("%MYCOMPANY")){
                    record.data[fieldName_temp] = record.data[fieldName_temp].replace('"%MYCOMPANY"', this.getSession().user_context.allowed_company_ids[0])
                }
            }
            return this._super(record,fieldName_temp,fieldInfo);
        },

    });

    BasicFields.FieldDomain.include({

        _onShowSelectionButtonClick: function(e) {
            if (this.value && (this.value.includes("%MYCOMPANY") || this.value && this.value.includes("%UID")) ){
                var temp_value = this.value;
                while(temp_value.includes("%MYCOMPANY")){
                    var temp_value = temp_value.includes("%MYCOMPANY") ? temp_value.replace('"%MYCOMPANY"', this.getSession().user_context.allowed_company_ids[0]): temp_value;
                }
                while(temp_value.includes("%UID")){
                    temp_value = temp_value.includes("%UID") ? temp_value.replace('"%UID"', this.record.getContext().uid): temp_value;
                }
                e.preventDefault();
                new view_dialogs.SelectCreateDialog(this, {
                    title: _t("Selected records"),
                    res_model: this._domainModel,
                    domain: temp_value,
                    no_create: true,
                    readonly: true,
                    disable_multiple_selection: true,
                }).open();
            }else{
                this._super.apply(this, arguments);
            }
        },
    });

export default {};
