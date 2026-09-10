/** @odoo-module **/

import { Component, useState, onWillStart, useEffect } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class TeamActivityReport extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.userService = useService("user");
        
        const today = new Date();
        const formatDate = (date) => {
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            return `${year}-${month}-${day}`;
        };
        
        const user = this.userService;
        
        this.state = useState({
            data: [],
            filtered_data: [],
            loading: false,
            show_report: false,
            date_from: formatDate(today),
            date_to: formatDate(today),
            header_info: {},
            search_text: '',
            is_admin: false, 
            admin_wing_id: null,
            admin_wings: [], 
        });

        onWillStart(async () => {
          
            try {
                const isSystemAdmin = await user.hasGroup('base.group_system');
                const isErpManager = await user.hasGroup('base.group_erp_manager');
                const isAdmin = isSystemAdmin || isErpManager;
                
                this.state.is_admin = Boolean(isAdmin);
                
                if (isAdmin) {
                    await this.loadAdminWings();
                } else {
                    
                    this.state.admin_wing_id = null;
                    this.state.admin_wings = [];
                }
            } catch (error) {
                console.error('Error checking admin status:', error);
                this.state.is_admin = false;
                this.state.admin_wing_id = null;
                this.state.admin_wings = [];
            }
            
            // Don't auto-load data; wait for user to click Show Report
        });

        useEffect(
            () => {
                this.filterData();
            },
            () => [this.state.search_text, this.state.data]
        );

        useEffect(
            () => {
                
                const syncScroll = () => {
                    const mainTable = document.querySelector('.table_container');
                    const totalContainer = document.querySelector('.total_row_container');
                    if (mainTable && totalContainer) {
                        // Sync the scroll position
                        totalContainer.scrollLeft = mainTable.scrollLeft;
                    }
                };
                
                const mainTable = document.querySelector('.table_container');
                const totalContainer = document.querySelector('.total_row_container');
                
                if (mainTable && totalContainer) {
                    // Prevent manual scrolling on total row container
                    const preventManualScroll = (e) => {
                        // Only allow scrolling via sync, not manual user interaction
                        if (totalContainer.scrollLeft !== mainTable.scrollLeft) {
                            totalContainer.scrollLeft = mainTable.scrollLeft;
                        }
                    };
                    
                    // Prevent touch scrolling on total container
                    const preventTouchScroll = (e) => {
                        e.preventDefault();
                        syncScroll();
                    };
                    
                    // Prevent wheel scrolling on total container
                    const preventWheelScroll = (e) => {
                        e.preventDefault();
                        syncScroll();
                    };
                    
                    totalContainer.addEventListener('scroll', preventManualScroll, { passive: false });
                    totalContainer.addEventListener('touchstart', preventTouchScroll, { passive: false });
                    totalContainer.addEventListener('touchmove', preventTouchScroll, { passive: false });
                    totalContainer.addEventListener('wheel', preventWheelScroll, { passive: false });
                    
                    mainTable.addEventListener('scroll', syncScroll);
                    
                    return () => {
                        mainTable.removeEventListener('scroll', syncScroll);
                        totalContainer.removeEventListener('scroll', preventManualScroll);
                        totalContainer.removeEventListener('touchstart', preventTouchScroll);
                        totalContainer.removeEventListener('touchmove', preventTouchScroll);
                        totalContainer.removeEventListener('wheel', preventWheelScroll);
                    };
                }
            },
            () => [this.state.filtered_data]
        );
    }

    filterData() {
        if (!this.state.search_text || !this.state.search_text.trim()) {
           
            this.state.filtered_data = [...this.state.data];
            return;
        }
        
        const searchLower = this.state.search_text.toLowerCase().trim();
        const filtered = this.state.data.map(group => {
           
            const filteredSalespersons = group.salespersons.filter(salesperson => {
                const supervisorName = (group.supervisor || '').toLowerCase();
                const salespersonName = (salesperson.salesperson || '').toLowerCase();
                return supervisorName.includes(searchLower) || salespersonName.includes(searchLower);
            });
            
          
            if (filteredSalespersons.length > 0) {
                return {
                    ...group,
                    salespersons: filteredSalespersons
                };
            }
            return null;
        }).filter(group => group !== null);
        
        this.state.filtered_data = filtered;
    }

    onSearchChange() {
        this.filterData();
    }

    async loadData() {
        this.state.loading = true;
        try {
            // Only send admin_wing_id if user is admin
            const params = {
                date_from: this.state.date_from || null,
                date_to: this.state.date_to || null,
            };
            
           
            if (this.state.is_admin && this.state.admin_wing_id) {
                params.wing_id = this.state.admin_wing_id;
            }
            
            const result = await this.rpc('/team_activity_report/api/get_data', params);
            
            if (result && result.success) {
                this.state.data = result.data || [];
                this.state.header_info = result.header_info || {};
                this.filterData();
            } else {
                console.error('Error loading data:', result.error);
                this.state.data = [];
                this.state.filtered_data = [];
                this.state.header_info = {};
            }
        } catch (error) {
            console.error('Error loading team activity data:', error);
            this.state.data = [];
            this.state.filtered_data = [];
        } finally {
            this.state.loading = false;
        }
    }

    async onShowReport() {
        this.state.show_report = true;
        await this.loadData();
    }

    onDateFromChange(ev) {
        this.state.date_from = ev.target.value;
        if (this.state.show_report) {
            this.loadData();
        }
    }

    onDateToChange(ev) {
        this.state.date_to = ev.target.value;
        if (this.state.show_report) {
            this.loadData();
        }
    }

    async loadAdminWings() {
       
        if (!this.state.is_admin) {
            this.state.admin_wings = [];
            this.state.admin_wing_id = null;
            return;
        }
        
        try {
            const result = await this.rpc('/team_activity_report/api/get_wings', {});
            if (result && result.success && result.wings) {
                this.state.admin_wings = result.wings || [];
            } else {
                this.state.admin_wings = [];
            }
        } catch (error) {
            console.error('Error loading admin wings:', error);
            this.state.admin_wings = [];
        }
    }

    onAdminWingChange(ev) {
        if (!this.state.is_admin) {
            return;
        }
        const wingId = ev.target.value ? parseInt(ev.target.value) : null;
        this.state.admin_wing_id = wingId;
        if (this.state.show_report) {
            this.loadData();
        }
    }


    async exportExcel() {
        try {
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = '/team_activity_report/api/export_excel';
            
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
            
           
            if (this.state.is_admin && this.state.admin_wing_id) {
                const input = document.createElement('input');
                input.type = 'hidden';
                input.name = 'wing_id';
                input.value = this.state.admin_wing_id;
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
        try {
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = '/team_activity_report/api/export_pdf';
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
            
           
            if (this.state.is_admin && this.state.admin_wing_id) {
                const input = document.createElement('input');
                input.type = 'hidden';
                input.name = 'wing_id';
                input.value = this.state.admin_wing_id;
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

    getFollowUpColumns() {
        
        const activityTypes = new Set();
        this.state.filtered_data.forEach(group => {
            if (group.salespersons) {
                group.salespersons.forEach(salesperson => {
                    if (salesperson.follow_up) {
                        Object.keys(salesperson.follow_up).forEach(key => {
                            if (salesperson.follow_up[key] > 0) {
                                activityTypes.add(key);
                            }
                        });
                    }
                });
            }
        });
        return Array.from(activityTypes).sort();
    }

    getFollowUpValue(salesperson, activityType) {
        return (salesperson.follow_up && salesperson.follow_up[activityType]) || 0;
    }

    getFollowUpTotal(salesperson) {
        if (!salesperson.follow_up) return 0;
        return Object.values(salesperson.follow_up).reduce((sum, val) => sum + (val || 0), 0);
    }

    getTotalProspect() {
        let total = 0;
        this.state.filtered_data.forEach(group => {
            if (group.salespersons) {
                group.salespersons.forEach(salesperson => {
                    total += salesperson.prospect || 0;
                });
            }
        });
        return total;
    }

    getTotalFollowUp(activityType) {
        let total = 0;
        this.state.filtered_data.forEach(group => {
            if (group.salespersons) {
                group.salespersons.forEach(salesperson => {
                    if (salesperson.follow_up && salesperson.follow_up[activityType]) {
                        total += salesperson.follow_up[activityType] || 0;
                    }
                });
            }
        });
        return total;
    }

    getTotalFollowUpTotal() {
        let total = 0;
        this.state.filtered_data.forEach(group => {
            if (group.salespersons) {
                group.salespersons.forEach(salesperson => {
                    total += this.getFollowUpTotal(salesperson);
                });
            }
        });
        return total;
    }

    getTotalReservation() {
        let total = 0;
        this.state.filtered_data.forEach(group => {
            if (group.salespersons) {
                group.salespersons.forEach(salesperson => {
                    total += salesperson.reservation || 0;
                });
            }
        });
        return total;
    }

    getTotalSold() {
        let total = 0;
        this.state.filtered_data.forEach(group => {
            if (group.salespersons) {
                group.salespersons.forEach(salesperson => {
                    total += salesperson.sold || 0;
                });
            }
        });
        return total;
    }

    getTotalUserCount() {
        let count = 0;
        this.state.filtered_data.forEach(group => {
            if (group.salespersons) {
                count += group.salespersons.length;
            }
        });
        return count;
    }
}

TeamActivityReport.template = "team_activity_report.TeamActivityReport";

registry.category("actions").add("team_activity_report.report", TeamActivityReport);

