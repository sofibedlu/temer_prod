/** @odoo-module **/

import { Component, useState, onWillStart, useEffect } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class SourceLeadReport extends Component {
    setup() {
        this.rpc = useService("rpc");
        
        const today = new Date();
        const formatDate = (date) => {
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            return `${year}-${month}-${day}`;
        };
        
        this.state = useState({
            data: [],
            filtered_data: [],
            loading: false,
            date_from: formatDate(today),
            date_to: formatDate(today),
            source_id: null,
            sources: [],
            show_table: false,
            count: 0,
            search_text: '',
        });

        onWillStart(async () => {
            await this.loadSources();
        });

        useEffect(
            () => {
                this.filterData();
            },
            () => [this.state.search_text, this.state.data]
        );
    }

    filterData() {
        if (!this.state.search_text || !this.state.search_text.trim()) {
            this.state.filtered_data = [...this.state.data];
            return;
        }
        
        const searchLower = this.state.search_text.toLowerCase().trim();
        const filtered = this.state.data.filter(lead => {
            const name = (lead.name || '').toLowerCase();
            const phoneNumbers = (lead.phone_numbers || '').toLowerCase();
            const salesperson = (lead.salesperson_name || '').toLowerCase();
            const createdBy = (lead.created_by || '').toLowerCase();
            const status = (lead.status || '').toLowerCase();
            
            return name.includes(searchLower) ||
                   phoneNumbers.includes(searchLower) ||
                   salesperson.includes(searchLower) ||
                   createdBy.includes(searchLower) ||
                   status.includes(searchLower);
        });
        
        this.state.filtered_data = filtered;
    }

    onSearchChange(ev) {
        this.state.search_text = ev.target.value || '';
    }

    async loadSources() {
        try {
            const result = await this.rpc('/source_lead_report/api/get_sources', {});
            if (result && result.success && result.sources) {
                this.state.sources = result.sources || [];
                // Auto-select first source if only one
                if (this.state.sources.length === 1) {
                    this.state.source_id = this.state.sources[0].id;
                }
            } else {
                this.state.sources = [];
            }
        } catch (error) {
            console.error('Error loading sources:', error);
            this.state.sources = [];
        }
    }

    onSourceChange(ev) {
        const sourceId = ev.target.value ? parseInt(ev.target.value) : null;
        this.state.source_id = sourceId;
        // Hide table when source changes - user must click Show to see new data
        this.state.show_table = false;
        this.state.data = [];
        this.state.filtered_data = [];
        this.state.count = 0;
        this.state.search_text = '';
    }

    onDateFromChange(ev) {
        this.state.date_from = ev.target.value;
        // Hide table when date changes - user must click Show to see new data
        this.state.show_table = false;
        this.state.data = [];
        this.state.filtered_data = [];
        this.state.count = 0;
        this.state.search_text = '';
    }

    onDateToChange(ev) {
        this.state.date_to = ev.target.value;
        // Hide table when date changes - user must click Show to see new data
        this.state.show_table = false;
        this.state.data = [];
        this.state.filtered_data = [];
        this.state.count = 0;
        this.state.search_text = '';
    }

    async onShowClick() {
        if (!this.state.source_id) {
            alert('Please select a source first');
            return;
        }
        
        this.state.loading = true;
        this.state.show_table = false;
        try {
            const params = {
                date_from: this.state.date_from || null,
                date_to: this.state.date_to || null,
                source_id: this.state.source_id,
            };
            
            const result = await this.rpc('/source_lead_report/api/get_data', params);
            
            if (result && result.success) {
                this.state.data = result.data || [];
                this.state.count = result.count || 0;
                this.filterData();
                this.state.show_table = true;
            } else {
                console.error('Error loading data:', result.error);
                this.state.data = [];
                this.state.show_table = false;
            }
        } catch (error) {
            console.error('Error loading lead data:', error);
            this.state.data = [];
            this.state.show_table = false;
        } finally {
            this.state.loading = false;
        }
    }

    async exportExcel() {
        if (!this.state.source_id) {
            alert('Please select a source first');
            return;
        }
        
        try {
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = '/source_lead_report/api/export_excel';
            
            if (this.state.date_from) {
                const input = document.createElement('input');
                input.type = 'hidden';
                input.name = 'date_from';
                input.value = this.state.date_from;
                form.appendChild(input);
            }
            
            if (this.state.date_to) {
                const input = document.createElement('input');
                input.type = 'hidden';
                input.name = 'date_to';
                input.value = this.state.date_to;
                form.appendChild(input);
            }
            
            if (this.state.source_id) {
                const input = document.createElement('input');
                input.type = 'hidden';
                input.name = 'source_id';
                input.value = this.state.source_id;
                form.appendChild(input);
            }
            
            if (this.state.search_text && this.state.search_text.trim()) {
                const input = document.createElement('input');
                input.type = 'hidden';
                input.name = 'search_text';
                input.value = this.state.search_text;
                form.appendChild(input);
            }
            
            document.body.appendChild(form);
            form.submit();
            document.body.removeChild(form);
        } catch (error) {
            console.error('Error exporting Excel:', error);
        }
    }

    async exportPDF() {
        if (!this.state.source_id) {
            alert('Please select a source first');
            return;
        }
        
        try {
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = '/source_lead_report/api/export_pdf';
            form.target = '_blank';
            
            if (this.state.date_from) {
                const input = document.createElement('input');
                input.type = 'hidden';
                input.name = 'date_from';
                input.value = this.state.date_from;
                form.appendChild(input);
            }
            
            if (this.state.date_to) {
                const input = document.createElement('input');
                input.type = 'hidden';
                input.name = 'date_to';
                input.value = this.state.date_to;
                form.appendChild(input);
            }
            
            if (this.state.source_id) {
                const input = document.createElement('input');
                input.type = 'hidden';
                input.name = 'source_id';
                input.value = this.state.source_id;
                form.appendChild(input);
            }
            
            if (this.state.search_text && this.state.search_text.trim()) {
                const input = document.createElement('input');
                input.type = 'hidden';
                input.name = 'search_text';
                input.value = this.state.search_text;
                form.appendChild(input);
            }
            
            document.body.appendChild(form);
            form.submit();
            document.body.removeChild(form);
        } catch (error) {
            console.error('Error exporting PDF:', error);
        }
    }

}

SourceLeadReport.template = "source_lead_report.SourceLeadReport";

registry.category("actions").add("source_lead_report.report", SourceLeadReport);

