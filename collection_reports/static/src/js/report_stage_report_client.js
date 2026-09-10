/** @odoo-module **/

import { Component, useState, onWillStart, useEffect, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class ReportStageReportClient extends Component {
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
        if (this.state.search_text && this.state.search_text.trim()) {
            const searchLower = this.state.search_text.toLowerCase().trim();
            filtered = filtered.filter(row => {
                // Search in project_name
                const projectName = (row.project_name || '').toLowerCase();
                // Always show total row
                if (row.is_total) {
                    return true;
                }
                return projectName.includes(searchLower);
            });
        } else {
            // If no search text, show all data (including total)
            filtered = [...this.state.data];
        }
        
        this.state.filtered_data = filtered;
    }
    
    onSearchChange() {
        this.filterData();
    }

    async loadData() {
        if (!this.isMounted) return;
        this.state.loading = true;
        try {
            const response = await fetch("/collection_reports/api/report_stage_report", {
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
            
            let data = result;
            if (result && result.result) {
                data = result.result;
            }
            
            if (data && data.success) {
                if (this.isMounted) {
                    this.state.data = data.data || [];
                    this.state.totals = data.totals || {};
                    // Apply filters after loading data
                    this.filterData();
                    console.log("Data loaded:", this.state.data.length, "rows, filtered:", this.state.filtered_data.length, "rows");
                }
            } else {
                if (this.isMounted) {
                    console.error("Error loading data:", data?.error || result?.error || "Unknown error");
                    this.state.data = [];
                    this.state.filtered_data = [];
                    this.state.totals = {};
                }
            }
        } catch (error) {
            if (this.isMounted) {
                console.error("Error loading data:", error);
                this.state.data = [];
                this.state.filtered_data = [];
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
            reportTypeInput.value = 'report_stage_report';
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
                    <title>Report Based on Collection Stage - ${this.state.date_from || 'All'} to ${this.state.date_to || 'All'}</title>
                    <style>
                        @page {
                            size: A4 landscape;
                            margin: 10mm;
                        }
                        body {
                            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                            margin: 0;
                            padding: 15px;
                            background: #fff;
                            color: #333;
                            font-size: 9px;
                        }
                        .report-header {
                            text-align: center;
                            margin-bottom: 20px;
                            padding-bottom: 10px;
                            border-bottom: 2px solid #2c3e50;
                        }
                        .report-header h1 {
                            color: #2c3e50;
                            margin: 0 0 5px 0;
                            font-size: 18px;
                        }
                        .report-meta {
                            color: #6c757d;
                            font-size: 11px;
                        }
                        table {
                            width: 100%;
                            border-collapse: collapse;
                            margin-top: 10px;
                            font-size: 8px;
                        }
                        th, td {
                            border: 1px solid #ddd;
                            padding: 6px 4px;
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
                            body { margin: 0; padding: 10px; }
                            .no-print { display: none; }
                        }
                    </style>
                </head>
                <body>
                    <div class="report-header">
                        <h1>Report Based on Collection Stage</h1>
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
        
        // Multi-level header
        html += '<thead>';
        html += '<tr><th rowspan="2">S.NO</th><th rowspan="2">PROJECT NAME</th>';
        html += '<th colspan="2">EXPECTED</th>';
        html += '<th colspan="3">PENALITY</th>';
        html += '<th colspan="2">TERMINATION</th>';
        html += '<th colspan="3">OTHER COLLECTION</th>';
        html += '<th colspan="3" class="green-header">TOTAL COLLECTION REPORT</th></tr>';
        
        html += '<tr>';
        html += '<th>NO OF CUSTOMERS</th><th>AMOUNT IN BIRR</th>';
        html += '<th>NO OF CUSTOMERS</th><th>AMOUNT IN BIRR</th><th>AMOUNT IN DOLLAR</th>';
        html += '<th>NO OF CUSTOMERS</th><th>AMOUNT IN BIRR</th>';
        html += '<th>NO OF CUSTOMERS</th><th>AMOUNT IN BIRR</th><th>AMOUNT IN DOLLAR</th>';
        html += '<th class="green-header">NO OF CUSTOMERS</th><th class="green-header">AMOUNT IN BIRR</th><th class="green-header">AMOUNT IN DOLLAR</th>';
        html += '</tr></thead><tbody>';
        
        // Data rows
        this.state.filtered_data.forEach(row => {
            const rowClass = row.is_total ? 'total-row' : '';
            html += `<tr class="${rowClass}">`;
            html += `<td>${row.sno || ''}</td>`;
            html += `<td>${row.project_name || ''}</td>`;
            html += `<td>${row.actual_expected_customers || 0}</td>`;
            html += `<td>${(row.actual_expected_amount_birr || 0).toFixed(2)} Birr</td>`;
            html += `<td>${row.actual_penalty_customers || 0}</td>`;
            html += `<td>${(row.actual_penalty_amount_birr || 0).toFixed(2)} Birr</td>`;
            html += `<td>$${(row.actual_penalty_amount_dollar || 0).toFixed(2)}</td>`;
            html += `<td>${row.actual_termination_customers || 0}</td>`;
            html += `<td>${(row.actual_termination_amount_birr || 0).toFixed(2)} Birr</td>`;
            html += `<td>${row.other_customers || 0}</td>`;
            html += `<td>${(row.other_amount_birr || 0).toFixed(2)} Birr</td>`;
            html += `<td>$${(row.other_amount_dollar || 0).toFixed(2)}</td>`;
            html += `<td class="green-cell">${row.actual_total_customers || 0}</td>`;
            html += `<td class="green-cell">${(row.actual_total_amount_birr || 0).toFixed(2)} Birr</td>`;
            html += `<td class="green-cell">$${(row.actual_total_amount_dollar || 0).toFixed(2)}</td>`;
            html += '</tr>';
        });
        
        html += '</tbody></table>';
        return html;
    }
}

ReportStageReportClient.template = "collection_reports.ReportStageReportClient";

registry.category("actions").add("collection_reports.report_stage_report", ReportStageReportClient);

