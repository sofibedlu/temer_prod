/** @odoo-module **/

import { Component, useState, onWillStart, useEffect, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class CollectionStageReportClient extends Component {
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
        
        useEffect(
            (search_text) => {
                if (this.isMounted) {
                    this.filterData();
                }
            },
            () => [this.state.search_text, this.state.data]
        );
    }
    
    filterData() {
        let filtered = [...this.state.data];
        
        // Filter by search text
        if (this.state.search_text && this.state.search_text.trim()) {
            const searchLower = this.state.search_text.toLowerCase().trim();
            filtered = filtered.filter(row => {
                const description = (row.description || '').toLowerCase();
                return description.includes(searchLower);
            });
        } else {
            filtered = [...this.state.data];
        }
        
        this.state.filtered_data = filtered;
    }
    
    onSearchChange() {
        this.filterData();
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

    async loadData() {
        if (!this.isMounted) return;
        this.state.loading = true;
        try {
            // Use Odoo's JSON-RPC format for JSON requests
            // Use collection_reports endpoint
            const response = await fetch("/collection_reports/api/collection_stage", {
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
            console.log("API Response (raw):", result);
            
            if (!this.isMounted) return;
            
            // Handle Odoo JSON-RPC response format
            let data = result;
            if (result && result.result) {
                data = result.result;
            }
            
            console.log("API Response (processed):", data);
            
            // ALWAYS create the 4 rows plus TOTAL, even if API fails or returns no data
            if (this.isMounted) {
                const transformedData = [];
                
                // Initialize all totals to 0
                let totalPlanExpectedCustomers = 0;
                let totalPlanExpectedAmountBirr = 0;
                let totalPlanExpectedAmountDollar = 0;
                let totalPlanPenaltyCustomers = 0;
                let totalPlanPenaltyAmountBirr = 0;
                let totalPlanPenaltyAmountDollar = 0;
                let totalPlanTerminationCustomers = 0;
                let totalPlanTerminationAmountBirr = 0;
                let totalPlanTerminationAmountDollar = 0;
                
                let totalReportExpectedCustomers = 0;
                let totalReportExpectedAmountBirr = 0;
                let totalReportExpectedAmountDollar = 0;
                let totalReportPenaltyCustomers = 0;
                let totalReportPenaltyAmountBirr = 0;
                let totalReportPenaltyAmountDollar = 0;
                let totalReportTerminationCustomers = 0;
                let totalReportTerminationAmountBirr = 0;
                let totalReportTerminationAmountDollar = 0;
                let totalReportOtherCustomers = 0;
                let totalReportOtherAmountBirr = 0;
                let totalReportOtherAmountDollar = 0;
                let totalReportTotalCustomers = 0;
                let totalReportTotalAmountBirr = 0;
                let totalReportTotalAmountDollar = 0;
                
                // Only aggregate if API returned successful data
                if (data && data.success) {
                    const apiData = data.data || [];
                    console.log("API Data (first row sample):", apiData.length > 0 ? apiData[0] : "No data");
                    console.log("API Data length:", apiData.length);
                    console.log("Sample site data keys:", apiData.length > 0 ? Object.keys(apiData[0]) : "No data");
                    
                    // Aggregate from all sites (skip total row)
                    apiData.forEach((siteData, index) => {
                        if (!siteData.is_total) {
                            console.log(`Site ${index + 1} (${siteData.project_name}):`, {
                                plan_customers: siteData.plan_customers,
                                plan_amount_birr: siteData.plan_amount_birr,
                                penalty_customers: siteData.penalty_customers,
                                termination_customers: siteData.termination_customers
                            });
                            
                            // PLAN data (from collection.plan.stage) - these come from the plan model
                            // For "PAYMENT EXPECTED STAGE COLLECTION", use plan_customers (normal plan)
                            totalPlanExpectedCustomers += Number(siteData.plan_customers) || 0;
                            totalPlanExpectedAmountBirr += Number(siteData.plan_amount_birr) || 0;
                            totalPlanExpectedAmountDollar += Number(siteData.plan_amount_dollar) || 0;
                            
                            // PLAN penalty data (from collection.plan.stage)
                            totalPlanPenaltyCustomers += Number(siteData.penalty_customers) || 0;
                            totalPlanPenaltyAmountBirr += Number(siteData.penalty_amount_birr) || 0;
                            totalPlanPenaltyAmountDollar += Number(siteData.penalty_amount_dollar) || 0;
                            
                            // PLAN termination data (from collection.plan.stage)
                            totalPlanTerminationCustomers += Number(siteData.termination_customers) || 0;
                            totalPlanTerminationAmountBirr += Number(siteData.termination_amount_birr) || 0;
                            totalPlanTerminationAmountDollar += Number(siteData.termination_amount_dollar) || 0;
                            
                            // REPORT data (actual collections) - these come from actual collection orders
                            totalReportExpectedCustomers += Number(siteData.actual_expected_customers) || 0;
                            totalReportExpectedAmountBirr += Number(siteData.actual_expected_amount_birr) || 0;
                            totalReportExpectedAmountDollar += Number(siteData.actual_expected_amount_dollar) || 0;
                            
                            totalReportPenaltyCustomers += Number(siteData.actual_penalty_customers) || 0;
                            totalReportPenaltyAmountBirr += Number(siteData.actual_penalty_amount_birr) || 0;
                            totalReportPenaltyAmountDollar += Number(siteData.actual_penalty_amount_dollar) || 0;
                            
                            totalReportTerminationCustomers += Number(siteData.actual_termination_customers) || 0;
                            totalReportTerminationAmountBirr += Number(siteData.actual_termination_amount_birr) || 0;
                            totalReportTerminationAmountDollar += Number(siteData.actual_termination_amount_dollar) || 0;
                            
                            totalReportOtherCustomers += Number(siteData.other_customers) || 0;
                            totalReportOtherAmountBirr += Number(siteData.other_amount_birr) || 0;
                            totalReportOtherAmountDollar += Number(siteData.other_amount_dollar) || 0;
                            
                            totalReportTotalCustomers += Number(siteData.actual_total_customers) || 0;
                            totalReportTotalAmountBirr += Number(siteData.actual_total_amount_birr) || 0;
                            totalReportTotalAmountDollar += Number(siteData.actual_total_amount_dollar) || 0;
                        }
                    });
                    
                    console.log("Aggregated PLAN totals:", {
                        totalPlanExpectedCustomers,
                        totalPlanExpectedAmountBirr,
                        totalPlanExpectedAmountDollar,
                        totalPlanPenaltyCustomers,
                        totalPlanPenaltyAmountBirr,
                        totalPlanPenaltyAmountDollar,
                        totalPlanTerminationCustomers,
                        totalPlanTerminationAmountBirr,
                        totalPlanTerminationAmountDollar
                    });
                    console.log("Aggregated REPORT totals:", {
                        totalReportExpectedCustomers,
                        totalReportExpectedAmountBirr,
                        totalReportExpectedAmountDollar,
                        totalReportPenaltyCustomers,
                        totalReportPenaltyAmountBirr,
                        totalReportPenaltyAmountDollar,
                        totalReportTerminationCustomers,
                        totalReportTerminationAmountBirr,
                        totalReportTerminationAmountDollar
                    });
                }
                
                // ALWAYS create these 4 rows plus TOTAL, regardless of data availability
                // Row 1: Payment Expected Stage Collection
                transformedData.push({
                    sno: 1,
                    description: 'PAYMENT EXPECTED STAGE COLLECTION',
                    payment_round_number: '',
                    plan_customers: totalPlanExpectedCustomers,
                    plan_amount_birr: totalPlanExpectedAmountBirr,
                    plan_amount_dollar: totalPlanExpectedAmountDollar,
                    report_customers: totalReportExpectedCustomers,
                    report_amount_birr: totalReportExpectedAmountBirr,
                    report_amount_dollar: totalReportExpectedAmountDollar,
                    remark: ''
                });
                
                // Row 2: Penality Stage Collection
                transformedData.push({
                    sno: 2,
                    description: 'PENALITY STAGE COLLECTION',
                    payment_round_number: '',
                    plan_customers: totalPlanPenaltyCustomers,
                    plan_amount_birr: totalPlanPenaltyAmountBirr,
                    plan_amount_dollar: totalPlanPenaltyAmountDollar,
                    report_customers: totalReportPenaltyCustomers,
                    report_amount_birr: totalReportPenaltyAmountBirr,
                    report_amount_dollar: totalReportPenaltyAmountDollar,
                    remark: ''
                });
                
                // Row 3: Termination Stage
                transformedData.push({
                    sno: 3,
                    description: 'TERMINATION STAGE',
                    payment_round_number: '',
                    plan_customers: totalPlanTerminationCustomers,
                    plan_amount_birr: totalPlanTerminationAmountBirr,
                    plan_amount_dollar: totalPlanTerminationAmountDollar,
                    report_customers: totalReportTerminationCustomers,
                    report_amount_birr: totalReportTerminationAmountBirr,
                    report_amount_dollar: totalReportTerminationAmountDollar,
                    remark: ''
                });
                
                // Row 4: Other Collection
                transformedData.push({
                    sno: 4,
                    description: 'OTHER COLLECTION',
                    payment_round_number: '',
                    plan_customers: 0, // Other collection is not in plan (always 0)
                    plan_amount_birr: 0,
                    plan_amount_dollar: 0,
                    report_customers: totalReportOtherCustomers,
                    report_amount_birr: totalReportOtherAmountBirr,
                    report_amount_dollar: totalReportOtherAmountDollar,
                    remark: ''
                });
                
                // Row 5: Total Collection
                const totalPlanCustomers = totalPlanExpectedCustomers + totalPlanPenaltyCustomers + totalPlanTerminationCustomers;
                const totalPlanAmountBirr = totalPlanExpectedAmountBirr + totalPlanPenaltyAmountBirr + totalPlanTerminationAmountBirr;
                const totalPlanAmountDollar = totalPlanExpectedAmountDollar + totalPlanPenaltyAmountDollar + totalPlanTerminationAmountDollar;
                
                transformedData.push({
                    sno: '',
                    description: 'TOTAL COLLECTION',
                    payment_round_number: '',
                    plan_customers: totalPlanCustomers,
                    plan_amount_birr: totalPlanAmountBirr,
                    plan_amount_dollar: totalPlanAmountDollar,
                    report_customers: totalReportTotalCustomers,
                    report_amount_birr: totalReportTotalAmountBirr,
                    report_amount_dollar: totalReportTotalAmountDollar,
                    remark: '',
                    is_total: true
                });
                
                console.log("Final transformed data:", transformedData);
                this.state.data = transformedData;
                this.state.totals = {
                    total_plan_customers: totalPlanCustomers,
                    total_plan_amount_birr: totalPlanAmountBirr,
                    total_plan_amount_dollar: totalPlanAmountDollar,
                    total_report_customers: totalReportTotalCustomers,
                    total_report_amount_birr: totalReportTotalAmountBirr,
                    total_report_amount_dollar: totalReportTotalAmountDollar,
                };
                console.log("Final totals:", this.state.totals);
                this.filterData();
                console.log("After filterData, filtered_data length:", this.state.filtered_data.length);
            }
        } catch (error) {
            if (this.isMounted) {
                console.error("Error loading data:", error);
                // Even on error, create the empty rows structure
                const transformedData = [
                    {
                        sno: 1,
                        description: 'PAYMENT EXPECTED STAGE COLLECTION',
                        payment_round_number: '',
                        plan_customers: 0,
                        plan_amount_birr: 0,
                        plan_amount_dollar: 0,
                        report_customers: 0,
                        report_amount_birr: 0,
                        report_amount_dollar: 0,
                        remark: ''
                    },
                    {
                        sno: 2,
                        description: 'PENALITY STAGE COLLECTION',
                        payment_round_number: '',
                        plan_customers: 0,
                        plan_amount_birr: 0,
                        plan_amount_dollar: 0,
                        report_customers: 0,
                        report_amount_birr: 0,
                        report_amount_dollar: 0,
                        remark: ''
                    },
                    {
                        sno: 3,
                        description: 'TERMINATION STAGE',
                        payment_round_number: '',
                        plan_customers: 0,
                        plan_amount_birr: 0,
                        plan_amount_dollar: 0,
                        report_customers: 0,
                        report_amount_birr: 0,
                        report_amount_dollar: 0,
                        remark: ''
                    },
                    {
                        sno: 4,
                        description: 'OTHER COLLECTION',
                        payment_round_number: '',
                        plan_customers: 0,
                        plan_amount_birr: 0,
                        plan_amount_dollar: 0,
                        report_customers: 0,
                        report_amount_birr: 0,
                        report_amount_dollar: 0,
                        remark: ''
                    },
                    {
                        sno: '',
                        description: 'TOTAL COLLECTION',
                        payment_round_number: '',
                        plan_customers: 0,
                        plan_amount_birr: 0,
                        plan_amount_dollar: 0,
                        report_customers: 0,
                        report_amount_birr: 0,
                        report_amount_dollar: 0,
                        remark: '',
                        is_total: true
                    }
                ];
                this.state.data = transformedData;
                this.state.filtered_data = transformedData;
                this.state.totals = {
                    total_plan_customers: 0,
                    total_plan_amount_birr: 0,
                    total_plan_amount_dollar: 0,
                    total_report_customers: 0,
                    total_report_amount_birr: 0,
                    total_report_amount_dollar: 0,
                };
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
            reportTypeInput.value = 'collection_stage';
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
            const printWindow = window.open('', '_blank');
            const printContent = this.generatePrintContent();
            
            printWindow.document.write(`
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Collection Report Based on Collection Stage - ${this.state.date_from || 'All'} to ${this.state.date_to || 'All'}</title>
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
                            font-size: 10px;
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
                            font-size: 9px;
                        }
                        th, td {
                            border: 1px solid #ddd;
                            padding: 6px 4px;
                            text-align: left;
                        }
                        th {
                            background-color: #f2f2f2;
                            font-weight: bold;
                            text-align: center;
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
                        <h1>Collection Report Based on Collection Stage</h1>
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
        
        // Header
        html += '<thead><tr>';
        html += '<th>S.NO</th>';
        html += '<th>DESCRIPTION</th>';
        html += '<th>PAYMENT ROUND NUMBER</th>';
        html += '<th colspan="3">PLAN</th>';
        html += '<th colspan="3">REPORT</th>';
        html += '<th>REMARK</th>';
        html += '</tr>';
        html += '<tr>';
        html += '<th></th>';
        html += '<th></th>';
        html += '<th></th>';
        html += '<th>NUMBER OF CUSTOMER</th>';
        html += '<th>AMOUNT IN BIRR</th>';
        html += '<th>AMOUNT IN DOLLAR</th>';
        html += '<th>NUMBER OF CUSTOMER</th>';
        html += '<th>AMOUNT IN BIRR</th>';
        html += '<th>AMOUNT IN DOLLAR</th>';
        html += '<th></th>';
        html += '</tr></thead><tbody>';
        
        // Data rows
        this.state.filtered_data.forEach(row => {
            const rowClass = row.is_total ? 'total-row' : '';
            html += `<tr class="${rowClass}">`;
            html += `<td>${row.sno || ''}</td>`;
            html += `<td>${row.description || ''}</td>`;
            html += `<td>${row.payment_round_number || ''}</td>`;
            html += `<td>${row.plan_customer_count || 0}</td>`;
            html += `<td>${row.plan_amount_birr || 0}</td>`;
            html += `<td>${row.plan_amount_dollar || 0}</td>`;
            html += `<td>${row.report_customer_count || 0}</td>`;
            html += `<td>${row.report_amount_birr || 0}</td>`;
            html += `<td>${row.report_amount_dollar || 0}</td>`;
            html += `<td>${row.remark || ''}</td>`;
            html += '</tr>';
        });
        
        html += '</tbody></table>';
        return html;
    }
}

CollectionStageReportClient.template = "collection_reports.CollectionStageReportClient";

registry.category("actions").add("collection_reports.collection_stage", CollectionStageReportClient);

