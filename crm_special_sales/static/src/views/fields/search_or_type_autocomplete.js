/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { useService, useBus } from "@web/core/utils/hooks";
import { makeContext } from "@web/core/context";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, useRef } from "@odoo/owl";

/**
 * Char field with autocomplete from a related model (name_search).
 * No Create option - user can type new values; created on lead save.
 */
export class SearchOrTypeAutocompleteField extends Component {
    static template = "crm_special_sales.SearchOrTypeAutocomplete";
    static components = { AutoComplete };
    static props = {
        ...standardFieldProps,
        placeholder: { type: String, optional: true },
        resModel: { type: String, optional: true },
        idField: { type: String, optional: true },
        nameField: { type: String, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.inputContainerRef = useRef("inputContainer");
        useBus(this.props.record.model.bus, "WILL_SAVE_URGENTLY", () => this.commitChanges());
        useBus(this.props.record.model.bus, "NEED_LOCAL_CHANGES", (ev) =>
            ev.detail.proms.push(this.commitChanges())
        );
    }

    async commitChanges() {
        const container = this.inputContainerRef.el;
        const input = container?.querySelector?.("input");
        if (!input) return;
        const val = (input.value || "").trim();
        const currentDisplay = (this.props.record.data[this.props.name] || "").trim();
        if (val === currentDisplay) return;
        const idField = this.props.idField;
        const nameField = this.props.nameField;
        const changes = { [this.props.name]: val };
        if (idField) changes[idField] = false;
        if (nameField) changes[nameField] = val || false;
        await this.props.record.update(changes, { save: false });
    }

    get displayValue() {
        return this.props.record.data[this.props.name] || "";
    }

    get context() {
        const { record } = this.props;
        const evalContext = record.getEvalContext ? record.getEvalContext(false) : record.evalContext;
        return makeContext([], evalContext);
    }

    get sources() {
        const resModel = this.props.resModel;
        if (!resModel) return [];
        return [
            {
                placeholder: _t("Loading..."),
                options: this.loadOptions.bind(this),
            },
        ];
    }

    async loadOptions(request) {
        const resModel = this.props.resModel;
        if (!resModel) return [];
        const records = await this.orm.call(resModel, "name_search", [], {
            name: request || "",
            operator: "ilike",
            args: [],
            limit: 15,
            context: this.context,
        });
        return records.map((r) => ({
            value: r[0],
            label: r[1] ? r[1].split("\n")[0] : _t("Unnamed"),
            displayName: r[1],
        }));
    }

    onSelect(option) {
        const idField = this.props.idField;
        const nameField = this.props.nameField;
        const label = option.displayName || option.label || "";
        const changes = {
            [this.props.name]: label,
        };
        // Many2one expects [id, display_name], not raw id
        if (idField) changes[idField] = option.value ? [option.value, label] : false;
        if (nameField) changes[nameField] = false;
        this.props.record.update(changes);
    }

    onBlur({ inputValue }) {
        const val = (inputValue || "").trim();
        const current = (this.props.record.data[this.props.name] || "").trim();
        if (val === current) return;
        const idField = this.props.idField;
        const nameField = this.props.nameField;
        const changes = { [this.props.name]: val };
        if (idField) changes[idField] = false;
        if (nameField) changes[nameField] = val;
        this.props.record.update(changes);
    }

    onChange() {}

    onCancel() {}
}

export const searchOrTypeAutocomplete = {
    component: SearchOrTypeAutocompleteField,
    displayName: _t("Search or type"),
    supportedTypes: ["char"],
    extractProps: ({ attrs, options }) => ({
        placeholder: attrs.placeholder,
        resModel: options?.res_model || attrs.res_model,
        idField: options?.id_field || attrs.id_field,
        nameField: options?.name_field || attrs.name_field,
    }),
};

registry.category("fields").add("search_or_type_autocomplete", searchOrTypeAutocomplete);
