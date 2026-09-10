/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

// Field patch for phone validation
const phoneFieldPatch = {
    _patchPhoneFields: function() {
        const self = this;
        
        // Check both phone_no and phone_ids fields
        const phoneNoInput = this.el.querySelector('input[name="phone_no"]');
        const phoneIdsWidget = this.el.querySelector('.o_field_many2many[name="phone_ids"]');

        if (!phoneNoInput && !phoneIdsWidget) return;

        // Create validation message elements
        let messageEl = this.el.querySelector('.o_phone_validation_msg');
        if (!messageEl) {
            messageEl = document.createElement('div');
            messageEl.className = 'o_phone_validation_msg alert';
            messageEl.style.cssText = 'padding: 5px; margin-top: 5px; display: none;';
            messageEl.innerHTML = '<i class="fa fa-warning me-2"></i><span class="o_phone_validation_text"></span>';
            // Add message near the fields
            const container = phoneNoInput ? phoneNoInput.parentNode : phoneIdsWidget.parentNode;
            container.appendChild(messageEl);
        }

        let debounceTimer = null;

        // Function to check both fields
        const checkBothFields = function() {
            let phone_no = '';
            let phone_ids = [];

            // Get phone_no value
            if (phoneNoInput) {
                phone_no = phoneNoInput.value.trim();
            }

            // Get phone_ids values
            if (phoneIdsWidget) {
                const tags = phoneIdsWidget.querySelectorAll('.o_tag');
                phone_ids = Array.from(tags).map(tag => {
                    const dataId = tag.getAttribute('data-id');
                    return dataId ? parseInt(dataId) : null;
                }).filter(id => id !== null);
            }

            if (debounceTimer) {
                clearTimeout(debounceTimer);
            }

            if (phone_no || phone_ids.length > 0) {
                debounceTimer = setTimeout(() => {
                    self._checkPhoneNumbers(phone_no, phone_ids, messageEl);
                }, 800);
            } else {
                messageEl.style.display = 'none';
            }
        };

        // Set up event listeners for phone_no field
        if (phoneNoInput) {
            phoneNoInput.addEventListener('input', checkBothFields);
            phoneNoInput.addEventListener('blur', checkBothFields);
        }

        // Set up event listeners for phone_ids field
        if (phoneIdsWidget) {
            // Use MutationObserver to detect changes in the many2many widget
            const observer = new MutationObserver(checkBothFields);
            observer.observe(phoneIdsWidget, { 
                childList: true, 
                subtree: true,
                attributes: true 
            });

            phoneIdsWidget.addEventListener('blur', checkBothFields);
        }
    },

    _checkPhoneNumbers: async function(phone_no, phone_ids, messageEl) {
        try {
            const orm = useService("orm");

            // Get current record ID if available
            const form = messageEl.closest('.o_form_view');
            const recordIdInput = form.querySelector('input[name="id"]');
            const recordId = recordIdInput ? parseInt(recordIdInput.value) || false : false;

            const result = await orm.call(
                "crm.lead",
                "check_duplicate_phones",
                [phone_no, phone_ids, recordId]
            );

            if (result.exists) {
                messageEl.className = 'o_phone_validation_msg alert alert-warning';
                
                let message = '';
                if (result.duplicate_type === 'phone_no') {
                    message = `Phone number ${result.duplicate_phone} is already registered.`;
                } else if (result.duplicate_type === 'phone_ids') {
                    if (result.duplicate_count === 1) {
                        message = `Phone number ${result.duplicate_phones} is already registered.`;
                    } else {
                        message = `Phone numbers ${result.duplicate_phones} are already registered.`;
                    }
                } else if (result.duplicate_type === 'both') {
                    message = `Phone number ${result.duplicate_phone} and phone numbers ${result.duplicate_phones} are already registered.`;
                }
                
                messageEl.querySelector('.o_phone_validation_text').textContent = message;
                messageEl.style.display = 'block';
            } else {
                messageEl.className = 'o_phone_validation_msg alert alert-success';
                messageEl.querySelector('.o_phone_validation_text').textContent =
                    'All phone numbers are available';
                messageEl.style.display = 'block';

                // Auto-hide success message after 3 seconds
                setTimeout(() => {
                    messageEl.style.display = 'none';
                }, 3000);
            }
        } catch (error) {
            console.error("Phone validation error:", error);
        }
    }
};

// Form controller patch to prevent saving with duplicate phones
const formControllerPatch = {
    setup() {
        this._super.apply(this, arguments);

        this.orm = useService("orm");
        this.notification = useService("notification");

        this._onWillSaveRecord = async (record) => {
            const phone_no = record.data.phone_no;
            let phone_ids = [];
            
            if (record.data.phone_ids && record.data.phone_ids.records) {
                phone_ids = record.data.phone_ids.records.map(rec => rec.id);
            }

            if (phone_no || phone_ids.length > 0) {
                try {
                    const result = await this.orm.call(
                        "crm.lead",
                        "check_duplicate_phones",
                        [phone_no, phone_ids, record.resId || false]
                    );

                    if (result.exists) {
                        let message = '';
                        if (result.duplicate_type === 'phone_no') {
                            message = `Phone number ${result.duplicate_phone} is already registered.`;
                        } else if (result.duplicate_type === 'phone_ids') {
                            if (result.duplicate_count === 1) {
                                message = `Phone number ${result.duplicate_phones} is already registered.`;
                            } else {
                                message = `Phone numbers ${result.duplicate_phones} are already registered.`;
                            }
                        } else if (result.duplicate_type === 'both') {
                            message = `Phone number ${result.duplicate_phone} and phone numbers ${result.duplicate_phones} are already registered.`;
                        }
                        
                        this.notification.add(message, { type: 'danger' });
                        throw new Error("Duplicate phone numbers");
                    }
                } catch (error) {
                    console.error("Phone validation error:", error);
                    throw error;
                }
            }
        };

        // Patch the willSaveRecord method
        const originalWillSaveRecord = this.willSaveRecord;
        this.willSaveRecord = async (record) => {
            await this._onWillSaveRecord(record);
            return originalWillSaveRecord.call(this, record);
        };
    }
};

// Apply patches when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Patch both phone fields
    const forms = document.querySelectorAll('.o_form_view');
    forms.forEach(function(form) {
        const hasPhoneNo = form.querySelector('input[name="phone_no"]');
        const hasPhoneIds = form.querySelector('.o_field_many2many[name="phone_ids"]');
        
        if (hasPhoneNo || hasPhoneIds) {
            phoneFieldPatch._patchPhoneFields.call({ el: form });
        }
    });
});

// Register form controller patch
registry.category("services").add("form_controller_patch", {
    start(env) {
        const formControllerRegistry = registry.category("form_controllers");
        const originalController = formControllerRegistry.get("default");

        const PatchedController = originalController.extend(formControllerPatch);
        formControllerRegistry.add("default", PatchedController);

        return {};
    }
});