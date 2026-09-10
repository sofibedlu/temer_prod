/** @odoo-module **/

import { Component, useState, onWillStart, useEffect, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class PlanStageReportClient extends Component {
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
        
        // Remove total row before filtering
        const totalRow = filtered.find(row => row.is_total);
        filtered = filtered.filter(row => !row.is_total);
        
        // Filter by search text
        if (this.state.search_text && this.state.search_text.trim()) {
            const searchLower = this.state.search_text.toLowerCase().trim();
            filtered = filtered.filter(row => {
                // Search in item_name (project name)
                const itemName = (row.item_name || '').toLowerCase();
                return itemName.includes(searchLower);
            });
        }
        
        // Recalculate totals from filtered data (excluding total row)
        this.calculateTotalsFromFiltered();
        
        // Add recalculated total row at the end
        if (filtered.length > 0 && this.state.totals) {
            const newTotalRow = {
                sno: '',
                item_name: 'TOTAL',
                is_total: true,
                // PLAN data
                plan_customers: this.state.totals.plan_customers || 0,
                plan_amount_birr: this.state.totals.plan_amount_birr || 0,
                plan_amount_dollar: this.state.totals.plan_amount_dollar || 0,
                // EXPECTED data
                expected_customers: this.state.totals.expected_customers || 0,
                expected_amount_birr: this.state.totals.expected_amount_birr || 0,
                expected_amount_dollar: this.state.totals.expected_amount_dollar || 0,
                // PENALTY data
                penalty_customers: this.state.totals.penalty_customers || 0,
                penalty_amount_birr: this.state.totals.penalty_amount_birr || 0,
                penalty_amount_dollar: this.state.totals.penalty_amount_dollar || 0,
                // TERMINATION data
                termination_customers: this.state.totals.termination_customers || 0,
                termination_amount_birr: this.state.totals.termination_amount_birr || 0,
                termination_amount_dollar: this.state.totals.termination_amount_dollar || 0,
                // ACTUAL data
                actual_expected_customers: this.state.totals.actual_expected_customers || 0,
                actual_expected_amount_birr: this.state.totals.actual_expected_amount_birr || 0,
                actual_expected_amount_dollar: this.state.totals.actual_expected_amount_dollar || 0,
                actual_penalty_customers: this.state.totals.actual_penalty_customers || 0,
                actual_penalty_amount_birr: this.state.totals.actual_penalty_amount_birr || 0,
                actual_penalty_amount_dollar: this.state.totals.actual_penalty_amount_dollar || 0,
                actual_termination_customers: this.state.totals.actual_termination_customers || 0,
                actual_termination_amount_birr: this.state.totals.actual_termination_amount_birr || 0,
                actual_termination_amount_dollar: this.state.totals.actual_termination_amount_dollar || 0,
                // DIFFERENCE data
                diff_plan_customers: this.state.totals.diff_plan_customers || 0,
                diff_plan_amount_birr: this.state.totals.diff_plan_amount_birr || 0,
                diff_plan_amount_dollar: this.state.totals.diff_plan_amount_dollar || 0,
                diff_expected_customers: this.state.totals.diff_expected_customers || 0,
                diff_expected_amount_birr: this.state.totals.diff_expected_amount_birr || 0,
                diff_expected_amount_dollar: this.state.totals.diff_expected_amount_dollar || 0,
                diff_penalty_customers: this.state.totals.diff_penalty_customers || 0,
                diff_penalty_amount_birr: this.state.totals.diff_penalty_amount_birr || 0,
                diff_penalty_amount_dollar: this.state.totals.diff_penalty_amount_dollar || 0,
                diff_termination_customers: this.state.totals.diff_termination_customers || 0,
                diff_termination_amount_birr: this.state.totals.diff_termination_amount_birr || 0,
                diff_termination_amount_dollar: this.state.totals.diff_termination_amount_dollar || 0,
                // TOTAL COLLECTION PLAN
                total_customers: this.state.totals.total_customers || 0,
                total_amount_birr: this.state.totals.total_amount_birr || 0,
                total_amount_dollar: this.state.totals.total_amount_dollar || 0,
            };
            filtered.push(newTotalRow);
        }
        
        this.state.filtered_data = filtered;
    }
    
    calculateTotalsFromFiltered() {
        // Calculate totals from filtered_data only (exclude total row)
        const filtered = (this.state.filtered_data || []).filter(row => !row.is_total);
        if (filtered.length === 0) {
            // If no data rows, use server totals
            return;
        }
        
        this.state.totals = {
            plan_customers: filtered.reduce((sum, row) => sum + (row.plan_customers || 0), 0),
            plan_amount_birr: filtered.reduce((sum, row) => sum + (row.plan_amount_birr || 0), 0),
            plan_amount_dollar: filtered.reduce((sum, row) => sum + (row.plan_amount_dollar || 0), 0),
            expected_customers: filtered.reduce((sum, row) => sum + (row.expected_customers || 0), 0),
            expected_amount_birr: filtered.reduce((sum, row) => sum + (row.expected_amount_birr || 0), 0),
            expected_amount_dollar: filtered.reduce((sum, row) => sum + (row.expected_amount_dollar || 0), 0),
            penalty_customers: filtered.reduce((sum, row) => sum + (row.penalty_customers || 0), 0),
            penalty_amount_birr: filtered.reduce((sum, row) => sum + (row.penalty_amount_birr || 0), 0),
            penalty_amount_dollar: filtered.reduce((sum, row) => sum + (row.penalty_amount_dollar || 0), 0),
            termination_customers: filtered.reduce((sum, row) => sum + (row.termination_customers || 0), 0),
            termination_amount_birr: filtered.reduce((sum, row) => sum + (row.termination_amount_birr || 0), 0),
            termination_amount_dollar: filtered.reduce((sum, row) => sum + (row.termination_amount_dollar || 0), 0),
            // TOTAL COLLECTION PLAN = PLAN + PENALTY + TERMINATION
            total_customers: 0, // Will be calculated below
            total_amount_birr: 0, // Will be calculated below
            total_amount_dollar: 0, // Will be calculated below
            // ACTUAL totals
            actual_expected_customers: filtered.reduce((sum, row) => sum + (row.actual_expected_customers || 0), 0),
            actual_expected_amount_birr: filtered.reduce((sum, row) => sum + (row.actual_expected_amount_birr || 0), 0),
            actual_expected_amount_dollar: filtered.reduce((sum, row) => sum + (row.actual_expected_amount_dollar || 0), 0),
            actual_penalty_customers: filtered.reduce((sum, row) => sum + (row.actual_penalty_customers || 0), 0),
            actual_penalty_amount_birr: filtered.reduce((sum, row) => sum + (row.actual_penalty_amount_birr || 0), 0),
            actual_penalty_amount_dollar: filtered.reduce((sum, row) => sum + (row.actual_penalty_amount_dollar || 0), 0),
            actual_termination_customers: filtered.reduce((sum, row) => sum + (row.actual_termination_customers || 0), 0),
            actual_termination_amount_birr: filtered.reduce((sum, row) => sum + (row.actual_termination_amount_birr || 0), 0),
            actual_termination_amount_dollar: filtered.reduce((sum, row) => sum + (row.actual_termination_amount_dollar || 0), 0),
            actual_total_customers: filtered.reduce((sum, row) => sum + (row.actual_total_customers || 0), 0),
            actual_total_amount_birr: filtered.reduce((sum, row) => sum + (row.actual_total_amount_birr || 0), 0),
            actual_total_amount_dollar: filtered.reduce((sum, row) => sum + (row.actual_total_amount_dollar || 0), 0),
            // DIFFERENCE totals
            diff_plan_customers: filtered.reduce((sum, row) => sum + (row.diff_plan_customers || 0), 0),
            diff_plan_amount_birr: filtered.reduce((sum, row) => sum + (row.diff_plan_amount_birr || 0), 0),
            diff_plan_amount_dollar: filtered.reduce((sum, row) => sum + (row.diff_plan_amount_dollar || 0), 0),
            diff_expected_customers: filtered.reduce((sum, row) => sum + (row.diff_expected_customers || 0), 0),
            diff_expected_amount_birr: filtered.reduce((sum, row) => sum + (row.diff_expected_amount_birr || 0), 0),
            diff_expected_amount_dollar: filtered.reduce((sum, row) => sum + (row.diff_expected_amount_dollar || 0), 0),
            diff_penalty_customers: filtered.reduce((sum, row) => sum + (row.diff_penalty_customers || 0), 0),
            diff_penalty_amount_birr: filtered.reduce((sum, row) => sum + (row.diff_penalty_amount_birr || 0), 0),
            diff_penalty_amount_dollar: filtered.reduce((sum, row) => sum + (row.diff_penalty_amount_dollar || 0), 0),
            diff_termination_customers: filtered.reduce((sum, row) => sum + (row.diff_termination_customers || 0), 0),
            diff_termination_amount_birr: filtered.reduce((sum, row) => sum + (row.diff_termination_amount_birr || 0), 0),
            diff_termination_amount_dollar: filtered.reduce((sum, row) => sum + (row.diff_termination_amount_dollar || 0), 0),
            diff_total_customers: filtered.reduce((sum, row) => sum + (row.diff_total_customers || 0), 0),
            diff_total_amount_birr: filtered.reduce((sum, row) => sum + (row.diff_total_amount_birr || 0), 0),
            diff_total_amount_dollar: filtered.reduce((sum, row) => sum + (row.diff_total_amount_dollar || 0), 0),
        };
        
        // Calculate TOTAL COLLECTION PLAN = PLAN + PENALTY + TERMINATION
        this.state.totals.total_customers = this.state.totals.plan_customers + this.state.totals.penalty_customers + this.state.totals.termination_customers;
        this.state.totals.total_amount_birr = this.state.totals.plan_amount_birr + this.state.totals.penalty_amount_birr + this.state.totals.termination_amount_birr;
        this.state.totals.total_amount_dollar = this.state.totals.plan_amount_dollar + this.state.totals.penalty_amount_dollar + this.state.totals.termination_amount_dollar;
    }
    
    onSearchChange() {
        this.filterData();
    }

    async loadData() {
        if (!this.isMounted) return;
        this.state.loading = true;
        try {
            const response = await fetch("/collection_reports/api/plan_stage_report", {
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
        if (!this.state.filtered_data || this.state.filtered_data.length === 0) {
            this.notification.add("No data to export", { type: "warning" });
            return;
        }

        try {
            // Generate CSV from filtered data
            let csv = this.generateCSV();
            
            // Create download link
            const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
            const link = document.createElement('a');
            const url = URL.createObjectURL(blob);
            link.setAttribute('href', url);
            link.setAttribute('download', `Plan_Based_on_Collection_Stage_${this.state.date_from || 'All'}_to_${this.state.date_to || 'All'}.csv`);
            link.style.visibility = 'hidden';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            this.notification.add("Excel file downloaded successfully", { type: "success" });
        } catch (error) {
            console.error("Error exporting to Excel:", error);
            this.notification.add("Error exporting to Excel: " + error.message, { type: "danger" });
        }
    }
    
    generateCSV() {
        // Get filtered data (excluding total row for now, we'll add it at the end)
        const dataRows = (this.state.filtered_data || []).filter(row => !row.is_total);
        const totalRow = (this.state.filtered_data || []).find(row => row.is_total);
        
        let csv = [];
        
        // Header row 1
        csv.push('S.N O,PROJECT NAME,"PLAN","","","","","","","EXPECTED","","","ACTUAL","","","","","","DIFFERENCE","","","","","","TOTAL COLLECTION PLAN","",""');
        
        // Header row 2
        csv.push(',,"PLAN (Normal)","","","PENALTY","","","TERMINATION","","","EXPECTED (from sold leads)","","","PLAN (Normal)","","","PENALTY","","","TERMINATION","","","PLAN (Normal)","","","EXPECTED","","","PENALTY","","","TERMINATION","","","","",""');
        
        // Header row 3
        csv.push(',,"NO OF CUSTOMERS","AMOUNT IN BIRR","AMOUNT IN DOLLAR","NO OF CUSTOMERS","AMOUNT IN BIRR","AMOUNT IN DOLLAR","NO OF CUSTOMERS","AMOUNT IN BIRR","AMOUNT IN DOLLAR","NO OF CUSTOMERS","AMOUNT IN BIRR","AMOUNT IN DOLLAR","NO OF CUSTOMERS","AMOUNT IN BIRR","AMOUNT IN DOLLAR","NO OF CUSTOMERS","AMOUNT IN BIRR","AMOUNT IN DOLLAR","NO OF CUSTOMERS","AMOUNT IN BIRR","AMOUNT IN DOLLAR","NO OF CUSTOMERS","AMOUNT IN BIRR","AMOUNT IN DOLLAR","NO OF CUSTOMERS","AMOUNT IN BIRR","AMOUNT IN DOLLAR","NO OF CUSTOMERS","AMOUNT IN BIRR","AMOUNT IN DOLLAR","NO OF CUSTOMERS","AMOUNT IN BIRR","AMOUNT IN DOLLAR","NO OF CUSTOMERS","AMOUNT IN BIRR","AMOUNT IN DOLLAR"');
        
        // Data rows
        dataRows.forEach(row => {
            const rowData = [
                row.sno || '',
                row.item_name || '',
                // PLAN
                row.plan_customers || 0,
                (row.plan_amount_birr || 0).toFixed(2),
                (row.plan_amount_dollar || 0).toFixed(2),
                row.penalty_customers || 0,
                (row.penalty_amount_birr || 0).toFixed(2),
                (row.penalty_amount_dollar || 0).toFixed(2),
                row.termination_customers || 0,
                (row.termination_amount_birr || 0).toFixed(2),
                (row.termination_amount_dollar || 0).toFixed(2),
                // EXPECTED
                row.expected_customers || 0,
                (row.expected_amount_birr || 0).toFixed(2),
                (row.expected_amount_dollar || 0).toFixed(2),
                // ACTUAL
                row.actual_expected_customers || 0,
                (row.actual_expected_amount_birr || 0).toFixed(2),
                (row.actual_expected_amount_dollar || 0).toFixed(2),
                row.actual_penalty_customers || 0,
                (row.actual_penalty_amount_birr || 0).toFixed(2),
                (row.actual_penalty_amount_dollar || 0).toFixed(2),
                row.actual_termination_customers || 0,
                (row.actual_termination_amount_birr || 0).toFixed(2),
                (row.actual_termination_amount_dollar || 0).toFixed(2),
                // DIFFERENCE
                row.diff_plan_customers || 0,
                (row.diff_plan_amount_birr || 0).toFixed(2),
                (row.diff_plan_amount_dollar || 0).toFixed(2),
                row.diff_expected_customers || 0,
                (row.diff_expected_amount_birr || 0).toFixed(2),
                (row.diff_expected_amount_dollar || 0).toFixed(2),
                row.diff_penalty_customers || 0,
                (row.diff_penalty_amount_birr || 0).toFixed(2),
                (row.diff_penalty_amount_dollar || 0).toFixed(2),
                row.diff_termination_customers || 0,
                (row.diff_termination_amount_birr || 0).toFixed(2),
                (row.diff_termination_amount_dollar || 0).toFixed(2),
                // TOTAL COLLECTION PLAN
                row.total_customers || 0,
                (row.total_amount_birr || 0).toFixed(2),
                (row.total_amount_dollar || 0).toFixed(2),
            ];
            csv.push(rowData.map(cell => `"${cell}"`).join(','));
        });
        
        // Add total row if it exists
        if (totalRow) {
            const totalData = [
                '',
                'TOTAL',
                // PLAN
                totalRow.plan_customers || 0,
                (totalRow.plan_amount_birr || 0).toFixed(2),
                (totalRow.plan_amount_dollar || 0).toFixed(2),
                totalRow.penalty_customers || 0,
                (totalRow.penalty_amount_birr || 0).toFixed(2),
                (totalRow.penalty_amount_dollar || 0).toFixed(2),
                totalRow.termination_customers || 0,
                (totalRow.termination_amount_birr || 0).toFixed(2),
                (totalRow.termination_amount_dollar || 0).toFixed(2),
                // EXPECTED
                totalRow.expected_customers || 0,
                (totalRow.expected_amount_birr || 0).toFixed(2),
                (totalRow.expected_amount_dollar || 0).toFixed(2),
                // ACTUAL
                totalRow.actual_expected_customers || 0,
                (totalRow.actual_expected_amount_birr || 0).toFixed(2),
                (totalRow.actual_expected_amount_dollar || 0).toFixed(2),
                totalRow.actual_penalty_customers || 0,
                (totalRow.actual_penalty_amount_birr || 0).toFixed(2),
                (totalRow.actual_penalty_amount_dollar || 0).toFixed(2),
                totalRow.actual_termination_customers || 0,
                (totalRow.actual_termination_amount_birr || 0).toFixed(2),
                (totalRow.actual_termination_amount_dollar || 0).toFixed(2),
                // DIFFERENCE
                totalRow.diff_plan_customers || 0,
                (totalRow.diff_plan_amount_birr || 0).toFixed(2),
                (totalRow.diff_plan_amount_dollar || 0).toFixed(2),
                totalRow.diff_expected_customers || 0,
                (totalRow.diff_expected_amount_birr || 0).toFixed(2),
                (totalRow.diff_expected_amount_dollar || 0).toFixed(2),
                totalRow.diff_penalty_customers || 0,
                (totalRow.diff_penalty_amount_birr || 0).toFixed(2),
                (totalRow.diff_penalty_amount_dollar || 0).toFixed(2),
                totalRow.diff_termination_customers || 0,
                (totalRow.diff_termination_amount_birr || 0).toFixed(2),
                (totalRow.diff_termination_amount_dollar || 0).toFixed(2),
                // TOTAL COLLECTION PLAN
                totalRow.total_customers || 0,
                (totalRow.total_amount_birr || 0).toFixed(2),
                (totalRow.total_amount_dollar || 0).toFixed(2),
            ];
            csv.push(totalData.map(cell => `"${cell}"`).join(','));
        }
        
        return csv.join('\n');
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
                    <title>Plan Based on Collection Stage - ${this.state.date_from || 'All'} to ${this.state.date_to || 'All'}</title>
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
                        <h1>Plan Based on Collection Stage</h1>
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
        
        // Multi-level header matching the table structure
        html += '<thead>';
        html += '<tr><th rowspan="3">S.N O</th><th rowspan="3">PROJECT NAME</th>';
        html += '<th colspan="9">PLAN</th>';
        html += '<th colspan="3">EXPECTED</th>';
        html += '<th colspan="9">ACTUAL</th>';
        html += '<th colspan="12">DIFFERENCE</th>';
        html += '<th colspan="3">TOTAL COLLECTION PLAN</th></tr>';
        
        html += '<tr>';
        html += '<th colspan="3">PLAN (Normal)</th>';
        html += '<th colspan="3">PENALTY</th>';
        html += '<th colspan="3">TERMINATION</th>';
        html += '<th colspan="3" rowspan="2">EXPECTED<br/>(from sold leads)</th>';
        html += '<th colspan="3">PLAN (Normal)</th>';
        html += '<th colspan="3">PENALTY</th>';
        html += '<th colspan="3">TERMINATION</th>';
        html += '<th colspan="3">PLAN (Normal)</th>';
        html += '<th colspan="3">EXPECTED</th>';
        html += '<th colspan="3">PENALTY</th>';
        html += '<th colspan="3">TERMINATION</th>';
        html += '<th rowspan="2">NO OF<br/>CUSTOMERS</th>';
        html += '<th rowspan="2">AMOUNT<br/>IN BIRR</th>';
        html += '<th rowspan="2">AMOUNT<br/>IN DOLLAR</th>';
        html += '</tr>';
        
        html += '<tr>';
        html += '<th>NO OF<br/>CUSTOMERS</th><th>AMOUNT<br/>IN BIRR</th><th>AMOUNT<br/>IN DOLLAR</th>';
        html += '<th>NO OF<br/>CUSTOMERS</th><th>AMOUNT<br/>IN BIRR</th><th>AMOUNT<br/>IN DOLLAR</th>';
        html += '<th>NO OF<br/>CUSTOMERS</th><th>AMOUNT<br/>IN BIRR</th><th>AMOUNT<br/>IN DOLLAR</th>';
        html += '<th>NO OF<br/>CUSTOMERS</th><th>AMOUNT<br/>IN BIRR</th><th>AMOUNT<br/>IN DOLLAR</th>';
        html += '<th>NO OF<br/>CUSTOMERS</th><th>AMOUNT<br/>IN BIRR</th><th>AMOUNT<br/>IN DOLLAR</th>';
        html += '<th>NO OF<br/>CUSTOMERS</th><th>AMOUNT<br/>IN BIRR</th><th>AMOUNT<br/>IN DOLLAR</th>';
        html += '<th>NO OF<br/>CUSTOMERS</th><th>AMOUNT<br/>IN BIRR</th><th>AMOUNT<br/>IN DOLLAR</th>';
        html += '<th>NO OF<br/>CUSTOMERS</th><th>AMOUNT<br/>IN BIRR</th><th>AMOUNT<br/>IN DOLLAR</th>';
        html += '<th>NO OF<br/>CUSTOMERS</th><th>AMOUNT<br/>IN BIRR</th><th>AMOUNT<br/>IN DOLLAR</th>';
        html += '<th>NO OF<br/>CUSTOMERS</th><th>AMOUNT<br/>IN BIRR</th><th>AMOUNT<br/>IN DOLLAR</th>';
        html += '<th>NO OF<br/>CUSTOMERS</th><th>AMOUNT<br/>IN BIRR</th><th>AMOUNT<br/>IN DOLLAR</th>';
        html += '</tr></thead><tbody>';
        
        // Data rows
        this.state.filtered_data.forEach(row => {
            const rowClass = row.is_total ? 'total-row' : '';
            html += `<tr class="${rowClass}">`;
            html += `<td>${row.sno || ''}</td>`;
            html += `<td>${row.item_name || row.project_name || ''}</td>`;
            // PLAN columns
            html += `<td>${row.plan_customers || 0}</td>`;
            html += `<td>${(row.plan_amount_birr || 0).toFixed(2)} Birr</td>`;
            html += `<td>$${(row.plan_amount_dollar || 0).toFixed(2)}</td>`;
            html += `<td>${row.penalty_customers || 0}</td>`;
            html += `<td>${(row.penalty_amount_birr || 0).toFixed(2)} Birr</td>`;
            html += `<td>$${(row.penalty_amount_dollar || 0).toFixed(2)}</td>`;
            html += `<td>${row.termination_customers || 0}</td>`;
            html += `<td>${(row.termination_amount_birr || 0).toFixed(2)} Birr</td>`;
            html += `<td>$${(row.termination_amount_dollar || 0).toFixed(2)}</td>`;
            // EXPECTED columns
            html += `<td>${row.expected_customers || 0}</td>`;
            html += `<td>${(row.expected_amount_birr || 0).toFixed(2)} Birr</td>`;
            html += `<td>$${(row.expected_amount_dollar || 0).toFixed(2)}</td>`;
            // ACTUAL columns
            html += `<td>${row.actual_expected_customers || 0}</td>`;
            html += `<td>${(row.actual_expected_amount_birr || 0).toFixed(2)} Birr</td>`;
            html += `<td>$${(row.actual_expected_amount_dollar || 0).toFixed(2)}</td>`;
            html += `<td>${row.actual_penalty_customers || 0}</td>`;
            html += `<td>${(row.actual_penalty_amount_birr || 0).toFixed(2)} Birr</td>`;
            html += `<td>$${(row.actual_penalty_amount_dollar || 0).toFixed(2)}</td>`;
            html += `<td>${row.actual_termination_customers || 0}</td>`;
            html += `<td>${(row.actual_termination_amount_birr || 0).toFixed(2)} Birr</td>`;
            html += `<td>$${(row.actual_termination_amount_dollar || 0).toFixed(2)}</td>`;
            // DIFFERENCE columns
            html += `<td>${row.diff_plan_customers || 0}</td>`;
            html += `<td>${(row.diff_plan_amount_birr || 0).toFixed(2)} Birr</td>`;
            html += `<td>$${(row.diff_plan_amount_dollar || 0).toFixed(2)}</td>`;
            html += `<td>${row.diff_expected_customers || 0}</td>`;
            html += `<td>${(row.diff_expected_amount_birr || 0).toFixed(2)} Birr</td>`;
            html += `<td>$${(row.diff_expected_amount_dollar || 0).toFixed(2)}</td>`;
            html += `<td>${row.diff_penalty_customers || 0}</td>`;
            html += `<td>${(row.diff_penalty_amount_birr || 0).toFixed(2)} Birr</td>`;
            html += `<td>$${(row.diff_penalty_amount_dollar || 0).toFixed(2)}</td>`;
            html += `<td>${row.diff_termination_customers || 0}</td>`;
            html += `<td>${(row.diff_termination_amount_birr || 0).toFixed(2)} Birr</td>`;
            html += `<td>$${(row.diff_termination_amount_dollar || 0).toFixed(2)}</td>`;
            // TOTAL COLLECTION PLAN
            html += `<td>${row.total_customers || 0}</td>`;
            html += `<td>${(row.total_amount_birr || 0).toFixed(2)} Birr</td>`;
            html += `<td>$${(row.total_amount_dollar || 0).toFixed(2)}</td>`;
            html += '</tr>';
        });
        
        html += '</tbody></table>';
        return html;
    }
}

PlanStageReportClient.template = "collection_reports.PlanStageReportClient";

registry.category("actions").add("collection_reports.plan_stage_report", PlanStageReportClient);

