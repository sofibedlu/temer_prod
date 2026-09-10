/** @odoo-module **/

import { Component, useState, onWillUpdateProps } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class SmoothSliderField extends Component {
    static template = "collection_progress_integration.SmoothSlider";
    static props = {
        ...standardFieldProps,
        max_value: { type: Number, optional: true },
        step: { type: Number, optional: true },
    };

    setup() {
        this.state = useState({
            value: this.props.record.data[this.props.name] || 0.0,
        });

        onWillUpdateProps((nextProps) => {
            this.state.value = nextProps.record.data[nextProps.name] || 0.0;
        });
    }

    get max() { return this.props.max_value !== undefined ? this.props.max_value : 100; }
    get step() { return this.props.step !== undefined ? this.props.step : 1; }

    get percentage() {
        const val = this.props.record.data[this.props.name] || 0;
        return (val / this.max) * 100;
    }

    get displayValue() {
        return parseFloat(this.state.value).toFixed(1);
    }

    onInput(ev) {
        this.state.value = parseFloat(ev.target.value);
    }

    onChange(ev) {
        const val = parseFloat(ev.target.value);
        this.state.value = val;
        this.props.record.update({[this.props.name]: val });
    }
}

export const smoothSliderField = {
    component: SmoothSliderField,
    supportedTypes: ["float", "integer"],
    extractProps: ({ options }) => ({
        max_value: options.max_value,
        step: options.step,
    }),
};

registry.category("fields").add("smooth_slider", smoothSliderField);