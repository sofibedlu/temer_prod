/** @odoo-module **/

import { Component, useState, onWillStart, useEffect, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class ActualPaidReportClient extends Component {
    setup() {
        this.notification = useService("notification");
        this.isMounted = true;
        
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
        if (this.state.search_text && this.state.search_text.trim()) {
            const searchLower = this.state.search_text.toLowerCase().trim();
            filtered = filtered.filter(row => {
                const description = (row.description || '').toLowerCase();
                return description.includes(searchLower);
            });
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
            // Call the actual_paid endpoint which delegates to api_summarized_report
            const response = await fetch("/collection_reports/api/actual_paid", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
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
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            
            const result = await response.json();
            let apiData = result?.result || result;
            
            if (!this.isMounted) return;
            
            // Transform API data into the 9 fixed rows structure
            const transformedData = [];
            
            if (apiData?.success && apiData.data && apiData.data.length > 0) {
                // Aggregate data across all sites
                let fullyPaidCustomers = 0;
                let fullyPaidAmountBirr = 0;
                let fullyPaidAmountDollar = 0;
                
                let partialCustomers = 0;
                let partialAmountBirr = 0;
                let partialAmountDollar = 0;
                
                let advanceCustomers = 0;
                let advanceAmountBirr = 0;
                let advanceAmountDollar = 0;
                
                let otherCustomers = 0;
                let otherAmountBirr = 0;
                let otherAmountDollar = 0;
                
                let totalCollectionCustomers = 0;
                let totalCollectionAmountBirr = 0;
                let totalCollectionAmountDollar = 0;
                
                let totalPlanCustomers = 0;
                let totalPlanAmountBirr = 0;
                let totalPlanAmountDollar = 0;
                
                let totalCollectedFromPlannedCustomers = 0;
                let totalCollectedFromPlannedAmountBirr = 0;
                let totalCollectedFromPlannedAmountDollar = 0;
                
                let totalRemainedUncollectedCustomers = 0;
                let totalRemainedUncollectedAmountBirr = 0;
                let totalRemainedUncollectedAmountDollar = 0;
                
                let paymentExtensionCustomers = 0;
                let paymentExtensionAmountBirr = 0;
                let paymentExtensionAmountDollar = 0;
                
                // Aggregate from all sites
                apiData.data.forEach((siteData) => {
                    // FULLY PAID: Collections where amount_remaining == 0 (execution - remaining)
                    // This is approximate: execution_customers - remaining_customers
                    const siteFullyPaidCustomers = Math.max(0, (siteData.execution_customers || 0) - (siteData.remaining_customers || 0));
                    fullyPaidCustomers += siteFullyPaidCustomers;
                    // Amount: execution_amount - remaining_amount
                    const siteFullyPaidBirr = Math.max(0, (siteData.execution_amount_birr || 0) - (siteData.remaining_amount_birr || 0));
                    fullyPaidAmountBirr += siteFullyPaidBirr;
                    const siteFullyPaidDollar = Math.max(0, (siteData.execution_amount_dollar || 0) - (siteData.remaining_amount_dollar || 0));
                    fullyPaidAmountDollar += siteFullyPaidDollar;
                    
                    // SEMI/PARTIAL PAID
                    partialCustomers += siteData.partial_customers || 0;
                    partialAmountBirr += siteData.partial_amount_birr || 0;
                    partialAmountDollar += siteData.partial_amount_dollar || 0;
                    
                    // COLLECTION FROM ADVANCE REMAINING - TODO: Need to check if there's advance payment data
                    // For now, set to 0 or use a placeholder
                    advanceCustomers += 0; // TODO: Calculate from advance payments
                    advanceAmountBirr += 0;
                    advanceAmountDollar += 0;
                    
                    // OTHER COLLECTION
                    otherCustomers += siteData.other_customers || 0;
                    otherAmountBirr += siteData.other_amount_birr || 0;
                    otherAmountDollar += siteData.other_amount_dollar || 0;
                    
                    // TOTAL COLLECTION
                    totalCollectionCustomers += siteData.total_customers || 0;
                    totalCollectionAmountBirr += siteData.total_amount_birr || 0;
                    totalCollectionAmountDollar += siteData.total_amount_dollar || 0;
                    
                    // TOTAL AMOUNT PLAN TO COLLECT
                    totalPlanCustomers += siteData.plan_customers || 0;
                    totalPlanAmountBirr += siteData.plan_amount_birr || 0;
                    totalPlanAmountDollar += siteData.plan_amount_dollar || 0;
                    
                    // TOTAL COLLECTED FROM PLANNED (execution)
                    totalCollectedFromPlannedCustomers += siteData.execution_customers || 0;
                    totalCollectedFromPlannedAmountBirr += siteData.execution_amount_birr || 0;
                    totalCollectedFromPlannedAmountDollar += siteData.execution_amount_dollar || 0;
                    
                    // TOTAL AMOUNT REMAINED UNCOLLECTED
                    totalRemainedUncollectedCustomers += siteData.remaining_customers || 0;
                    totalRemainedUncollectedAmountBirr += siteData.remaining_amount_birr || 0;
                    totalRemainedUncollectedAmountDollar += siteData.remaining_amount_dollar || 0;
                    
                    // PAYMENT EXTENSION
                    paymentExtensionCustomers += siteData.extension_customers || 0;
                    paymentExtensionAmountBirr += siteData.extension_amount_birr || 0;
                    paymentExtensionAmountDollar += (siteData.extension_amount_birr || 0) * 0.0064; // Approximate conversion
                });
                
                // Row 1: FULLY PAID FOR THE ROUND NUMBER
                transformedData.push({
                    sno: 1,
                    description: 'FULLY PAID FOR THE ROUND NUMBER',
                    payment_round_number: '',
                    customer_count: fullyPaidCustomers,
                    amount_birr: Math.round(fullyPaidAmountBirr * 100) / 100,
                    amount_dollar: Math.round(fullyPaidAmountDollar * 100) / 100,
                    remark: ''
                });
                
                // Row 2: SEMI/PARTIAL PAID FOR ROUND PAYMENT
                transformedData.push({
                    sno: 2,
                    description: 'SEMI/PARTIAL PAID FOR ROUND PAYMENT',
                    payment_round_number: '',
                    customer_count: partialCustomers,
                    amount_birr: Math.round(partialAmountBirr * 100) / 100,
                    amount_dollar: Math.round(partialAmountDollar * 100) / 100,
                    remark: ''
                });
                
                // Row 3: COLLECTION FROM ADVANCE REMAINING
                transformedData.push({
                    sno: 3,
                    description: 'COLLECTION FROM ADVANCE REMAINING',
                    payment_round_number: '',
                    customer_count: advanceCustomers,
                    amount_birr: Math.round(advanceAmountBirr * 100) / 100,
                    amount_dollar: Math.round(advanceAmountDollar * 100) / 100,
                    remark: ''
                });
                
                // Row 4: OTHER COLLECTION
                transformedData.push({
                    sno: 4,
                    description: 'OTHER COLLECTION',
                    payment_round_number: '',
                    customer_count: otherCustomers,
                    amount_birr: Math.round(otherAmountBirr * 100) / 100,
                    amount_dollar: Math.round(otherAmountDollar * 100) / 100,
                    remark: ''
                });
                
                // Row 5: TOTAL COLLECTION
                transformedData.push({
                    sno: 5,
                    description: 'TOTAL COLLECTION',
                    payment_round_number: '',
                    customer_count: totalCollectionCustomers,
                    amount_birr: Math.round(totalCollectionAmountBirr * 100) / 100,
                    amount_dollar: Math.round(totalCollectionAmountDollar * 100) / 100,
                    remark: ''
                });
                
                // Row 6: TOTAL AMOUNT PLAN TO COLLECT
                transformedData.push({
                    sno: 6,
                    description: 'TOTAL AMOUNT PLAN TO COLLECT',
                    payment_round_number: '',
                    customer_count: totalPlanCustomers,
                    amount_birr: Math.round(totalPlanAmountBirr * 100) / 100,
                    amount_dollar: Math.round(totalPlanAmountDollar * 100) / 100,
                    remark: ''
                });
                
                // Row 7: TOTAL COLLECTED FROM PLANNED
                transformedData.push({
                    sno: 7,
                    description: 'TOTAL COLLECTED FROM PLANNED',
                    payment_round_number: '',
                    customer_count: totalCollectedFromPlannedCustomers,
                    amount_birr: Math.round(totalCollectedFromPlannedAmountBirr * 100) / 100,
                    amount_dollar: Math.round(totalCollectedFromPlannedAmountDollar * 100) / 100,
                    remark: ''
                });
                
                // Row 8: TOTAL AMOUNT REMAINED UNCOLLECTED
                transformedData.push({
                    sno: 8,
                    description: 'TOTAL AMOUNT REMAINED UNCOLLECTED',
                    payment_round_number: '',
                    customer_count: totalRemainedUncollectedCustomers,
                    amount_birr: Math.round(totalRemainedUncollectedAmountBirr * 100) / 100,
                    amount_dollar: Math.round(totalRemainedUncollectedAmountDollar * 100) / 100,
                    remark: ''
                });
                
                // Row 9: PAYMENT EXTENSION
                transformedData.push({
                    sno: 9,
                    description: 'PAYMENT EXTENSION',
                    payment_round_number: '',
                    customer_count: paymentExtensionCustomers,
                    amount_birr: Math.round(paymentExtensionAmountBirr * 100) / 100,
                    amount_dollar: Math.round(paymentExtensionAmountDollar * 100) / 100,
                    remark: ''
                });
            } else {
                // Even if no data, show the 9 fixed rows with zeros
                const descriptions = [
                    'FULLY PAID FOR THE ROUND NUMBER',
                    'SEMI/PARTIAL PAID FOR ROUND PAYMENT',
                    'COLLECTION FROM ADVANCE REMAINING',
                    'OTHER COLLECTION',
                    'TOTAL COLLECTION',
                    'TOTAL AMOUNT PLAN TO COLLECT',
                    'TOTAL COLLECTED FROM PLANNED',
                    'TOTAL AMOUNT REMAINED UNCOLLECTED',
                    'PAYMENT EXTENSION'
                ];
                
                descriptions.forEach((desc, index) => {
                    transformedData.push({
                        sno: index + 1,
                        description: desc,
                        payment_round_number: '',
                        customer_count: 0,
                        amount_birr: 0,
                        amount_dollar: 0,
                        remark: ''
                    });
                });
            }
            
            if (this.isMounted) {
                this.state.data = transformedData;
                this.state.totals = apiData.totals || {};
                this.filterData();
            }
        } catch (error) {
            if (this.isMounted) {
                console.error("Error loading data:", error);
                this.state.data = [];
                this.state.filtered_data = [];
                this.state.totals = {};
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
            reportTypeInput.value = 'actual_paid';
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
        } catch (error) {
            console.error("Error exporting Excel:", error);
            this.notification.add("Error exporting Excel", { type: "danger" });
        }
    }

    async exportPDF() {
        if (!this.state.filtered_data || this.state.filtered_data.length === 0) {
            this.notification.add("No data to export", { type: "warning" });
            return;
        }
        // PDF export logic similar to collection_stage_report_client.js
        this.notification.add("PDF export functionality to be implemented", { type: "info" });
    }
}

ActualPaidReportClient.template = "collection_reports.ActualPaidReportClient";
registry.category("actions").add("collection_reports.actual_paid", ActualPaidReportClient);

