/** @odoo-module **/

import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";

patch(FormController.prototype, {
    /**
     * Override to ensure fields stay in one row for sales report
     */
    setup() {
        super.setup();
        if (this.props.resModel === 'sales.report') {
            // Hide save/cancel buttons
            this.props.noCreate = true;
            this.props.noEdit = true;
        }
    },

    /**
     * Override render to apply custom styling
     */
    async render() {
        await super.render(...arguments);
        if (this.props.resModel === 'sales.report') {
            setTimeout(() => this._applyCustomLayout(), 300);
        }
    },

    /**
     * Apply custom layout for sales report
     */
    _applyCustomLayout() {
        const form = document.querySelector('form[data-model="sales.report"]');
        if (!form) {
            setTimeout(() => this._applyCustomLayout(), 100);
            return;
        }

        // Hide save and cancel buttons
        const saveBtn = form.querySelector('.o_form_button_save');
        const cancelBtn = form.querySelector('.o_form_button_cancel');
        if (saveBtn) saveBtn.style.display = 'none';
        if (cancelBtn) cancelBtn.style.display = 'none';

        // Ensure filter row layout
        const filterRow = form.querySelector('.sales_report_filters_row');
        if (filterRow) {
            filterRow.style.display = 'flex';
            filterRow.style.flexWrap = 'nowrap';
            filterRow.style.alignItems = 'center';
            filterRow.style.gap = '15px';
            
            // Make fields medium size
            const fieldWidgets = filterRow.querySelectorAll('.o_field_widget');
            fieldWidgets.forEach(widget => {
                widget.style.minWidth = '200px';
                widget.style.flexShrink = '0';
                const input = widget.querySelector('input, select');
                if (input) {
                    input.style.minWidth = '200px';
                    input.style.fontSize = '14px';
                    input.style.padding = '8px 12px';
                }
            });

            // Position button next to date fields
            const button = filterRow.querySelector('button[name="action_refresh_report"]');
            if (button) {
                button.style.marginLeft = '0';
                button.style.padding = '8px 20px';
            }
        }

        // Make table larger
        const table = form.querySelector('.sales_report_table');
        if (table) {
            table.style.fontSize = '16px';
            const cells = table.querySelectorAll('th, td');
            cells.forEach(cell => {
                cell.style.padding = '14px';
                cell.style.fontSize = '15px';
            });
        }
    },
});

