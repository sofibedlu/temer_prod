/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";

patch(ListController.prototype, {
    setup() {
        super.setup();
        if (this.props.resModel === 'payment.approval.record') {
            // Hide buttons immediately on load and create total container
            setTimeout(() => {
                this._hideButtons();
                this._createSelectedTotalContainer();
                // Set up observer for checkbox changes
                this._setupCheckboxObserver();
            }, 300);
        }
    },

    /**
     * Create the selected total container element
     */
    _createSelectedTotalContainer() {
        if (this.props.resModel !== 'payment.approval.record') {
            return;
        }
        
        // Check if container already exists
        let totalContainer = document.querySelector('.selected-total-container');
        if (totalContainer) {
            return;
        }
        
        // Find the table or list container
        const listView = document.querySelector('.o_list_view, .o_list_renderer');
        if (!listView) {
            // Retry if not found
            setTimeout(() => this._createSelectedTotalContainer(), 200);
            return;
        }
        
        // Create the container element
        totalContainer = document.createElement('div');
        totalContainer.className = 'selected-total-container';
        totalContainer.style.cssText = 'display: none; padding: 8px; background-color: #f8f9fa; border-bottom: 1px solid #dee2e6; margin-bottom: 8px;';
        
        const label = document.createElement('span');
        label.className = 'selected-total-label';
        label.style.cssText = 'font-weight: bold; margin-right: 10px;';
        label.textContent = 'Selected Total:';
        
        const amount = document.createElement('span');
        amount.className = 'selected-total-amount';
        amount.style.cssText = 'font-size: 16px; color: #007bff;';
        
        totalContainer.appendChild(label);
        totalContainer.appendChild(amount);
        
        // Insert before the table
        const table = listView.querySelector('table, .o_list_table');
        if (table && table.parentNode) {
            table.parentNode.insertBefore(totalContainer, table);
        } else {
            // Fallback: insert at the beginning of listView
            listView.insertBefore(totalContainer, listView.firstChild);
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
                        this._updateSelectedTotal();
                    }, 50);
                }
            }, true);
        }
        
        // Also watch for click events on checkboxes
        document.addEventListener('click', (e) => {
            if (e.target.type === 'checkbox' && e.target.closest('.o_list_table, table')) {
                setTimeout(() => {
                    this._updateButtonStates();
                    this._updateSelectedTotal();
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
     * Get amount from selected rows in DOM
     */
    _getAmountsFromSelectedRows() {
        const amounts = [];
        // Find all checked checkboxes in the table
        const checkboxes = document.querySelectorAll('table tbody tr input[type="checkbox"]:checked, .o_list_table tbody tr input[type="checkbox"]:checked');
        
        checkboxes.forEach(checkbox => {
            const row = checkbox.closest('tr');
            if (row) {
                // Find amount column - try multiple ways
                const amountCell = row.querySelector('td[name="amount"], td[data-name="amount"]');
                if (amountCell) {
                    // Get text content and parse amount
                    const text = amountCell.textContent.trim();
                    // Remove currency symbols and parse number
                    const amountText = text.replace(/[^\d.,-]/g, '').replace(/,/g, '');
                    const amount = parseFloat(amountText);
                    if (!isNaN(amount)) {
                        amounts.push(amount);
                    }
                }
            }
        });
        
        return amounts;
    },

    /**
     * Update selected total display
     */
    _updateSelectedTotal() {
        if (this.props.resModel !== 'payment.approval.record') {
            return;
        }
        
        // Create container if it doesn't exist
        this._createSelectedTotalContainer();
        
        const totalContainer = document.querySelector('.selected-total-container');
        const totalAmount = document.querySelector('.selected-total-amount');
        
        if (!totalContainer || !totalAmount) {
            // Retry if not found
            setTimeout(() => this._updateSelectedTotal(), 100);
            return;
        }
        
        // Get amounts from selected rows
        const amounts = this._getAmountsFromSelectedRows();
        const selectedCount = amounts.length;
        const total = amounts.reduce((sum, amt) => sum + amt, 0);
        
        if (selectedCount > 0) {
            // Format the total with currency symbol (assuming same currency for all)
            totalAmount.textContent = `${selectedCount} item(s) - Total: ${total.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
            totalContainer.style.display = 'block';
        } else {
            totalContainer.style.display = 'none';
        }
    },

    /**
     * Update button states based on selection
     */
    _updateButtonStates() {
        if (this.props.resModel !== 'payment.approval.record') {
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
        
        // Update selected total display
        this._updateSelectedTotal();
    },

    /**
     * Override to update button states when selection changes
     */
    async onSelectionUpdate(selection) {
        await super.onSelectionUpdate?.(selection);
        if (this.props.resModel === 'payment.approval.record') {
            // Update immediately and also with small delay for DOM updates
            this._updateButtonStates();
            this._updateSelectedTotal();
            setTimeout(() => {
                this._updateButtonStates();
                this._updateSelectedTotal();
            }, 100);
        }
    },
});

