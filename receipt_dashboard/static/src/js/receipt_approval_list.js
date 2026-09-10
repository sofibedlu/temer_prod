/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";

patch(ListController.prototype, {
    setup() {
        super.setup();
        if (this.props.resModel === 'receipt.approval.record') {
            // Hide buttons immediately on load
            setTimeout(() => {
                this._hideButtons();
                // Set up observer for checkbox changes
                this._setupCheckboxObserver();
            }, 300);
        }
    },

    /**
     * Setup observer to watch for checkbox changes
     */
    _setupCheckboxObserver() {
        // Watch for checkbox changes
        const table = document.querySelector('.o_list_table, table');
        if (table) {
            table.addEventListener('change', (e) => {
                if (e.target.type === 'checkbox') {
                    // Immediate update when checkbox changes
                    setTimeout(() => {
                        this._updateButtonStates();
                    }, 50);
                }
            }, true);
        }
        
        // Also watch for click events on checkboxes
        document.addEventListener('click', (e) => {
            if (e.target.type === 'checkbox' && e.target.closest('.o_list_table, table')) {
                setTimeout(() => {
                    this._updateButtonStates();
                }, 50);
            }
        }, true);
    },

    /**
     * Hide buttons immediately
     */
    _hideButtons() {
        const approveBtn = document.querySelector('.approve-btn');
        const denyBtn = document.querySelector('.deny-btn');
        if (approveBtn) approveBtn.style.display = 'none';
        if (denyBtn) denyBtn.style.display = 'none';
    },

    /**
     * Get states from selected rows in DOM
     */
    _getStatesFromSelectedRows() {
        const states = [];
        // Find all checked checkboxes in the table
        const checkboxes = document.querySelectorAll('table tbody tr input[type="checkbox"]:checked, .o_list_table tbody tr input[type="checkbox"]:checked');
        
        checkboxes.forEach(checkbox => {
            const row = checkbox.closest('tr');
            if (row) {
                // Find state column - try multiple ways
                const stateCell = row.querySelector('td[name="state"], td[data-name="state"]');
                if (stateCell) {
                    const badge = stateCell.querySelector('.badge, [class*="badge"]');
                    if (badge) {
                        const text = badge.textContent.trim().toLowerCase();
                        if (text === 'draft') states.push('draft');
                        else if (text === 'approved') states.push('approved');
                        else if (text === 'denied') states.push('denied');
                    } else {
                        // Fallback: check cell text
                        const cellText = stateCell.textContent.trim().toLowerCase();
                        if (cellText === 'draft') states.push('draft');
                        else if (cellText === 'approved') states.push('approved');
                        else if (cellText === 'denied') states.push('denied');
                    }
                }
            }
        });
        
        return states;
    },

    /**
     * Update button states based on selection
     */
    _updateButtonStates() {
        if (this.props.resModel !== 'receipt.approval.record') {
            return;
        }
        
        const approveBtn = document.querySelector('.approve-btn');
        const denyBtn = document.querySelector('.deny-btn');
        
        if (!approveBtn || !denyBtn) {
            // Retry if buttons not found
            setTimeout(() => this._updateButtonStates(), 100);
            return;
        }
        
        // Get states directly from DOM - most reliable
        const states = this._getStatesFromSelectedRows();
        const hasSelection = states.length > 0;
        
        // Only show if ALL selected are draft
        const allDraft = hasSelection && states.every(state => state === 'draft');
        
        // Update buttons immediately
        if (approveBtn) {
            if (allDraft) {
                approveBtn.style.display = '';
                approveBtn.disabled = false;
                approveBtn.classList.remove('o_disabled');
            } else {
                approveBtn.style.display = 'none';
                approveBtn.disabled = true;
                approveBtn.classList.add('o_disabled');
            }
        }
        if (denyBtn) {
            if (allDraft) {
                denyBtn.style.display = '';
                denyBtn.disabled = false;
                denyBtn.classList.remove('o_disabled');
            } else {
                denyBtn.style.display = 'none';
                denyBtn.disabled = true;
                denyBtn.classList.add('o_disabled');
            }
        }
    },

    /**
     * Override to update button states when selection changes
     */
    async onSelectionUpdate(selection) {
        await super.onSelectionUpdate?.(selection);
        if (this.props.resModel === 'receipt.approval.record') {
            // Update immediately and also with small delay for DOM updates
            this._updateButtonStates();
            setTimeout(() => {
                this._updateButtonStates();
            }, 100);
        }
    },
});

