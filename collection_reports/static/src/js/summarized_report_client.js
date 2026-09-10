/** @odoo-module **/

import { Component, useState, onWillStart, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class SummarizedReportClient extends Component {
    setup() {
        this.notification = useService("notification");
        this.isMounted = true;
        
        // Set default dates to current month
        const today = new Date();
        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
        const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);
        
        const formatDate = (date) => {
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            return `${year}-${month}-${day}`;
        };
        
        this.state = useState({
            loading: true,
            data: [],
            filtered_data: [],
            totals: {},
            date_from: formatDate(firstDay),
            date_to: formatDate(lastDay),
            show_all_dates: false,
            search_text: '',
        });
        
        onWillStart(async () => {
            await this.loadData();
        });
        
        onWillUnmount(() => {
            this.isMounted = false;
        });
    }
    
    onShowAllDatesChange() {
        if (this.state.show_all_dates) {
            this.state.date_from = '';
            this.state.date_to = '';
        } else {
            const today = new Date();
            const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
            const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);
            const formatDate = (date) => {
                const year = date.getFullYear();
                const month = String(date.getMonth() + 1).padStart(2, '0');
                const day = String(date.getDate()).padStart(2, '0');
                return `${year}-${month}-${day}`;
            };
            this.state.date_from = formatDate(firstDay);
            this.state.date_to = formatDate(lastDay);
        }
    }
    
    filterData() {
        let filtered = [...this.state.data];
        
        // Filter by search text
        if (this.state.search_text) {
            const searchLower = this.state.search_text.toLowerCase();
            filtered = filtered.filter(row => {
                const projectName = (row.project_name || '').toLowerCase();
                return projectName.includes(searchLower);
            });
        }
        
        this.state.filtered_data = filtered;
        // Recalculate totals from filtered data
        this.calculateTotalsFromFiltered();
    }
    
    calculateTotalsFromFiltered() {
        // Calculate totals from filtered_data only
        const filtered = this.state.filtered_data || [];
        if (filtered.length === 0) {
            this.state.totals = {};
            return;
        }
        
        this.state.totals = {
            plan_customers: filtered.reduce((sum, row) => sum + (row.plan_customers || 0), 0),
            plan_amount_birr: filtered.reduce((sum, row) => sum + (row.plan_amount_birr || 0), 0),
            plan_amount_dollar: filtered.reduce((sum, row) => sum + (row.plan_amount_dollar || 0), 0),
            execution_customers: filtered.reduce((sum, row) => sum + (row.execution_customers || 0), 0),
            execution_amount_birr: filtered.reduce((sum, row) => sum + (row.execution_amount_birr || 0), 0),
            execution_amount_dollar: filtered.reduce((sum, row) => sum + (row.execution_amount_dollar || 0), 0),
            plan_vs_execution_diff_customers: filtered.reduce((sum, row) => sum + (row.plan_vs_execution_diff_customers || 0), 0),
            plan_vs_execution_diff_birr: filtered.reduce((sum, row) => sum + (row.plan_vs_execution_diff_birr || 0), 0),
            plan_vs_execution_diff_dollar: filtered.reduce((sum, row) => sum + (row.plan_vs_execution_diff_dollar || 0), 0),
            other_customers: filtered.reduce((sum, row) => sum + (row.other_customers || 0), 0),
            other_amount_birr: filtered.reduce((sum, row) => sum + (row.other_amount_birr || 0), 0),
            other_amount_dollar: filtered.reduce((sum, row) => sum + (row.other_amount_dollar || 0), 0),
            total_customers: filtered.reduce((sum, row) => sum + (row.total_customers || 0), 0),
            total_amount_birr: filtered.reduce((sum, row) => sum + (row.total_amount_birr || 0), 0),
            total_amount_dollar: filtered.reduce((sum, row) => sum + (row.total_amount_dollar || 0), 0),
            extension_customers: filtered.reduce((sum, row) => sum + (row.extension_customers || 0), 0),
            extension_amount_birr: filtered.reduce((sum, row) => sum + (row.extension_amount_birr || 0), 0),
            remaining_customers: filtered.reduce((sum, row) => sum + (row.remaining_customers || 0), 0),
            remaining_amount_birr: filtered.reduce((sum, row) => sum + (row.remaining_amount_birr || 0), 0),
            remaining_amount_dollar: filtered.reduce((sum, row) => sum + (row.remaining_amount_dollar || 0), 0),
            comm_text: filtered.reduce((sum, row) => sum + (row.comm_text || 0), 0),
            comm_phone: filtered.reduce((sum, row) => sum + (row.comm_phone || 0), 0),
            comm_letter: filtered.reduce((sum, row) => sum + (row.comm_letter || 0), 0),
            comm_difficulty: filtered.reduce((sum, row) => sum + (row.comm_difficulty || 0), 0),
            comm_service_customers: filtered.reduce((sum, row) => sum + (row.comm_service_customers || 0), 0),
            comm_sno: filtered.reduce((sum, row) => sum + (row.comm_sno || 0), 0),
            partial_letter_not_delivered: filtered.reduce((sum, row) => sum + (row.partial_letter_not_delivered || 0), 0),
            partial_customers: filtered.reduce((sum, row) => sum + (row.partial_customers || 0), 0),
            partial_amount_birr: filtered.reduce((sum, row) => sum + (row.partial_amount_birr || 0), 0),
            partial_amount_dollar: filtered.reduce((sum, row) => sum + (row.partial_amount_dollar || 0), 0),
        };
    }
    
    // Watch for search text changes
    onSearchChange() {
        this.filterData();
    }

    async loadData() {
        if (!this.isMounted) return;
        this.state.loading = true;
        try {
            // Use Odoo's RPC format for JSON requests
            const response = await fetch("/collection_reports/api/summarized_report", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                credentials: "same-origin",
                body: JSON.stringify({
                    jsonrpc: "2.0",
                    method: "call",
                    params: {
                        date_from: this.state.show_all_dates ? null : this.state.date_from,
                        date_to: this.state.show_all_dates ? null : this.state.date_to,
                    },
                }),
            });
            
            if (!this.isMounted) return;
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            console.log("API Response:", result);
            
            if (!this.isMounted) return;
            
            // Handle Odoo JSON-RPC response format
            let data = result;
            if (result && result.result) {
                data = result.result;
            }
            
            if (data && data.success) {
                if (this.isMounted) {
                    this.state.data = data.data || [];
                    this.state.totals = data.totals || {};
                    this.filterData(); // Apply filters
                    console.log("Data loaded:", this.state.data.length, "rows");
                }
            } else {
                if (this.isMounted) {
                    console.error("Error loading data:", data?.error || result?.error || "Unknown error");
                    this.state.data = [];
                    this.state.totals = {};
                }
            }
        } catch (error) {
            if (this.isMounted) {
                console.error("Error loading data:", error);
                this.state.data = [];
                this.state.totals = {};
            } else {
                console.warn("Load data completed after component unmounted, ignoring error:", error);
            }
        } finally {
            if (this.isMounted) {
                this.state.loading = false;
            }
        }
    }

    async exportExcel() {
        if (!this.state.data || this.state.data.length === 0) {
            this.notification.add("No data to export", { type: "warning" });
            return;
        }

        try {
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = '/collection_reports/api/export_excel';
            
            const reportTypeInput = document.createElement('input');
            reportTypeInput.type = 'hidden';
            reportTypeInput.name = 'report_type';
            reportTypeInput.value = 'summarized_report';
            form.appendChild(reportTypeInput);
            
            const dateFromInput = document.createElement('input');
            dateFromInput.type = 'hidden';
            dateFromInput.name = 'date_from';
            dateFromInput.value = this.state.show_all_dates ? '' : (this.state.date_from || '');
            form.appendChild(dateFromInput);
            
            const dateToInput = document.createElement('input');
            dateToInput.type = 'hidden';
            dateToInput.name = 'date_to';
            dateToInput.value = this.state.show_all_dates ? '' : (this.state.date_to || '');
            form.appendChild(dateToInput);
            
            document.body.appendChild(form);
            form.submit();
            document.body.removeChild(form);
            
            this.notification.add("Excel file downloaded successfully", { type: "success" });
        } catch (error) {
            console.error("Error exporting to Excel:", error);
            this.notification.add("Error exporting to Excel: " + error.message, { type: "danger" });
        }
    }

    async exportPDF() {
        if (!this.state.filtered_data || this.state.filtered_data.length === 0) {
            this.notification.add("No data to export", { type: "warning" });
            return;
        }

        try {
            // Generate print-friendly HTML (like wing reports)
            const printWindow = window.open('', '_blank');
            const printContent = this.generatePrintContent();
            
            printWindow.document.write(`
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Summarized Report - ${this.state.date_from || 'All'} to ${this.state.date_to || 'All'}</title>
                    <style>
                        @page {
                            size: A4 landscape;
                            margin: 5mm;
                        }
                        body {
                            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                            margin: 0;
                            padding: 10px;
                            background: #fff;
                            color: #333;
                            font-size: 8px;
                        }
                        .report-header {
                            text-align: center;
                            margin-bottom: 15px;
                            padding-bottom: 8px;
                            border-bottom: 2px solid #2c3e50;
                        }
                        .report-header h1 {
                            color: #2c3e50;
                            margin: 0 0 5px 0;
                            font-size: 16px;
                        }
                        .report-meta {
                            color: #6c757d;
                            font-size: 10px;
                        }
                        table {
                            width: 100%;
                            border-collapse: collapse;
                            margin-top: 10px;
                            font-size: 7px;
                        }
                        th, td {
                            border: 1px solid #ddd;
                            padding: 4px 2px;
                            text-align: center;
                        }
                        th {
                            background-color: #f2f2f2;
                            font-weight: bold;
                        }
                        .green-header, .green-cell {
                            background-color: #d4edda;
                        }
                        tr:nth-child(even) {
                            background-color: #f9f9f9;
                        }
                        .total-row {
                            background-color: #e8f4f8;
                            font-weight: bold;
                        }
                        @media print {
                            body { margin: 0; padding: 5px; }
                            .no-print { display: none; }
                        }
                    </style>
                </head>
                <body>
                    <div class="report-header">
                        <h1>Summarized Report</h1>
                        <div class="report-meta">
                            <p>Date Range: ${this.state.show_all_dates ? 'All Dates' : (this.state.date_from || '') + ' to ' + (this.state.date_to || '')}</p>
                            <p>Generated: ${new Date().toLocaleString()}</p>
                        </div>
                    </div>
                    ${printContent}
                    <div style="text-align: center; margin-top: 20px;" class="no-print">
                        <button onclick="window.print()" style="padding: 10px 25px; background-color: #007bff; color: white; border: none; border-radius: 6px; cursor: pointer; margin: 10px; font-weight: 500;">Print Report</button>
                        <button onclick="window.close()" style="padding: 10px 25px; background-color: #6c757d; color: white; border: none; border-radius: 6px; cursor: pointer; margin: 10px; font-weight: 500;">Close</button>
                    </div>
                    <script>
                        window.onload = function() {
                            setTimeout(function() {
                                window.print();
                            }, 500);
                        };
                    </script>
                </body>
                </html>
            `);
            printWindow.document.close();
            
            this.notification.add("PDF print dialog opened", { type: "success" });
        } catch (error) {
            console.error("Error exporting PDF:", error);
            this.notification.add("Error exporting PDF: " + error.message, { type: "danger" });
        }
    }
    
    generatePrintContent() {
        let html = '<table>';
        
        // Complex multi-level header
        html += '<thead>';
        html += '<tr><th rowspan="4">S.NO</th><th rowspan="4">PROJECT NAME</th>';
        html += '<th colspan="3">COLLECTION PLAN</th>';
        html += '<th colspan="3">COLLECTION REPORT (EXECUTION)</th>';
        html += '<th colspan="3">OTHER COLLECTION</th>';
        html += '<th colspan="3" class="green-header">TOTAL COLLECTION (EXECUTION) REPORT</th>';
        html += '<th colspan="2">PAYMENT EXTENSION</th>';
        html += '<th colspan="3">TOTAL AMOUNT REMAINED UNCOLLECTED</th>';
        html += '<th colspan="6">COMMUNICATION REPORT</th>';
        html += '<th colspan="5">SEMI /PARTIAL PAID</th></tr>';
        
        html += '<tr><th colspan="3"></th><th colspan="3">FROM PLAN</th><th colspan="3"></th>';
        html += '<th colspan="3" class="green-header"></th><th colspan="2"></th><th colspan="3"></th>';
        html += '<th colspan="6"></th><th colspan="5"></th></tr>';
        
        html += '<tr>';
        html += '<th>NUMBER OF CUSTOMERS</th><th>AMOUNT IN BIRR</th><th>AMOUNT IN DOLLAR</th>';
        html += '<th>NUMBER OF CUSTOMERS</th><th>AMOUNT IN BIRR</th><th>COLLECTION IN DOLLAR</th>';
        html += '<th>NUMBER OF CUSTOMERS</th><th>AMOUNT IN BIRR</th><th>COLLECTION IN DOLLAR</th>';
        html += '<th class="green-header">NUMBER OF CUSTOMERS</th><th class="green-header">AMOUNT IN BIRR</th><th class="green-header">COLLECTION IN DOLLAR</th>';
        html += '<th>NUMBER OF CUSTOMERS</th><th>AMOUNT IN BIRR</th>';
        html += '<th>NUMBER OF CUSTOMERS</th><th>AMOUNT IN BIRR</th><th>COLLECTION IN DOLLAR</th>';
        html += '<th>TEXT</th><th>PHONE CALL</th><th>LETTER</th><th>COMMUNICATION DIFFICULTY</th><th>NUMBER OF CUSTOMERS</th><th>S.NO</th>';
        html += '<th>LETTER NOT DELIVERED</th><th>NO OF CUSTOMER</th><th>AMOUNT IN BIRR</th><th>AMOUNT IN DOLLAR</th><th>REMARK</th>';
        html += '</tr></thead><tbody>';
        
        // Data rows
        this.state.filtered_data.forEach(row => {
            const rowClass = row.is_total ? 'total-row' : '';
            html += `<tr class="${rowClass}">`;
            html += `<td>${row.sno || ''}</td>`;
            html += `<td>${row.project_name || ''}</td>`;
            html += `<td>${row.plan_customers || 0}</td>`;
            html += `<td>${(row.plan_amount_birr || 0).toFixed(2)} Birr</td>`;
            html += `<td>$${(row.plan_amount_dollar || 0).toFixed(2)}</td>`;
            html += `<td>${row.execution_customers || 0}</td>`;
            html += `<td>${(row.execution_amount_birr || 0).toFixed(2)} Birr</td>`;
            html += `<td>$${(row.execution_amount_dollar || 0).toFixed(2)}</td>`;
            html += `<td>${row.other_customers || 0}</td>`;
            html += `<td>${(row.other_amount_birr || 0).toFixed(2)} Birr</td>`;
            html += `<td>$${(row.other_amount_dollar || 0).toFixed(2)}</td>`;
            html += `<td class="green-cell">${row.total_customers || 0}</td>`;
            html += `<td class="green-cell">${(row.total_amount_birr || 0).toFixed(2)} Birr</td>`;
            html += `<td class="green-cell">$${(row.total_amount_dollar || 0).toFixed(2)}</td>`;
            html += `<td>${row.extension_customers || 0}</td>`;
            html += `<td>${(row.extension_amount_birr || 0).toFixed(2)} Birr</td>`;
            html += `<td>${row.remaining_customers || 0}</td>`;
            html += `<td>${(row.remaining_amount_birr || 0).toFixed(2)} Birr</td>`;
            html += `<td>$${(row.remaining_amount_dollar || 0).toFixed(2)}</td>`;
            html += `<td>${row.comm_text || 0}</td>`;
            html += `<td>${row.comm_phone || 0}</td>`;
            html += `<td>${row.comm_letter || 0}</td>`;
            html += `<td>${row.comm_difficulty || 0}</td>`;
            html += `<td>${row.comm_service_customers || 0}</td>`;
            html += `<td>${row.comm_sno || 0}</td>`;
            html += `<td>${row.partial_letter_not_delivered || 0}</td>`;
            html += `<td>${row.partial_customers || 0}</td>`;
            html += `<td>${(row.partial_amount_birr || 0).toFixed(2)} Birr</td>`;
            html += `<td>$${(row.partial_amount_dollar || 0).toFixed(2)}</td>`;
            html += `<td>${row.partial_remark || ''}</td>`;
            html += '</tr>';
        });
        
        // Total row
        if (this.state.totals) {
            html += '<tr class="total-row">';
            html += '<td><strong>TOTAL SUM</strong></td>';
            html += '<td></td>';
            html += `<td>${this.state.totals.plan_customers || 0}</td>`;
            html += `<td>${(this.state.totals.plan_amount_birr || 0).toFixed(2)} Birr</td>`;
            html += `<td>$${(this.state.totals.plan_amount_dollar || 0).toFixed(2)}</td>`;
            html += `<td>${this.state.totals.execution_customers || 0}</td>`;
            html += `<td>${(this.state.totals.execution_amount_birr || 0).toFixed(2)} Birr</td>`;
            html += `<td>$${(this.state.totals.execution_amount_dollar || 0).toFixed(2)}</td>`;
            html += `<td>${this.state.totals.other_customers || 0}</td>`;
            html += `<td>${(this.state.totals.other_amount_birr || 0).toFixed(2)} Birr</td>`;
            html += `<td>$${(this.state.totals.other_amount_dollar || 0).toFixed(2)}</td>`;
            html += `<td class="green-cell">${this.state.totals.total_customers || 0}</td>`;
            html += `<td class="green-cell">${(this.state.totals.total_amount_birr || 0).toFixed(2)} Birr</td>`;
            html += `<td class="green-cell">$${(this.state.totals.total_amount_dollar || 0).toFixed(2)}</td>`;
            html += `<td>${this.state.totals.extension_customers || 0}</td>`;
            html += `<td>${(this.state.totals.extension_amount_birr || 0).toFixed(2)} Birr</td>`;
            html += `<td>${this.state.totals.remaining_customers || 0}</td>`;
            html += `<td>${(this.state.totals.remaining_amount_birr || 0).toFixed(2)} Birr</td>`;
            html += `<td>$${(this.state.totals.remaining_amount_dollar || 0).toFixed(2)}</td>`;
            html += `<td>${this.state.totals.comm_text || 0}</td>`;
            html += `<td>${this.state.totals.comm_phone || 0}</td>`;
            html += `<td>${this.state.totals.comm_letter || 0}</td>`;
            html += `<td>${this.state.totals.comm_difficulty || 0}</td>`;
            html += `<td>${this.state.totals.comm_service_customers || 0}</td>`;
            html += `<td>${this.state.totals.comm_sno || 0}</td>`;
            html += `<td>${this.state.totals.partial_letter_not_delivered || 0}</td>`;
            html += `<td>${this.state.totals.partial_customers || 0}</td>`;
            html += `<td>${(this.state.totals.partial_amount_birr || 0).toFixed(2)} Birr</td>`;
            html += `<td>$${(this.state.totals.partial_amount_dollar || 0).toFixed(2)}</td>`;
            html += '<td></td>';
            html += '</tr>';
        }
        
        html += '</tbody></table>';
        return html;
    }
}

SummarizedReportClient.template = "collection_reports.SummarizedReportClient";

registry.category("actions").add("collection_reports.summarized_report", SummarizedReportClient);

