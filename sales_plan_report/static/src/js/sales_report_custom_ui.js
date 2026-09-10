/** @odoo-module **/

import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";

patch(FormController.prototype, {
    setup() {
        super.setup();
        if (this.props.resModel === 'sales.report') {
            this.isCustomReport = true;
        }
    },

    async render() {
        await super.render(...arguments);
        if (this.isCustomReport) {
            console.log('Sales Report: Starting custom UI render');
            // Use multiple attempts to ensure DOM is ready
            setTimeout(() => this._renderCustomUI(), 200);
        }
    },

    async _renderCustomUI() {
        let attempts = 0;
        const maxAttempts = 20;
        
        const tryRender = async () => {
            attempts++;
            console.log(`Sales Report: Attempt ${attempts} to render custom UI`);
            
            // Try multiple selectors
            let form = document.querySelector('form.sales_report_custom_form');
            if (!form) {
                form = document.querySelector('form[data-model="sales.report"]');
            }
            if (!form) {
                form = document.querySelector('.o_form_view form');
            }
            
            if (!form && attempts < maxAttempts) {
                setTimeout(tryRender, 200);
                return;
            }
            
            if (!form) {
                console.error('Sales Report: Form not found after multiple attempts');
                return;
            }
            
            console.log('Sales Report: Form found', form);

            // Hide all Odoo form elements
            const sheet = form.querySelector('sheet');
            if (sheet) {
                sheet.style.padding = '0';
                sheet.style.background = 'transparent';
            }
            
            // Hide Odoo form header and buttons
            const formHeader = form.querySelector('.o_form_header');
            if (formHeader) formHeader.style.display = 'none';
            const formButtons = form.querySelectorAll('.o_form_button');
            formButtons.forEach(btn => btn.style.display = 'none');
            
            const container = form.querySelector('#sales_report_custom_container');
            if (!container && attempts < maxAttempts) {
                setTimeout(tryRender, 200);
                return;
            }
            
            if (!container) {
                console.error('Container not found');
                return;
            }

            // Get form data - try multiple ways to access the record
            let record = null;
            if (this.model?.root) {
                record = this.model.root;
            } else if (this.props?.record) {
                record = this.props.record;
            } else if (this.model?.resModel === 'sales.report') {
                // Try to get the record from the model
                const records = this.model.records;
                if (records && records.length > 0) {
                    record = records[0];
                }
            }
            
            if (!record && attempts < maxAttempts) {
                console.log(`Sales Report: Record not found, attempt ${attempts}/${maxAttempts}`);
                setTimeout(tryRender, 200);
                return;
            }
            
            if (!record) {
                console.error('Sales Report: Record not found after all attempts');
                container.innerHTML = '<div style="padding: 40px; text-align: center;"><h3>Sales Performance Report</h3><p style="color: red;">Could not load report data. Please refresh the page.</p><p style="color: #666; font-size: 12px;">Check browser console (F12) for details.</p></div>';
                container.style.display = 'block';
                return;
            }
            
            try {
                console.log('Sales Report: Record found, loading data...', record);
                
                // Ensure record is loaded
                if (record.load && typeof record.load === 'function') {
                    await record.load();
                }
                
                // Get data from record
                let data = {};
                if (record.data) {
                    data = record.data;
                } else if (record._values) {
                    data = record._values;
                } else if (record.resData) {
                    data = record.resData;
                }
                
                console.log('Sales Report: Data loaded', data);

                // If no data yet, show initial form
                if (!data.report_type) {
                    container.innerHTML = this._buildInitialForm(data);
                    container.style.display = 'block';
                    this._setupCustomEventListeners();
                    return;
                }

                // Build custom UI
                const customHTML = this._buildCustomUI(data);
                container.innerHTML = customHTML;
                container.style.display = 'block';
                container.style.padding = '0';
                container.style.margin = '0';
                container.style.width = '100%';
                container.style.background = 'white';

                // Setup event listeners
                this._setupCustomEventListeners();
                await this._populateSelectFields(data);
                console.log('Sales Report: Custom UI rendered successfully');
            } catch (error) {
                console.error('Sales Report: Error rendering custom UI:', error);
                container.innerHTML = `<div style="padding: 40px; text-align: center;"><h3>Error Loading Report</h3><p style="color: red;">${error.message || 'Unknown error'}</p><p style="color: #666; font-size: 12px; margin-top: 20px;">Please check the browser console (F12) for more details.</p><pre style="text-align: left; background: #f5f5f5; padding: 10px; margin-top: 10px; font-size: 11px;">${error.stack || ''}</pre></div>`;
                container.style.display = 'block';
            }
        };
        
        tryRender();
    },

    _buildInitialForm(data) {
        const reportType = data.report_type || 'wing';
        return `
            <div style="padding: 40px; background: white; min-height: calc(100vh - 100px);">
                <h2 style="text-align: center; margin-bottom: 30px;">Sales Performance Report</h2>
                <div style="max-width: 600px; margin: 0 auto; padding: 30px; background: #f8f9fa; border-radius: 8px;">
                    <div style="margin-bottom: 20px; display: flex; align-items: center; gap: 15px; flex-wrap: wrap;">
                        <select id="custom_wing_select" style="min-width: 200px; padding: 8px; font-size: 14px; display: ${reportType === 'wing' ? 'block' : 'none'};">
                            <option value="">Select Wing...</option>
                        </select>
                        <select id="custom_supervisor_select" style="min-width: 200px; padding: 8px; font-size: 14px; display: ${reportType === 'supervisor' ? 'block' : 'none'};">
                            <option value="">Select Supervisor...</option>
                        </select>
                        <input type="date" id="custom_date_from" style="min-width: 150px; padding: 8px; font-size: 14px;"/>
                        <input type="date" id="custom_date_to" style="min-width: 150px; padding: 8px; font-size: 14px;"/>
                        <button id="custom_refresh_btn" style="padding: 8px 20px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 14px;">Generate Report</button>
                    </div>
                    <p style="text-align: center; color: #666; font-size: 14px;">Please select ${reportType === 'wing' ? 'a wing' : 'a supervisor'} and date range to generate the report.</p>
                </div>
            </div>
        `;
    },

    _buildCustomUI(data) {
        if (!data) {
            return '<div style="padding: 20px;">No data available. Please refresh.</div>';
        }
        
        const metrics = [
            { key: 'prospects', label: 'Prospects (Leads)' },
            { key: 'follow_ups', label: 'Follow-ups' },
            { key: 'site_visits', label: 'Site Visits' },
            { key: 'office_visits', label: 'Office Visits' },
            { key: 'total_visits', label: 'Total Visits (Site + Office)' },
            { key: 'unit_reservations', label: 'Total unit reservations' },
            { key: 'deals_closed', label: 'Deals Closed (QTY)' },
        ];

        // Format date for input field
        const formatDateForInput = (dateStr) => {
            if (!dateStr) return '';
            if (typeof dateStr === 'string') {
                return dateStr.split(' ')[0]; // Remove time if present
            }
            return dateStr;
        };

        let html = `
            <div style="padding: 20px; background: white; min-height: calc(100vh - 100px);">
                <div style="margin-bottom: 20px; display: flex; align-items: center; gap: 15px; flex-wrap: wrap; padding: 15px; background: #f8f9fa; border-radius: 6px;">
                    <select id="custom_wing_select" style="min-width: 200px; padding: 8px; font-size: 14px; display: ${data.report_type === 'wing' ? 'block' : 'none'};">
                        <option value="">Select Wing...</option>
                    </select>
                    <select id="custom_supervisor_select" style="min-width: 200px; padding: 8px; font-size: 14px; display: ${data.report_type === 'supervisor' ? 'block' : 'none'};">
                        <option value="">Select Supervisor...</option>
                    </select>
                    <input type="date" id="custom_date_from" value="${formatDateForInput(data.date_from)}" style="min-width: 150px; padding: 8px; font-size: 14px;"/>
                    <input type="date" id="custom_date_to" value="${formatDateForInput(data.date_to)}" style="min-width: 150px; padding: 8px; font-size: 14px;"/>
                    <button id="custom_refresh_btn" style="padding: 8px 20px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 14px;">Refresh Report</button>
                </div>

                <div style="overflow-x: auto;">
                    <table id="custom_report_table" style="width: 100%; border-collapse: collapse; font-size: 14px; background: white;">
                        <thead>
                            <tr style="background: #343a40; color: white;">
                                <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6; font-weight: bold;">Metric</th>
                                <th style="padding: 12px; text-align: center; border: 1px solid #dee2e6; font-weight: bold;">Actual Previous week</th>
                                <th style="padding: 12px; text-align: center; border: 1px solid #dee2e6; font-weight: bold; color: red;">Plan</th>
                                <th style="padding: 12px; text-align: center; border: 1px solid #dee2e6; font-weight: bold;">Actual</th>
                                <th style="padding: 12px; text-align: center; border: 1px solid #dee2e6; font-weight: bold;">Difference<br/>(This week - Previous week)</th>
                                <th style="padding: 12px; text-align: center; border: 1px solid #dee2e6; font-weight: bold;">Difference<br/>(Actual - Plan)</th>
                                <th style="padding: 12px; text-align: center; border: 1px solid #dee2e6; font-weight: bold;">Conversion<br/>(sales/leads)</th>
                            </tr>
                        </thead>
                        <tbody>
        `;

        metrics.forEach(metric => {
            const prevWeek = data[`actual_previous_week_${metric.key}`] || 0;
            const plan = data[`plan_${metric.key}`] || 0;
            const actual = data[`actual_${metric.key}`] || 0;
            const diffWeek = data[`diff_week_${metric.key}`] || 0;
            const diffPlan = data[`diff_${metric.key}`] || 0;
            const conversion = metric.key === 'deals_closed' ? (data.conversion_rate || 0).toFixed(4) : '';

            html += `
                <tr>
                    <td style="padding: 10px; border: 1px solid #dee2e6; font-weight: 600;">${metric.label}</td>
                    <td style="padding: 10px; border: 1px solid #dee2e6; text-align: center;">${prevWeek}</td>
                    <td style="padding: 10px; border: 1px solid #dee2e6; text-align: center; color: red;">${plan}</td>
                    <td style="padding: 10px; border: 1px solid #dee2e6; text-align: center;">${actual}</td>
                    <td style="padding: 10px; border: 1px solid #dee2e6; text-align: center;">${diffWeek}</td>
                    <td style="padding: 10px; border: 1px solid #dee2e6; text-align: center;">${diffPlan}</td>
                    <td style="padding: 10px; border: 1px solid #dee2e6; text-align: center;">${conversion}</td>
                </tr>
            `;
        });

        html += `
                        </tbody>
                    </table>
                </div>
            </div>
        `;

        return html;
    },

    async _populateSelectFields(data) {
        const wingSelect = document.getElementById('custom_wing_select');
        const supervisorSelect = document.getElementById('custom_supervisor_select');

        if (wingSelect && data.report_type === 'wing') {
            try {
                // Try multiple ways to access ORM
                let orm = null;
                if (this.model?.orm) {
                    orm = this.model.orm;
                } else if (this.env?.services?.orm) {
                    orm = this.env.services.orm;
                } else if (this.props?.env?.services?.orm) {
                    orm = this.props.env.services.orm;
                }
                
                if (orm && typeof orm.searchRead === 'function') {
                    const wings = await orm.searchRead('property.sales.wing', [], ['id', 'name']);
                    wings.forEach(wing => {
                        const option = document.createElement('option');
                        option.value = wing.id;
                        option.textContent = wing.name;
                        if (data.wing_id && (data.wing_id[0] === wing.id || data.wing_id === wing.id)) {
                            option.selected = true;
                        }
                        wingSelect.appendChild(option);
                    });
                    wingSelect.addEventListener('change', () => this._refreshCustomReport());
                } else {
                    console.warn('Sales Report: ORM service not available, skipping wing population');
                }
            } catch (error) {
                console.error('Error loading wings:', error);
            }
        }

        if (supervisorSelect && data.report_type === 'supervisor') {
            try {
                // Try multiple ways to access ORM
                let orm = null;
                if (this.model?.orm) {
                    orm = this.model.orm;
                } else if (this.env?.services?.orm) {
                    orm = this.env.services.orm;
                } else if (this.props?.env?.services?.orm) {
                    orm = this.props.env.services.orm;
                }
                
                if (orm && typeof orm.searchRead === 'function') {
                    const supervisors = await orm.searchRead('property.sales.supervisor', [], ['id', 'name']);
                    supervisors.forEach(supervisor => {
                        const option = document.createElement('option');
                        option.value = supervisor.id;
                        option.textContent = supervisor.name;
                        if (data.supervisor_id && (data.supervisor_id[0] === supervisor.id || data.supervisor_id === supervisor.id)) {
                            option.selected = true;
                        }
                        supervisorSelect.appendChild(option);
                    });
                    supervisorSelect.addEventListener('change', () => this._refreshCustomReport());
                } else {
                    console.warn('Sales Report: ORM service not available, skipping supervisor population');
                }
            } catch (error) {
                console.error('Error loading supervisors:', error);
            }
        }
    },

    _setupCustomEventListeners() {
        const refreshBtn = document.getElementById('custom_refresh_btn');
        if (refreshBtn) {
            // Remove existing listeners
            const newBtn = refreshBtn.cloneNode(true);
            refreshBtn.parentNode.replaceChild(newBtn, refreshBtn);
            newBtn.addEventListener('click', () => this._refreshCustomReport());
        }

        const dateFrom = document.getElementById('custom_date_from');
        const dateTo = document.getElementById('custom_date_to');
        if (dateFrom) {
            dateFrom.removeEventListener('change', this._refreshCustomReport);
            dateFrom.addEventListener('change', () => this._refreshCustomReport());
        }
        if (dateTo) {
            dateTo.removeEventListener('change', this._refreshCustomReport);
            dateTo.addEventListener('change', () => this._refreshCustomReport());
        }
    },

    async _refreshCustomReport() {
        try {
            const record = this.model?.root || this.props?.record;
            if (!record) {
                console.error('Sales Report: No record found for refresh');
                return;
            }

            const dateFrom = document.getElementById('custom_date_from')?.value;
            const dateTo = document.getElementById('custom_date_to')?.value;
            const wingSelect = document.getElementById('custom_wing_select');
            const supervisorSelect = document.getElementById('custom_supervisor_select');

            if (!dateFrom || !dateTo) {
                alert('Please select both start and end dates.');
                return;
            }

            const updateData = {
                date_from: dateFrom,
                date_to: dateTo,
            };

            if (wingSelect?.value) {
                updateData.wing_id = parseInt(wingSelect.value);
            }
            if (supervisorSelect?.value) {
                updateData.supervisor_id = parseInt(supervisorSelect.value);
            }

            console.log('Sales Report: Updating record with', updateData);
            
            if (record.update) {
                await record.update(updateData);
            }
            
            if (record.save) {
                await record.save();
            }
            
            if (record.load) {
                await record.load();
            }
            
            // Get updated data
            let data = record.data || record._values || record.resData || {};
            console.log('Sales Report: Refreshed data', data);
            
            // Re-render UI
            const container = document.querySelector('#sales_report_custom_container');
            if (container) {
                container.innerHTML = this._buildCustomUI(data);
                this._setupCustomEventListeners();
                await this._populateSelectFields(data);
            }
        } catch (error) {
            console.error('Sales Report: Error refreshing report:', error);
            alert('Error refreshing report: ' + (error.message || 'Unknown error'));
        }
    },
});

