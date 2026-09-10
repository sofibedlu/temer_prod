// // // // // // // // // // // // // /** @odoo-module **/

// // // // // // // // // // // // // import { registry } from "@web/core/registry";
// // // // // // // // // // // // // import { useService } from "@web/core/utils/hooks";
// // // // // // // // // // // // // import { Component, onWillStart, useState } from "@odoo/owl";

// // // // // // // // // // // // // const actionRegistry = registry.category("actions");

// // // // // // // // // // // // // export class PropertyDashboard extends Component {
// // // // // // // // // // // // //     setup() {
// // // // // // // // // // // // //         this.orm = useService("orm");
// // // // // // // // // // // // //         this.action = useService("action");

// // // // // // // // // // // // //         this.state = useState({
// // // // // // // // // // // // //             floors: [],
// // // // // // // // // // // // //             propertiesByFloor: {},
// // // // // // // // // // // // //             siteFilter: '',
// // // // // // // // // // // // //         });

// // // // // // // // // // // // //         onWillStart(async () => {
// // // // // // // // // // // // //             await this.loadDashboard();
// // // // // // // // // // // // //         });
// // // // // // // // // // // // //     }

// // // // // // // // // // // // //     async loadDashboard() {
// // // // // // // // // // // // //         const domain = this.state.siteFilter
// // // // // // // // // // // // //             ? [["location", "ilike", this.state.siteFilter]]
// // // // // // // // // // // // //             : [];

// // // // // // // // // // // // //         const properties = await this.orm.searchRead(
// // // // // // // // // // // // //             "property.property",
// // // // // // // // // // // // //             domain,
// // // // // // // // // // // // //             ["id", "name", "location", "floor_id", "state"],
// // // // // // // // // // // // //         );

// // // // // // // // // // // // //         const floorsSet = new Set();
// // // // // // // // // // // // //         const propertiesByFloor = {};

// // // // // // // // // // // // //         properties.forEach((prop) => {
// // // // // // // // // // // // //             // floor_id is usually [id, name] or null
// // // // // // // // // // // // //             const floorKey = prop.floor_id ? prop.floor_id[0] : null;
// // // // // // // // // // // // //             if (floorKey) {
// // // // // // // // // // // // //                 floorsSet.add(floorKey);
// // // // // // // // // // // // //                 if (!propertiesByFloor[floorKey]) propertiesByFloor[floorKey] = [];
// // // // // // // // // // // // //                 propertiesByFloor[floorKey].push({
// // // // // // // // // // // // //                     ...prop,
// // // // // // // // // // // // //                     floor_name: prop.floor_id[1],
// // // // // // // // // // // // //                 });
// // // // // // // // // // // // //             }
// // // // // // // // // // // // //         });

// // // // // // // // // // // // //         this.state.floors = Array.from(floorsSet).sort((a, b) => a - b);
// // // // // // // // // // // // //         this.state.propertiesByFloor = propertiesByFloor;
// // // // // // // // // // // // //     }

// // // // // // // // // // // // //     async onSearchChange(ev) {
// // // // // // // // // // // // //         this.state.siteFilter = ev.target.value;
// // // // // // // // // // // // //         await this.loadDashboard();
// // // // // // // // // // // // //     }

// // // // // // // // // // // // //     openProperty(id) {
// // // // // // // // // // // // //         this.action.doAction({
// // // // // // // // // // // // //             type: "ir.actions.act_window",
// // // // // // // // // // // // //             res_model: "property.property",
// // // // // // // // // // // // //             res_id: id,
// // // // // // // // // // // // //             views: [[false, "form"]],
// // // // // // // // // // // // //             target: "current",
// // // // // // // // // // // // //         });
// // // // // // // // // // // // //     }
// // // // // // // // // // // // // }

// // // // // // // // // // // // // PropertyDashboard.template = "property_dashboard.template";
// // // // // // // // // // // // // actionRegistry.add("property_dashboard", PropertyDashboard);






// // // // // // // // // // // // /** @odoo-module **/

// // // // // // // // // // // // import { registry } from "@web/core/registry";
// // // // // // // // // // // // import { useService } from "@web/core/utils/hooks";
// // // // // // // // // // // // import { Component, onWillStart, useState } from "@odoo/owl";

// // // // // // // // // // // // const actionRegistry = registry.category("actions");

// // // // // // // // // // // // export class PropertyDashboard extends Component {
// // // // // // // // // // // //     setup() {
// // // // // // // // // // // //         this.orm = useService("orm");
// // // // // // // // // // // //         this.action = useService("action");

// // // // // // // // // // // //         this.state = useState({
// // // // // // // // // // // //             floors: [],
// // // // // // // // // // // //             propertiesByFloor: {},
// // // // // // // // // // // //             sites: [],
// // // // // // // // // // // //             selectedSite: '',
// // // // // // // // // // // //             siteFilter: '',
// // // // // // // // // // // //         });

// // // // // // // // // // // //         onWillStart(async () => {
// // // // // // // // // // // //             await this.loadDashboard();
// // // // // // // // // // // //         });
// // // // // // // // // // // //     }

// // // // // // // // // // // //     async loadDashboard() {
// // // // // // // // // // // //         // Fetch sites for the dropdown
// // // // // // // // // // // //         const sites = await this.orm.searchRead(
// // // // // // // // // // // //             "property.site",
// // // // // // // // // // // //             [],
// // // // // // // // // // // //             ["id", "name"]
// // // // // // // // // // // //         );
// // // // // // // // // // // //         this.state.sites = sites;

// // // // // // // // // // // //         // Build domain based on filters
// // // // // // // // // // // //         const domain = [];
// // // // // // // // // // // //         if (this.state.selectedSite) {
// // // // // // // // // // // //             domain.push(["site", "=", parseInt(this.state.selectedSite)]);
// // // // // // // // // // // //         }
// // // // // // // // // // // //         if (this.state.siteFilter) {
// // // // // // // // // // // //             domain.push(["location", "ilike", this.state.siteFilter]);
// // // // // // // // // // // //         }

// // // // // // // // // // // //         const properties = await this.orm.searchRead(
// // // // // // // // // // // //             "property.property",
// // // // // // // // // // // //             domain,
// // // // // // // // // // // //             ["id", "name", "location", "floor_id", "state", "net_area", "gross_area", "bedroom", "unit_price", "site"]
// // // // // // // // // // // //         );

// // // // // // // // // // // //         const floorsSet = new Set();
// // // // // // // // // // // //         const propertiesByFloor = {};

// // // // // // // // // // // //         properties.forEach((prop) => {
// // // // // // // // // // // //             const floorKey = prop.floor_id ? prop.floor_id[0] : null;
// // // // // // // // // // // //             if (floorKey) {
// // // // // // // // // // // //                 floorsSet.add(floorKey);
// // // // // // // // // // // //                 if (!propertiesByFloor[floorKey]) propertiesByFloor[floorKey] = [];
// // // // // // // // // // // //                 propertiesByFloor[floorKey].push({
// // // // // // // // // // // //                     ...prop,
// // // // // // // // // // // //                     floor_name: prop.floor_id ? prop.floor_id[1] : null,
// // // // // // // // // // // //                 });
// // // // // // // // // // // //             }
// // // // // // // // // // // //         });

// // // // // // // // // // // //         this.state.floors = Array.from(floorsSet).sort((a, b) => a - b);
// // // // // // // // // // // //         this.state.propertiesByFloor = propertiesByFloor;
// // // // // // // // // // // //     }

// // // // // // // // // // // //     async onSearchChange(ev) {
// // // // // // // // // // // //         this.state.siteFilter = ev.target.value;
// // // // // // // // // // // //         await this.loadDashboard();
// // // // // // // // // // // //     }

// // // // // // // // // // // //     async onSiteFilterChange(ev) {
// // // // // // // // // // // //         this.state.selectedSite = ev.target.value;
// // // // // // // // // // // //         await this.loadDashboard();
// // // // // // // // // // // //     }

// // // // // // // // // // // //     openProperty(id) {
// // // // // // // // // // // //         this.action.doAction({
// // // // // // // // // // // //             type: "ir.actions.act_window",
// // // // // // // // // // // //             res_model: "property.property",
// // // // // // // // // // // //             res_id: id,
// // // // // // // // // // // //             views: [[false, "form"]],
// // // // // // // // // // // //             target: "current",
// // // // // // // // // // // //         });
// // // // // // // // // // // //     }
// // // // // // // // // // // // }

// // // // // // // // // // // // PropertyDashboard.template = "property_dashboard.template";
// // // // // // // // // // // // actionRegistry.add("property_dashboard", PropertyDashboard);








// // // // // // // // // // // /** @odoo-module **/

// // // // // // // // // // // import { registry } from "@web/core/registry";
// // // // // // // // // // // import { useService } from "@web/core/utils/hooks";
// // // // // // // // // // // import { Component, onWillStart, useState } from "@odoo/owl";

// // // // // // // // // // // const actionRegistry = registry.category("actions");

// // // // // // // // // // // export class PropertyDashboard extends Component {
// // // // // // // // // // //     setup() {
// // // // // // // // // // //         this.orm = useService("orm");
// // // // // // // // // // //         this.action = useService("action");

// // // // // // // // // // //         this.state = useState({
// // // // // // // // // // //             floors: [],
// // // // // // // // // // //             propertiesByFloor: {},
// // // // // // // // // // //             sites: [],
// // // // // // // // // // //             selectedSite: "",
// // // // // // // // // // //             selectedStates: [], // e.g., ['available','reserved']
// // // // // // // // // // //         });

// // // // // // // // // // //         onWillStart(async () => {
// // // // // // // // // // //             await this.loadDashboard();
// // // // // // // // // // //         });
// // // // // // // // // // //     }

// // // // // // // // // // //     async loadDashboard() {
// // // // // // // // // // //         // Sites
// // // // // // // // // // //         const sites = await this.orm.searchRead("property.site", [], ["id", "name"]);
// // // // // // // // // // //         this.state.sites = sites;

// // // // // // // // // // //         // Domain from filters
// // // // // // // // // // //         const domain = [];
// // // // // // // // // // //         if (this.state.selectedSite) {
// // // // // // // // // // //             domain.push(["site", "=", parseInt(this.state.selectedSite)]);
// // // // // // // // // // //         }
// // // // // // // // // // //         if (this.state.selectedStates && this.state.selectedStates.length) {
// // // // // // // // // // //             domain.push(["state", "in", this.state.selectedStates]);
// // // // // // // // // // //         }

// // // // // // // // // // //         const properties = await this.orm.searchRead(
// // // // // // // // // // //             "property.property",
// // // // // // // // // // //             domain,
// // // // // // // // // // //             ["id","name","location","floor_id","state","net_area","gross_area","bedroom","unit_price","site"]
// // // // // // // // // // //         );

// // // // // // // // // // //         const floorsSet = new Set();
// // // // // // // // // // //         const propertiesByFloor = {};
// // // // // // // // // // //         properties.forEach((prop) => {
// // // // // // // // // // //             const floorKey = prop.floor_id ? prop.floor_id[0] : null;
// // // // // // // // // // //             if (floorKey) {
// // // // // // // // // // //                 floorsSet.add(floorKey);
// // // // // // // // // // //                 if (!propertiesByFloor[floorKey]) propertiesByFloor[floorKey] = [];
// // // // // // // // // // //                 propertiesByFloor[floorKey].push({ ...prop, floor_name: prop.floor_id ? prop.floor_id[1] : null });
// // // // // // // // // // //             }
// // // // // // // // // // //         });

// // // // // // // // // // //         this.state.floors = Array.from(floorsSet).sort((a, b) => a - b);
// // // // // // // // // // //         this.state.propertiesByFloor = propertiesByFloor;
// // // // // // // // // // //     }

// // // // // // // // // // //     async onSiteFilterChange(ev) {
// // // // // // // // // // //         this.state.selectedSite = ev.target.value;
// // // // // // // // // // //         await this.loadDashboard();
// // // // // // // // // // //     }

// // // // // // // // // // //     async toggleState(stateVal) {
// // // // // // // // // // //         const i = this.state.selectedStates.indexOf(stateVal);
// // // // // // // // // // //         if (i === -1) {
// // // // // // // // // // //             this.state.selectedStates = [...this.state.selectedStates, stateVal];
// // // // // // // // // // //         } else {
// // // // // // // // // // //             const next = [...this.state.selectedStates];
// // // // // // // // // // //             next.splice(i, 1);
// // // // // // // // // // //             this.state.selectedStates = next;
// // // // // // // // // // //         }
// // // // // // // // // // //         await this.loadDashboard();
// // // // // // // // // // //     }

// // // // // // // // // // //     openProperty(id) {
// // // // // // // // // // //         this.action.doAction({
// // // // // // // // // // //             type: "ir.actions.act_window",
// // // // // // // // // // //             res_model: "property.property",
// // // // // // // // // // //             res_id: id,
// // // // // // // // // // //             views: [[false, "form"]],
// // // // // // // // // // //             target: "current",
// // // // // // // // // // //         });
// // // // // // // // // // //     }
// // // // // // // // // // // }

// // // // // // // // // // // PropertyDashboard.template = "property_dashboard.template";
// // // // // // // // // // // actionRegistry.add("property_dashboard", PropertyDashboard);









// // // // // // // // // // /** @odoo-module **/

// // // // // // // // // // import { registry } from "@web/core/registry";
// // // // // // // // // // import { useService } from "@web/core/utils/hooks";
// // // // // // // // // // import { Component, onWillStart, useState } from "@odoo/owl";

// // // // // // // // // // const actionRegistry = registry.category("actions");

// // // // // // // // // // export class PropertyDashboard extends Component {
// // // // // // // // // //     setup() {
// // // // // // // // // //         this.orm = useService("orm");
// // // // // // // // // //         this.action = useService("action");

// // // // // // // // // //         this.state = useState({
// // // // // // // // // //             floors: [],
// // // // // // // // // //             propertiesByFloor: {},
// // // // // // // // // //             sites: [],
// // // // // // // // // //             selectedSite: "",
// // // // // // // // // //             selectedStates: [], // e.g., ['available','reserved']
// // // // // // // // // //         });

// // // // // // // // // //         onWillStart(async () => {
// // // // // // // // // //             await this.loadDashboard();
// // // // // // // // // //         });
// // // // // // // // // //     }

// // // // // // // // // //     loadDashboard = async () => {
// // // // // // // // // //         // Sites
// // // // // // // // // //         const sites = await this.orm.searchRead("property.site", [], ["id", "name"]);
// // // // // // // // // //         this.state.sites = sites;

// // // // // // // // // //         // Domain from filters
// // // // // // // // // //         const domain = [];
// // // // // // // // // //         if (this.state.selectedSite) {
// // // // // // // // // //             domain.push(["site", "=", parseInt(this.state.selectedSite)]);
// // // // // // // // // //         }
// // // // // // // // // //         if (this.state.selectedStates && this.state.selectedStates.length) {
// // // // // // // // // //             domain.push(["state", "in", this.state.selectedStates]);
// // // // // // // // // //         }

// // // // // // // // // //         const properties = await this.orm.searchRead(
// // // // // // // // // //             "property.property",
// // // // // // // // // //             domain,
// // // // // // // // // //             ["id","name","location","floor_id","state","net_area","gross_area","bedroom","unit_price","site"]
// // // // // // // // // //         );

// // // // // // // // // //         const floorsSet = new Set();
// // // // // // // // // //         const propertiesByFloor = {};
// // // // // // // // // //         for (const prop of properties) {
// // // // // // // // // //             const floorKey = prop.floor_id && prop.floor_id[0];
// // // // // // // // // //             if (!floorKey) continue;
// // // // // // // // // //             floorsSet.add(floorKey);
// // // // // // // // // //             (propertiesByFloor[floorKey] ||= []).push({
// // // // // // // // // //                 ...prop,
// // // // // // // // // //                 floor_name: prop.floor_id ? prop.floor_id[1] : null,
// // // // // // // // // //             });
// // // // // // // // // //         }

// // // // // // // // // //         this.state.floors = Array.from(floorsSet).sort((a, b) => a - b);
// // // // // // // // // //         this.state.propertiesByFloor = propertiesByFloor;
// // // // // // // // // //     };

// // // // // // // // // //     onSiteFilterChange = async (ev) => {
// // // // // // // // // //         this.state.selectedSite = ev.target.value;
// // // // // // // // // //         await this.loadDashboard();
// // // // // // // // // //     };

// // // // // // // // // //     toggleState = async (stateVal) => {
// // // // // // // // // //         const i = this.state.selectedStates.indexOf(stateVal);
// // // // // // // // // //         if (i === -1) {
// // // // // // // // // //             this.state.selectedStates = [...this.state.selectedStates, stateVal];
// // // // // // // // // //         } else {
// // // // // // // // // //             const next = [...this.state.selectedStates];
// // // // // // // // // //             next.splice(i, 1);
// // // // // // // // // //             this.state.selectedStates = next;
// // // // // // // // // //         }
// // // // // // // // // //         await this.loadDashboard();
// // // // // // // // // //     };

// // // // // // // // // //     openProperty(id) {
// // // // // // // // // //         this.action.doAction({
// // // // // // // // // //             type: "ir.actions.act_window",
// // // // // // // // // //             res_model: "property.property",
// // // // // // // // // //             res_id: id,
// // // // // // // // // //             views: [[false, "form"]],
// // // // // // // // // //             target: "current",
// // // // // // // // // //         });
// // // // // // // // // //     }
// // // // // // // // // // }

// // // // // // // // // // PropertyDashboard.template = "property_dashboard.template";
// // // // // // // // // // actionRegistry.add("property_dashboard", PropertyDashboard);








// // // // // // // // // /** @odoo-module **/

// // // // // // // // // import { registry } from "@web/core/registry";
// // // // // // // // // import { useService } from "@web/core/utils/hooks";
// // // // // // // // // import { Component, onWillStart, useState } from "@odoo/owl";

// // // // // // // // // const actionRegistry = registry.category("actions");

// // // // // // // // // export class PropertyDashboard extends Component {
// // // // // // // // //     setup() {
// // // // // // // // //         this.orm = useService("orm");
// // // // // // // // //         this.action = useService("action");

// // // // // // // // //         this.state = useState({
// // // // // // // // //             floors: [],
// // // // // // // // //             propertiesByFloor: {},
// // // // // // // // //             sites: [],
// // // // // // // // //             selectedSite: "",
// // // // // // // // //             selectedStates: [], // e.g., ['available','reserved']
// // // // // // // // //         });

// // // // // // // // //         onWillStart(async () => {
// // // // // // // // //             await this.loadDashboard();
// // // // // // // // //         });
// // // // // // // // //     }

// // // // // // // // //     loadDashboard = async () => {
// // // // // // // // //         // Sites (for selector)
// // // // // // // // //         const sites = await this.orm.searchRead("property.site", [], ["id", "name"]);
// // // // // // // // //         this.state.sites = sites;

// // // // // // // // //         // Build domain from filters
// // // // // // // // //         const domain = [];
// // // // // // // // //         if (this.state.selectedSite) {
// // // // // // // // //             domain.push(["site", "=", parseInt(this.state.selectedSite)]);
// // // // // // // // //         }
// // // // // // // // //         if (this.state.selectedStates && this.state.selectedStates.length) {
// // // // // // // // //             domain.push(["state", "in", this.state.selectedStates]);
// // // // // // // // //         }

// // // // // // // // //         // Fetch props
// // // // // // // // //         const properties = await this.orm.searchRead(
// // // // // // // // //             "property.property",
// // // // // // // // //             domain,
// // // // // // // // //             ["id","name","location","floor_id","state","net_area","gross_area","bedroom","unit_price","site"]
// // // // // // // // //         );

// // // // // // // // //         // Group by floor
// // // // // // // // //         const floorsSet = new Set();
// // // // // // // // //         const propertiesByFloor = {};
// // // // // // // // //         for (const prop of properties) {
// // // // // // // // //             const floorKey = prop.floor_id && prop.floor_id[0];
// // // // // // // // //             if (!floorKey) continue;
// // // // // // // // //             floorsSet.add(floorKey);
// // // // // // // // //             (propertiesByFloor[floorKey] ||= []).push({
// // // // // // // // //                 ...prop,
// // // // // // // // //                 floor_name: prop.floor_id ? prop.floor_id[1] : null,
// // // // // // // // //             });
// // // // // // // // //         }

// // // // // // // // //         // If no properties matched, show empty state by setting floors to []
// // // // // // // // //         this.state.floors = Array.from(floorsSet).sort((a, b) => a - b);
// // // // // // // // //         this.state.propertiesByFloor = propertiesByFloor;
// // // // // // // // //     };

// // // // // // // // //     onSiteFilterChange = async (ev) => {
// // // // // // // // //         this.state.selectedSite = ev.target.value;
// // // // // // // // //         await this.loadDashboard();
// // // // // // // // //     };

// // // // // // // // //     toggleState = async (stateVal) => {
// // // // // // // // //         const i = this.state.selectedStates.indexOf(stateVal);
// // // // // // // // //         if (i === -1) {
// // // // // // // // //             this.state.selectedStates = [...this.state.selectedStates, stateVal];
// // // // // // // // //         } else {
// // // // // // // // //             const next = [...this.state.selectedStates];
// // // // // // // // //             next.splice(i, 1);
// // // // // // // // //             this.state.selectedStates = next;
// // // // // // // // //         }
// // // // // // // // //         await this.loadDashboard();
// // // // // // // // //     };

// // // // // // // // //     openProperty(id) {
// // // // // // // // //         this.action.doAction({
// // // // // // // // //             type: "ir.actions.act_window",
// // // // // // // // //             res_model: "property.property",
// // // // // // // // //             res_id: id,
// // // // // // // // //             views: [[false, "form"]],
// // // // // // // // //             target: "current",
// // // // // // // // //         });
// // // // // // // // //     }
// // // // // // // // // }

// // // // // // // // // PropertyDashboard.template = "property_dashboard.template";
// // // // // // // // // actionRegistry.add("property_dashboard", PropertyDashboard);





// // // // // // // // /** @odoo-module **/

// // // // // // // // import { registry } from "@web/core/registry";
// // // // // // // // import { useService } from "@web/core/utils/hooks";
// // // // // // // // import { Component, onWillStart, useState } from "@odoo/owl";

// // // // // // // // const actionRegistry = registry.category("actions");

// // // // // // // // export class PropertyDashboard extends Component {
// // // // // // // //     setup() {
// // // // // // // //         this.orm = useService("orm");
// // // // // // // //         this.action = useService("action");

// // // // // // // //         this.state = useState({
// // // // // // // //             floors: [],
// // // // // // // //             propertiesByFloor: {},
// // // // // // // //             sites: [],
// // // // // // // //             selectedSite: "",
// // // // // // // //             selectedStates: [], // e.g., ['available','reserved']
// // // // // // // //         });

// // // // // // // //         onWillStart(async () => {
// // // // // // // //             await this.loadDashboard();
// // // // // // // //         });
// // // // // // // //     }

// // // // // // // //     loadDashboard = async () => {
// // // // // // // //         // Sites (for selector)
// // // // // // // //         const sites = await this.orm.searchRead("property.site", [], ["id", "name"]);
// // // // // // // //         this.state.sites = sites;

// // // // // // // //         // Build domain from filters
// // // // // // // //         const domain = [];
// // // // // // // //         if (this.state.selectedSite) {
// // // // // // // //             domain.push(["site", "=", parseInt(this.state.selectedSite)]);
// // // // // // // //         }
// // // // // // // //         if (this.state.selectedStates && this.state.selectedStates.length) {
// // // // // // // //             domain.push(["state", "in", this.state.selectedStates]);
// // // // // // // //         }

// // // // // // // //         // Fetch properties
// // // // // // // //         const properties = await this.orm.searchRead(
// // // // // // // //             "property.property",
// // // // // // // //             domain,
// // // // // // // //             ["id","name","location","floor_id","state","net_area","gross_area","bedroom","unit_price","site"]
// // // // // // // //         );

// // // // // // // //         // Group by floor
// // // // // // // //         const floorsSet = new Set();
// // // // // // // //         const propertiesByFloor = {};
// // // // // // // //         for (const prop of properties) {
// // // // // // // //             const floorKey = prop.floor_id && prop.floor_id[0];
// // // // // // // //             if (!floorKey) continue;
// // // // // // // //             floorsSet.add(floorKey);
// // // // // // // //             (propertiesByFloor[floorKey] ||= []).push({
// // // // // // // //                 ...prop,
// // // // // // // //                 floor_name: prop.floor_id ? prop.floor_id[1] : null,
// // // // // // // //             });
// // // // // // // //         }

// // // // // // // //         this.state.floors = Array.from(floorsSet).sort((a, b) => a - b);
// // // // // // // //         this.state.propertiesByFloor = propertiesByFloor;
// // // // // // // //     };

// // // // // // // //     onSiteFilterChange = async (ev) => {
// // // // // // // //         this.state.selectedSite = ev.target.value;
// // // // // // // //         await this.loadDashboard();
// // // // // // // //     };

// // // // // // // //     toggleState = async (stateVal) => {
// // // // // // // //         const i = this.state.selectedStates.indexOf(stateVal);
// // // // // // // //         if (i === -1) {
// // // // // // // //             this.state.selectedStates = [...this.state.selectedStates, stateVal];
// // // // // // // //         } else {
// // // // // // // //             const next = [...this.state.selectedStates];
// // // // // // // //             next.splice(i, 1);
// // // // // // // //             this.state.selectedStates = next;
// // // // // // // //         }
// // // // // // // //         await this.loadDashboard();
// // // // // // // //     };

// // // // // // // //     clearFilters = async () => {
// // // // // // // //         this.state.selectedSite = "";
// // // // // // // //         this.state.selectedStates = [];
// // // // // // // //         await this.loadDashboard();
// // // // // // // //     };

// // // // // // // //     openProperty(id) {
// // // // // // // //         this.action.doAction({
// // // // // // // //             type: "ir.actions.act_window",
// // // // // // // //             res_model: "property.property",
// // // // // // // //             res_id: id,
// // // // // // // //             views: [[false, "form"]],
// // // // // // // //             target: "current",
// // // // // // // //         });
// // // // // // // //     }
// // // // // // // // }

// // // // // // // // PropertyDashboard.template = "property_dashboard.template";
// // // // // // // // actionRegistry.add("property_dashboard", PropertyDashboard);










// // // // // // // /** @odoo-module **/

// // // // // // // import { registry } from "@web/core/registry";
// // // // // // // import { useService } from "@web/core/utils/hooks";
// // // // // // // import { Component, onWillStart, useState } from "@odoo/owl";

// // // // // // // const actionRegistry = registry.category("actions");

// // // // // // // export class PropertyDashboard extends Component {
// // // // // // //     setup() {
// // // // // // //         this.orm = useService("orm");
// // // // // // //         this.action = useService("action");

// // // // // // //         this.state = useState({
// // // // // // //             floors: [],
// // // // // // //             propertiesByFloor: {},
// // // // // // //             sites: [],
// // // // // // //             selectedSite: "",
// // // // // // //             selectedStates: [],
// // // // // // //             // popover state
// // // // // // //             resvInfo: {},          // { [propId]: { customer, salesperson, wing } }
// // // // // // //             hoverPropId: null,     // show on hover
// // // // // // //             stickyPropId: null,    // toggle on click
// // // // // // //         });

// // // // // // //         onWillStart(async () => {
// // // // // // //             await this.loadDashboard();
// // // // // // //         });
// // // // // // //     }

// // // // // // //     loadDashboard = async () => {
// // // // // // //         // Sites
// // // // // // //         const sites = await this.orm.searchRead("property.site", [], ["id", "name"]);
// // // // // // //         this.state.sites = sites;

// // // // // // //         // Domain
// // // // // // //         const domain = [];
// // // // // // //         if (this.state.selectedSite) {
// // // // // // //             domain.push(["site", "=", parseInt(this.state.selectedSite)]);
// // // // // // //         }
// // // // // // //         if (this.state.selectedStates && this.state.selectedStates.length) {
// // // // // // //             domain.push(["state", "in", this.state.selectedStates]);
// // // // // // //         }

// // // // // // //         const properties = await this.orm.searchRead(
// // // // // // //             "property.property",
// // // // // // //             domain,
// // // // // // //             ["id","name","location","floor_id","state","net_area","gross_area","bedroom","unit_price","site"]
// // // // // // //         );

// // // // // // //         // Group by floor
// // // // // // //         const floorsSet = new Set();
// // // // // // //         const propertiesByFloor = {};
// // // // // // //         for (const prop of properties) {
// // // // // // //             const floorKey = prop.floor_id && prop.floor_id[0];
// // // // // // //             if (!floorKey) continue;
// // // // // // //             floorsSet.add(floorKey);
// // // // // // //             (propertiesByFloor[floorKey] ||= []).push({
// // // // // // //                 ...prop,
// // // // // // //                 floor_name: prop.floor_id ? prop.floor_id[1] : null,
// // // // // // //             });
// // // // // // //         }
// // // // // // //         this.state.floors = Array.from(floorsSet).sort((a, b) => a - b);
// // // // // // //         this.state.propertiesByFloor = propertiesByFloor;

// // // // // // //         // clear transient popovers if data changed significantly
// // // // // // //         if (!this.state.floors.length) {
// // // // // // //             this.state.hoverPropId = null;
// // // // // // //             this.state.stickyPropId = null;
// // // // // // //         }
// // // // // // //     };

// // // // // // //     onSiteFilterChange = async (ev) => {
// // // // // // //         this.state.selectedSite = ev.target.value;
// // // // // // //         await this.loadDashboard();
// // // // // // //     };

// // // // // // //     toggleState = async (stateVal) => {
// // // // // // //         const i = this.state.selectedStates.indexOf(stateVal);
// // // // // // //         if (i === -1) {
// // // // // // //             this.state.selectedStates = [...this.state.selectedStates, stateVal];
// // // // // // //         } else {
// // // // // // //             const next = [...this.state.selectedStates];
// // // // // // //             next.splice(i, 1);
// // // // // // //             this.state.selectedStates = next;
// // // // // // //         }
// // // // // // //         await this.loadDashboard();
// // // // // // //     };

// // // // // // //     clearFilters = async () => {
// // // // // // //         this.state.selectedSite = "";
// // // // // // //         this.state.selectedStates = [];
// // // // // // //         await this.loadDashboard();
// // // // // // //     };

// // // // // // //     // ====== Reserved popover logic ======
// // // // // // //     onCardEnter = async (prop) => {
// // // // // // //         if (prop.state !== "reserved") return;
// // // // // // //         this.state.hoverPropId = prop.id;
// // // // // // //         await this._ensureReservationLoaded(prop.id);
// // // // // // //     };

// // // // // // //     onCardLeave = (prop) => {
// // // // // // //         if (this.state.stickyPropId === prop.id) return; // keep if sticky
// // // // // // //         if (this.state.hoverPropId === prop.id) this.state.hoverPropId = null;
// // // // // // //     };

// // // // // // //     onCardClick = async (prop) => {
// // // // // // //         if (prop.state !== "reserved") {
// // // // // // //             // If not reserved, go open the record like normal
// // // // // // //             return this.openProperty(prop.id);
// // // // // // //         }
// // // // // // //         // Toggle sticky
// // // // // // //         if (this.state.stickyPropId === prop.id) {
// // // // // // //             this.state.stickyPropId = null;
// // // // // // //             // also hide hover if same
// // // // // // //             if (this.state.hoverPropId === prop.id) this.state.hoverPropId = null;
// // // // // // //         } else {
// // // // // // //             this.state.stickyPropId = prop.id;
// // // // // // //             this.state.hoverPropId = prop.id;
// // // // // // //             await this._ensureReservationLoaded(prop.id);
// // // // // // //         }
// // // // // // //     };

// // // // // // //     _ensureReservationLoaded = async (propId) => {
// // // // // // //         if (this.state.resvInfo[propId]) return;
// // // // // // //         // Fetch latest/current reservation for this property in 'reserved' status
// // // // // // //         const resv = await this.orm.searchRead(
// // // // // // //             "property.reservation",
// // // // // // //             [["property_id","=", propId], ["status","=", "reserved"]],
// // // // // // //             ["id","partner_id","salesperson_ids","wing_id","create_date"],
// // // // // // //             { limit: 1, order: "create_date desc" }
// // // // // // //         );
// // // // // // //         const rec = resv && resv[0];
// // // // // // //         const info = {
// // // // // // //             customer: rec?.partner_id ? rec.partner_id[1] : "",
// // // // // // //             salesperson: rec?.salesperson_ids ? (Array.isArray(rec.salesperson_ids) ? rec.salesperson_ids[1] : rec.salesperson_ids[1]) : "",
// // // // // // //             wing: rec?.wing_id ? rec.wing_id[1] : "",
// // // // // // //         };
// // // // // // //         this.state.resvInfo = { ...this.state.resvInfo, [propId]: info };
// // // // // // //     };

// // // // // // //     openProperty(id) {
// // // // // // //         this.action.doAction({
// // // // // // //             type: "ir.actions.act_window",
// // // // // // //             res_model: "property.property",
// // // // // // //             res_id: id,
// // // // // // //             views: [[false, "form"]],
// // // // // // //             target: "current",
// // // // // // //         });
// // // // // // //     }
// // // // // // // }

// // // // // // // PropertyDashboard.template = "property_dashboard.template";
// // // // // // // actionRegistry.add("property_dashboard", PropertyDashboard);





// // // // // // /** @odoo-module **/

// // // // // // import { registry } from "@web/core/registry";
// // // // // // import { useService } from "@web/core/utils/hooks";
// // // // // // import { Component, onWillStart, useState } from "@odoo/owl";

// // // // // // const actionRegistry = registry.category("actions");

// // // // // // export class PropertyDashboard extends Component {
// // // // // //     setup() {
// // // // // //         this.orm = useService("orm");
// // // // // //         this.action = useService("action");

// // // // // //         this.state = useState({
// // // // // //             floors: [],
// // // // // //             propertiesByFloor: {},
// // // // // //             sites: [],
// // // // // //             selectedSite: "",
// // // // // //             selectedStates: [],
// // // // // //             // floating popover
// // // // // //             pop: { visible:false, sticky:false, kind:null, propId:null, x:0, y:0, info:{} },
// // // // // //             cache: {}, // { `${propId}:${kind}`: info }
// // // // // //         });

// // // // // //         onWillStart(async () => {
// // // // // //             await this.loadDashboard();
// // // // // //         });
// // // // // //     }

// // // // // //     // ---------- DATA ----------
// // // // // //     loadDashboard = async () => {
// // // // // //         const sites = await this.orm.searchRead("property.site", [], ["id", "name"]);
// // // // // //         this.state.sites = sites;

// // // // // //         const domain = [];
// // // // // //         if (this.state.selectedSite) domain.push(["site", "=", parseInt(this.state.selectedSite)]);
// // // // // //         if (this.state.selectedStates.length) domain.push(["state", "in", this.state.selectedStates]);

// // // // // //         const properties = await this.orm.searchRead(
// // // // // //             "property.property",
// // // // // //             domain,
// // // // // //             ["id","name","location","floor_id","state","net_area","gross_area","bedroom","unit_price","site"]
// // // // // //         );

// // // // // //         const floorsSet = new Set();
// // // // // //         const propertiesByFloor = {};
// // // // // //         for (const p of properties) {
// // // // // //             const fk = p.floor_id && p.floor_id[0];
// // // // // //             if (!fk) continue;
// // // // // //             floorsSet.add(fk);
// // // // // //             (propertiesByFloor[fk] ||= []).push({ ...p, floor_name: p.floor_id ? p.floor_id[1] : null });
// // // // // //         }
// // // // // //         this.state.floors = Array.from(floorsSet).sort((a,b)=>a-b);
// // // // // //         this.state.propertiesByFloor = propertiesByFloor;

// // // // // //         if (!this.state.floors.length) this.hidePopup();
// // // // // //     };

// // // // // //     // ---------- FILTERS ----------
// // // // // //     onSiteFilterChange = async (ev) => {
// // // // // //         this.state.selectedSite = ev.target.value;
// // // // // //         await this.loadDashboard();
// // // // // //     };
// // // // // //     toggleState = async (stateVal) => {
// // // // // //         const i = this.state.selectedStates.indexOf(stateVal);
// // // // // //         if (i === -1) this.state.selectedStates = [...this.state.selectedStates, stateVal];
// // // // // //         else {
// // // // // //             const next = [...this.state.selectedStates]; next.splice(i,1); this.state.selectedStates = next;
// // // // // //         }
// // // // // //         await this.loadDashboard();
// // // // // //     };
// // // // // //     clearFilters = async () => {
// // // // // //         this.state.selectedSite = ""; this.state.selectedStates = [];
// // // // // //         await this.loadDashboard();
// // // // // //     };

// // // // // //     // ---------- POPOVER UX ----------
// // // // // //     onCardEnter = async (ev, prop) => {
// // // // // //         if (prop.state !== "reserved" && prop.state !== "sold") return;
// // // // // //         if (this.state.pop.sticky && this.state.pop.propId === prop.id) return; // leave pinned
// // // // // //         await this.showPopupFor(ev.currentTarget, prop);
// // // // // //     };
// // // // // //     onCardLeave = (ev, prop) => {
// // // // // //         if (this.state.pop.sticky && this.state.pop.propId === prop.id) return;
// // // // // //         this.hidePopup();
// // // // // //     };
// // // // // //     onCardClick = async (ev, prop) => {
// // // // // //         if (prop.state !== "reserved" && prop.state !== "sold") {
// // // // // //             return this.openProperty(prop.id);
// // // // // //         }
// // // // // //         // toggle pin
// // // // // //         if (this.state.pop.sticky && this.state.pop.propId === prop.id) {
// // // // // //             this.hidePopup();
// // // // // //             return;
// // // // // //         }
// // // // // //         await this.showPopupFor(ev.currentTarget, prop, true);
// // // // // //     };

// // // // // //     showPopupFor = async (anchorEl, prop, sticky=false) => {
// // // // // //         const rect = anchorEl.getBoundingClientRect();
// // // // // //         // anchor X/Y at the top-center of the card; the popup itself draws above with CSS arrow
// // // // // //         const x = rect.left + rect.width/2;
// // // // // //         const y = rect.top - 12; // a bit above the card; CSS arrow fills the gap

// // // // // //         const kind = prop.state; // 'reserved' or 'sold'
// // // // // //         const key = `${prop.id}:${kind}`;
// // // // // //         let info = this.state.cache[key];
// // // // // //         if (!info) {
// // // // // //             // Fetch latest reservation for this prop with status = kind
// // // // // //             const res = await this.orm.searchRead(
// // // // // //                 "property.reservation",
// // // // // //                 [["property_id","=", prop.id], ["status","=", kind]],
// // // // // //                 ["id","partner_id","salesperson_ids","wing_id","create_date"],
// // // // // //                 { limit: 1, order: "create_date desc" }
// // // // // //             );
// // // // // //             const rec = res && res[0];
// // // // // //             info = {
// // // // // //                 customer: rec?.partner_id ? rec.partner_id[1] : "",
// // // // // //                 salesperson: rec?.salesperson_ids ? rec.salesperson_ids[1] : "",
// // // // // //                 wing: rec?.wing_id ? rec.wing_id[1] : "",
// // // // // //             };
// // // // // //             this.state.cache[key] = info;
// // // // // //         }

// // // // // //         this.state.pop = { visible:true, sticky, kind, propId:prop.id, x, y, info };
// // // // // //     };

// // // // // //     hidePopup = () => {
// // // // // //         if (this.state.pop.sticky) return; // don't auto-hide pinned
// // // // // //         this.state.pop = { visible:false, sticky:false, kind:null, propId:null, x:0, y:0, info:{} };
// // // // // //     };
// // // // // //     closePopup = () => {
// // // // // //         this.state.pop = { visible:false, sticky:false, kind:null, propId:null, x:0, y:0, info:{} };
// // // // // //     };

// // // // // //     openProperty(id) {
// // // // // //         this.action.doAction({
// // // // // //             type: "ir.actions.act_window",
// // // // // //             res_model: "property.property",
// // // // // //             res_id: id,
// // // // // //             views: [[false, "form"]],
// // // // // //             target: "current",
// // // // // //         });
// // // // // //     }
// // // // // // }

// // // // // // PropertyDashboard.template = "property_dashboard.template";
// // // // // // actionRegistry.add("property_dashboard", PropertyDashboard);




// // // // // /** @odoo-module **/

// // // // // import { registry } from "@web/core/registry";
// // // // // import { useService } from "@web/core/utils/hooks";
// // // // // import { Component, onWillStart, useState } from "@odoo/owl";

// // // // // const actionRegistry = registry.category("actions");

// // // // // export class PropertyDashboard extends Component {
// // // // //     setup() {
// // // // //         this.orm = useService("orm");
// // // // //         this.action = useService("action");

// // // // //         this.state = useState({
// // // // //             floors: [],
// // // // //             propertiesByFloor: {},
// // // // //             sites: [],
// // // // //             selectedSite: "",
// // // // //             selectedStates: [],
// // // // //             // floating popover
// // // // //             pop: { visible:false, sticky:false, kind:null, propId:null, x:0, y:0, info:{} },
// // // // //             cache: {}, // { `${propId}:${kind}`: info }
// // // // //             hoverTimerId: null, // to debounce reserved hover
// // // // //         });

// // // // //         onWillStart(async () => {
// // // // //             await this.loadDashboard();
// // // // //         });
// // // // //     }

// // // // //     // ---------- DATA ----------
// // // // //     loadDashboard = async () => {
// // // // //         const sites = await this.orm.searchRead("property.site", [], ["id", "name"]);
// // // // //         this.state.sites = sites;

// // // // //         const domain = [];
// // // // //         if (this.state.selectedSite) domain.push(["site", "=", parseInt(this.state.selectedSite)]);
// // // // //         if (this.state.selectedStates.length) domain.push(["state", "in", this.state.selectedStates]);

// // // // //         const properties = await this.orm.searchRead(
// // // // //             "property.property",
// // // // //             domain,
// // // // //             ["id","name","location","floor_id","state","net_area","gross_area","bedroom","unit_price","site"]
// // // // //         );

// // // // //         const floorsSet = new Set();
// // // // //         const propertiesByFloor = {};
// // // // //         for (const p of properties) {
// // // // //             const fk = p.floor_id && p.floor_id[0];
// // // // //             if (!fk) continue;
// // // // //             floorsSet.add(fk);
// // // // //             (propertiesByFloor[fk] ||= []).push({ ...p, floor_name: p.floor_id ? p.floor_id[1] : null });
// // // // //         }
// // // // //         this.state.floors = Array.from(floorsSet).sort((a,b)=>a-b);
// // // // //         this.state.propertiesByFloor = propertiesByFloor;

// // // // //         if (!this.state.floors.length) this.hidePopup(true);
// // // // //     };

// // // // //     // ---------- FILTERS ----------
// // // // //     onSiteFilterChange = async (ev) => {
// // // // //         this.state.selectedSite = ev.target.value;
// // // // //         await this.loadDashboard();
// // // // //     };

// // // // //     toggleState = async (stateVal) => {
// // // // //         const i = this.state.selectedStates.indexOf(stateVal);
// // // // //         if (i === -1) this.state.selectedStates = [...this.state.selectedStates, stateVal];
// // // // //         else {
// // // // //             const next = [...this.state.selectedStates];
// // // // //             next.splice(i,1);
// // // // //             this.state.selectedStates = next;
// // // // //         }
// // // // //         await this.loadDashboard();
// // // // //     };

// // // // //     clearFilters = async () => {
// // // // //         this.state.selectedSite = "";
// // // // //         this.state.selectedStates = [];
// // // // //         await this.loadDashboard();
// // // // //     };

// // // // //     // ---------- POPOVER UX ----------
// // // // //     // HOVER: only for RESERVED (with small delay)
// // // // //     onCardEnter = async (ev, prop) => {
// // // // //         if (prop.state !== "reserved") return; // no hover for sold/others
// // // // //         if (this.state.pop.sticky && this.state.pop.propId === prop.id) return; // keep pinned
// // // // //         // debounce hover to reduce “noise” while browsing
// // // // //         clearTimeout(this.state.hoverTimerId);
// // // // //         this.state.hoverTimerId = setTimeout(() => {
// // // // //             this.showPopupFor(ev.currentTarget, prop, false);
// // // // //         }, 200);
// // // // //     };

// // // // //     onCardLeave = (ev, prop) => {
// // // // //         clearTimeout(this.state.hoverTimerId);
// // // // //         // don’t hide if this card is pinned
// // // // //         if (this.state.pop.sticky && this.state.pop.propId === prop.id) return;
// // // // //         this.hidePopup();
// // // // //     };

// // // // //     // CLICK:
// // // // //     // - RESERVED: click pins/unpins the hover popup
// // // // //     // - SOLD: click shows/pins the popup (there is NO hover for sold)
// // // // //     // - OTHERS: open record
// // // // //     onCardClick = async (ev, prop) => {
// // // // //         if (prop.state === "reserved" || prop.state === "sold") {
// // // // //             // toggle if same card already pinned
// // // // //             if (this.state.pop.sticky && this.state.pop.propId === prop.id) {
// // // // //                 this.closePopup();
// // // // //                 return;
// // // // //             }
// // // // //             await this.showPopupFor(ev.currentTarget, prop, true);
// // // // //             return;
// // // // //         }
// // // // //         // default behavior for available/draft
// // // // //         return this.openProperty(prop.id);
// // // // //     };

// // // // //     showPopupFor = async (anchorEl, prop, sticky=false) => {
// // // // //         const rect = anchorEl.getBoundingClientRect();
// // // // //         // position above the card, centered horizontally
// // // // //         const x = rect.left + rect.width/2;
// // // // //         const y = rect.top - 12;

// // // // //         const kind = prop.state; // 'reserved' or 'sold'
// // // // //         const key = `${prop.id}:${kind}`;
// // // // //         let info = this.state.cache[key];
// // // // //         if (!info) {
// // // // //             // Fetch latest reservation with this status for the property
// // // // //             const res = await this.orm.searchRead(
// // // // //                 "property.reservation",
// // // // //                 [["property_id","=", prop.id], ["status","=", kind]],
// // // // //                 ["id","partner_id","salesperson_ids","wing_id","create_date"],
// // // // //                 { limit: 1, order: "create_date desc" }
// // // // //             );
// // // // //             const rec = res && res[0];
// // // // //             info = {
// // // // //                 customer: rec?.partner_id ? rec.partner_id[1] : "",
// // // // //                 // if salesperson_ids is M2M, this grabs the display name (index 1)
// // // // //                 salesperson: rec?.salesperson_ids ? rec.salesperson_ids[1] : "",
// // // // //                 wing: rec?.wing_id ? rec.wing_id[1] : "",
// // // // //             };
// // // // //             this.state.cache[key] = info;
// // // // //         }

// // // // //         this.state.pop = { visible:true, sticky, kind, propId:prop.id, x, y, info };
// // // // //     };

// // // // //     hidePopup = (force=false) => {
// // // // //         if (!force && this.state.pop.sticky) return; // don’t auto-hide pinned
// // // // //         this.state.pop = { visible:false, sticky:false, kind:null, propId:null, x:0, y:0, info:{} };
// // // // //     };

// // // // //     closePopup = () => {
// // // // //         this.state.pop = { visible:false, sticky:false, kind:null, propId:null, x:0, y:0, info:{} };
// // // // //     };

// // // // //     openProperty(id) {
// // // // //         this.action.doAction({
// // // // //             type: "ir.actions.act_window",
// // // // //             res_model: "property.property",
// // // // //             res_id: id,
// // // // //             views: [[false, "form"]],
// // // // //             target: "current",
// // // // //         });
// // // // //     }
// // // // // }

// // // // // PropertyDashboard.template = "property_dashboard.template";
// // // // // actionRegistry.add("property_dashboard", PropertyDashboard);







// // // // /** @odoo-module **/

// // // // import { registry } from "@web/core/registry";
// // // // import { useService } from "@web/core/utils/hooks";
// // // // import { Component, onWillStart, useState } from "@odoo/owl";

// // // // const actionRegistry = registry.category("actions");

// // // // export class PropertyDashboard extends Component {
// // // //     setup() {
// // // //         this.orm = useService("orm");
// // // //         this.action = useService("action");

// // // //         this.state = useState({
// // // //             floors: [],
// // // //             propertiesByFloor: {},
// // // //             sites: [],
// // // //             selectedSite: "",
// // // //             selectedStates: [],
// // // //             // floating popover state
// // // //             pop: { visible:false, sticky:false, kind:null, propId:null, x:0, y:0, info:{} },
// // // //             cache: {}, // { `${propId}:${kind}`: info }
// // // //             hoverTimerId: null,
// // // //         });

// // // //         onWillStart(async () => {
// // // //             await this.loadDashboard();
// // // //         });

// // // //         // optional: auto-hide unpinned popup on scroll/resize
// // // //         window.addEventListener('scroll', () => this.hidePopup(false), { passive:true });
// // // //         window.addEventListener('resize', () => this.hidePopup(false), { passive:true });
// // // //     }

// // // //     /* ---------- Format helpers ---------- */
// // // //     formatNumber = (val) => {
// // // //         if (val === undefined || val === null || val === '') return '-';
// // // //         const num = Number(val);
// // // //         if (Number.isNaN(num)) return String(val);
// // // //         return new Intl.NumberFormat().format(num);
// // // //     };
// // // //     formatInt = (val) => (val || val === 0) ? this.formatNumber(parseInt(val)) : '-';
// // // //     formatArea = (val) => {
// // // //         if (val === undefined || val === null || val === '') return '-';
// // // //         const num = Number(val);
// // // //         if (Number.isNaN(num)) return '-';
// // // //         return `${new Intl.NumberFormat().format(num)} m<sup>2</sup>`;
// // // //     };
// // // //     formatDateTime = (dt) => {
// // // //         if (!dt) return '—';
// // // //         try { return new Date(dt).toLocaleString(); } catch { return String(dt); }
// // // //     };

// // // //     /* ---------- Data ---------- */
// // // //     loadDashboard = async () => {
// // // //         const sites = await this.orm.searchRead("property.site", [], ["id", "name"]);
// // // //         this.state.sites = sites;

// // // //         const domain = [];
// // // //         if (this.state.selectedSite) domain.push(["site", "=", parseInt(this.state.selectedSite)]);
// // // //         if (this.state.selectedStates.length) domain.push(["state", "in", this.state.selectedStates]);

// // // //         const properties = await this.orm.searchRead(
// // // //             "property.property",
// // // //             domain,
// // // //             ["id","name","location","floor_id","state","net_area","gross_area","bedroom","unit_price","site"]
// // // //         );

// // // //         const floorsSet = new Set();
// // // //         const propertiesByFloor = {};
// // // //         for (const p of properties) {
// // // //             const fk = p.floor_id && p.floor_id[0];
// // // //             if (!fk) continue;
// // // //             floorsSet.add(fk);
// // // //             (propertiesByFloor[fk] ||= []).push({ ...p, floor_name: p.floor_id ? p.floor_id[1] : null });
// // // //         }
// // // //         this.state.floors = Array.from(floorsSet).sort((a,b)=>a-b);
// // // //         this.state.propertiesByFloor = propertiesByFloor;

// // // //         if (!this.state.floors.length) this.hidePopup(true);
// // // //     };

// // // //     /* ---------- Filters ---------- */
// // // //     onSiteFilterChange = async (ev) => {
// // // //         this.state.selectedSite = ev.target.value;
// // // //         await this.loadDashboard();
// // // //     };
// // // //     toggleState = async (stateVal) => {
// // // //         const i = this.state.selectedStates.indexOf(stateVal);
// // // //         if (i === -1) this.state.selectedStates = [...this.state.selectedStates, stateVal];
// // // //         else { const next = [...this.state.selectedStates]; next.splice(i,1); this.state.selectedStates = next; }
// // // //         await this.loadDashboard();
// // // //     };
// // // //     clearFilters = async () => {
// // // //         this.state.selectedSite = ""; this.state.selectedStates = [];
// // // //         await this.loadDashboard();
// // // //     };

// // // //     /* ---------- Popover UX ---------- */
// // // //     // Reserved: hover (debounced) + click to pin
// // // //     onCardEnter = (ev, prop) => {
// // // //         if (prop.state !== "reserved") return;
// // // //         if (this.state.pop.sticky && this.state.pop.propId === prop.id) return;
// // // //         const el = ev.currentTarget; // capture now
// // // //         clearTimeout(this.state.hoverTimerId);
// // // //         this.state.hoverTimerId = setTimeout(() => {
// // // //             const anchor = (el && el.isConnected) ? el
// // // //               : document.querySelector(`.tp-card[data-prop-id="${prop.id}"]`);
// // // //             if (!anchor) return;
// // // //             this.showPopupFor(anchor, prop, false);
// // // //         }, 200);
// // // //     };
// // // //     onCardLeave = (ev, prop) => {
// // // //         clearTimeout(this.state.hoverTimerId);
// // // //         if (this.state.pop.sticky && this.state.pop.propId === prop.id) return;
// // // //         this.hidePopup();
// // // //     };

// // // //     // Sold: click only; Reserved: click pins/unpins
// // // //     onCardClick = async (ev, prop) => {
// // // //         if (prop.state === "reserved" || prop.state === "sold") {
// // // //             if (this.state.pop.sticky && this.state.pop.propId === prop.id) { this.closePopup(); return; }
// // // //             const el = ev.currentTarget;
// // // //             const anchor = (el && el.isConnected) ? el
// // // //               : document.querySelector(`.tp-card[data-prop-id="${prop.id}"]`);
// // // //             if (!anchor) return;
// // // //             await this.showPopupFor(anchor, prop, true);
// // // //             return;
// // // //         }
// // // //         return this.openProperty(prop.id);
// // // //     };

// // // //     showPopupFor = async (anchorEl, prop, sticky=false) => {
// // // //         if (!anchorEl || !anchorEl.getBoundingClientRect) return;
// // // //         const rect = anchorEl.getBoundingClientRect();
// // // //         const x = rect.left + rect.width/2;
// // // //         const y = rect.top - 12;

// // // //         const kind = prop.state; // 'reserved' or 'sold'
// // // //         const key = `${prop.id}:${kind}`;
// // // //         let info = this.state.cache[key];

// // // //         if (!info) {
// // // //             // For reserved, include reservation_type_id, expire_date, payment_diff
// // // //             const fields = ["id","partner_id","salesperson_ids","wing_id","create_date"];
// // // //             if (kind === "reserved") { fields.push("reservation_type_id","expire_date","payment_diff"); }

// // // //             const res = await this.orm.searchRead(
// // // //                 "property.reservation",
// // // //                 [["property_id","=", prop.id], ["status","=", kind]],
// // // //                 fields,
// // // //                 { limit: 1, order: "create_date desc" }
// // // //             );
// // // //             const rec = res && res[0];
// // // //             info = {
// // // //                 customer: rec?.partner_id ? rec.partner_id[1] : "",
// // // //                 salesperson: rec?.salesperson_ids ? rec.salesperson_ids[1] : "",
// // // //                 wing: rec?.wing_id ? rec.wing_id[1] : "",
// // // //                 reservation_type: rec?.reservation_type_id ? rec.reservation_type_id[1] : "",
// // // //                 expire_date: rec?.expire_date || null,
// // // //                 payment_diff: rec?.payment_diff ?? null,
// // // //             };
// // // //             this.state.cache[key] = info;
// // // //         }

// // // //         this.state.pop = { visible:true, sticky, kind, propId:prop.id, x, y, info };
// // // //     };

// // // //     hidePopup = (force=false) => {
// // // //         if (!force && this.state.pop.sticky) return;
// // // //         this.state.pop = { visible:false, sticky:false, kind:null, propId:null, x:0, y:0, info:{} };
// // // //     };
// // // //     closePopup = () => {
// // // //         this.state.pop = { visible:false, sticky:false, kind:null, propId:null, x:0, y:0, info:{} };
// // // //     };

// // // //     openProperty(id) {
// // // //         this.action.doAction({
// // // //             type: "ir.actions.act_window",
// // // //             res_model: "property.property",
// // // //             res_id: id,
// // // //             views: [[false, "form"]],
// // // //             target: "current",
// // // //         });
// // // //     }
// // // // }

// // // // PropertyDashboard.template = "property_dashboard.template";
// // // // actionRegistry.add("property_dashboard", PropertyDashboard);






// // // /** @odoo-module **/

// // // import { registry } from "@web/core/registry";
// // // import { useService } from "@web/core/utils/hooks";
// // // import { Component, onWillStart, useState } from "@odoo/owl";

// // // const actionRegistry = registry.category("actions");

// // // // Popup geometry
// // // const POP_MIN_W = 340;
// // // const POP_MAX_W = 460;
// // // const POP_MARGIN = 8;     // viewport edge margin
// // // const ARROW_GAP  = 12;    // gap from anchor to popup

// // // export class PropertyDashboard extends Component {
// // //     setup() {
// // //         this.orm = useService("orm");
// // //         this.action = useService("action");

// // //         this.state = useState({
// // //             floors: [],
// // //             propertiesByFloor: {},
// // //             sites: [],
// // //             selectedSite: "",
// // //             selectedStates: [],
// // //             // popup state (clamped)
// // //             pop: {
// // //                 visible:false, sticky:false, kind:null, propId:null,
// // //                 left:0, top:0, arrowX:0, placement:'above',
// // //                 info:{},
// // //             },
// // //             cache: {},      // cache reservation info
// // //             hoverTimerId: null,
// // //         });

// // //         onWillStart(async () => {
// // //             await this.loadDashboard();
// // //         });

// // //         // Hide unpinned popup on scroll/resize
// // //         window.addEventListener('scroll', () => this.hidePopup(false), { passive:true });
// // //         window.addEventListener('resize', () => this.hidePopup(false), { passive:true });
// // //     }

// // //     /* ---------- Format helpers ---------- */
// // //     formatNumber = (val) => {
// // //         if (val === undefined || val === null || val === '') return '-';
// // //         const num = Number(val);
// // //         if (Number.isNaN(num)) return String(val);
// // //         return new Intl.NumberFormat().format(num);
// // //     };
// // //     formatInt = (val) => (val || val === 0) ? this.formatNumber(parseInt(val)) : '-';
// // //     formatArea = (val) => {
// // //         if (val === undefined || val === null || val === '') return '-';
// // //         const num = Number(val);
// // //         if (Number.isNaN(num)) return '-';
// // //         return `${new Intl.NumberFormat().format(num)} m²`;
// // //     };
// // //     formatDateTime = (dt) => {
// // //         if (!dt) return '—';
// // //         try { return new Date(dt).toLocaleString(); } catch { return String(dt); }
// // //     };

// // //     /* ---------- Data ---------- */
// // //     loadDashboard = async () => {
// // //         const sites = await this.orm.searchRead("property.site", [], ["id", "name"]);
// // //         this.state.sites = sites;

// // //         const domain = [];
// // //         if (this.state.selectedSite) domain.push(["site", "=", parseInt(this.state.selectedSite)]);
// // //         if (this.state.selectedStates.length) domain.push(["state", "in", this.state.selectedStates]);

// // //         const properties = await this.orm.searchRead(
// // //             "property.property",
// // //             domain,
// // //             ["id","name","location","floor_id","state","net_area","gross_area","bedroom","unit_price","site"]
// // //         );

// // //         const floorsSet = new Set();
// // //         const propertiesByFloor = {};
// // //         for (const p of properties) {
// // //             const fk = p.floor_id && p.floor_id[0];
// // //             if (!fk) continue;
// // //             floorsSet.add(fk);
// // //             (propertiesByFloor[fk] ||= []).push({ ...p, floor_name: p.floor_id ? p.floor_id[1] : null });
// // //         }
// // //         this.state.floors = Array.from(floorsSet).sort((a,b)=>a-b);
// // //         this.state.propertiesByFloor = propertiesByFloor;

// // //         if (!this.state.floors.length) this.hidePopup(true);
// // //     };

// // //     /* ---------- Filters ---------- */
// // //     onSiteFilterChange = async (ev) => {
// // //         this.state.selectedSite = ev.target.value;
// // //         await this.loadDashboard();
// // //     };
// // //     toggleState = async (stateVal) => {
// // //         const i = this.state.selectedStates.indexOf(stateVal);
// // //         if (i === -1) this.state.selectedStates = [...this.state.selectedStates, stateVal];
// // //         else { const next = [...this.state.selectedStates]; next.splice(i,1); this.state.selectedStates = next; }
// // //         await this.loadDashboard();
// // //     };
// // //     clearFilters = async () => {
// // //         this.state.selectedSite = ""; this.state.selectedStates = [];
// // //         await this.loadDashboard();
// // //     };

// // //     /* ---------- Popover UX ---------- */
// // //     // Reserved: hover (1.5s delay) + click to pin
// // //     onCardEnter = (ev, prop) => {
// // //         if (prop.state !== "reserved") return;
// // //         if (this.state.pop.sticky && this.state.pop.propId === prop.id) return;
// // //         const el = ev.currentTarget;
// // //         clearTimeout(this.state.hoverTimerId);
// // //         this.state.hoverTimerId = setTimeout(() => {
// // //             const anchor = (el && el.isConnected) ? el
// // //               : document.querySelector(`.tp-card[data-prop-id="${prop.id}"]`);
// // //             if (!anchor) return;
// // //             this.showPopupFor(anchor, prop, false);
// // //         }, 1500);
// // //     };
// // //     onCardLeave = (ev, prop) => {
// // //         clearTimeout(this.state.hoverTimerId);
// // //         if (this.state.pop.sticky && this.state.pop.propId === prop.id) return;
// // //         this.hidePopup();
// // //     };

// // //     // Sold: click only; Reserved: click pins/unpins
// // //     onCardClick = async (ev, prop) => {
// // //         if (prop.state === "reserved" || prop.state === "sold") {
// // //             if (this.state.pop.sticky && this.state.pop.propId === prop.id) { this.closePopup(); return; }
// // //             const el = ev.currentTarget;
// // //             const anchor = (el && el.isConnected) ? el
// // //               : document.querySelector(`.tp-card[data-prop-id="${prop.id}"]`);
// // //             if (!anchor) return;
// // //             await this.showPopupFor(anchor, prop, true);
// // //             return;
// // //         }
// // //         return this.openProperty(prop.id);
// // //     };

// // //     async showPopupFor(anchorEl, prop, sticky=false) {
// // //         if (!anchorEl || !anchorEl.getBoundingClientRect) return;

// // //         const rect = anchorEl.getBoundingClientRect();
// // //         const anchorMidX = rect.left + rect.width/2;
// // //         const anchorTop  = rect.top;
// // //         const anchorBot  = rect.bottom;

// // //         const kind = prop.state; // 'reserved' or 'sold'
// // //         const key = `${prop.id}:${kind}`;
// // //         let info = this.state.cache[key];

// // //         if (!info) {
// // //             const fields = ["id","partner_id","salesperson_ids","wing_id","create_date"];
// // //             if (kind === "reserved") fields.push("reservation_type_id","expire_date","payment_diff");

// // //             const res = await this.orm.searchRead(
// // //                 "property.reservation",
// // //                 [["property_id","=", prop.id], ["status","=", kind]],
// // //                 fields,
// // //                 { limit: 1, order: "create_date desc" }
// // //             );
// // //             const rec = res && res[0];
// // //             info = {
// // //                 customer: rec?.partner_id ? rec.partner_id[1] : "",
// // //                 salesperson: rec?.salesperson_ids ? rec.salesperson_ids[1] : "",
// // //                 wing: rec?.wing_id ? rec.wing_id[1] : "",
// // //                 reservation_type: rec?.reservation_type_id ? rec.reservation_type_id[1] : "",
// // //                 expire_date: rec?.expire_date || null,
// // //                 payment_diff: rec?.payment_diff ?? null,
// // //             };
// // //             this.state.cache[key] = info;
// // //         }

// // //         // Provisional placement (above)
// // //         this.state.pop = {
// // //             visible:true, sticky, kind, propId:prop.id,
// // //             left: Math.max(POP_MARGIN, anchorMidX - POP_MAX_W/2),
// // //             top:  Math.max(POP_MARGIN, anchorTop - 260),
// // //             arrowX: 0, placement: 'above', info,
// // //         };

// // //         // Next frame: measure and clamp
// // //         await new Promise(requestAnimationFrame);
// // //         const popEl = document.querySelector('.pop-card');
// // //         if (!popEl) return;

// // //         const popW = Math.min(Math.max(popEl.offsetWidth || POP_MIN_W, POP_MIN_W), POP_MAX_W);
// // //         const popH = popEl.offsetHeight || 220;
// // //         const vw = window.innerWidth;
// // //         const vh = window.innerHeight;

// // //         // Above/below flip to keep on-screen vertically
// // //         let placement = 'above';
// // //         let top = anchorTop - popH - ARROW_GAP;
// // //         if (top < POP_MARGIN) {
// // //             placement = 'below';
// // //             top = Math.min(vh - popH - POP_MARGIN, anchorBot + ARROW_GAP);
// // //         }

// // //         // Clamp horizontally
// // //         let left = anchorMidX - popW / 2;
// // //         left = Math.max(POP_MARGIN, Math.min(left, vw - popW - POP_MARGIN));

// // //         // Arrow position relative to popup
// // //         let arrowX = anchorMidX - left;
// // //         arrowX = Math.max(12, Math.min(arrowX, popW - 12));

// // //         this.state.pop = {
// // //             ...this.state.pop,
// // //             left, top, arrowX, placement,
// // //         };
// // //     }

// // //     hidePopup(force=false) {
// // //         if (!force && this.state.pop.sticky) return;
// // //         this.state.pop = {
// // //             visible:false, sticky:false, kind:null, propId:null,
// // //             left:0, top:0, arrowX:0, placement:'above', info:{},
// // //         };
// // //     }
// // //     closePopup = () => this.hidePopup(true);

// // //     openProperty(id) {
// // //         this.action.doAction({
// // //             type: "ir.actions.act_window",
// // //             res_model: "property.property",
// // //             res_id: id,
// // //             views: [[false, "form"]],
// // //             target: "current",
// // //         });
// // //     }
// // // }

// // // PropertyDashboard.template = "property_dashboard.template";
// // // actionRegistry.add("property_dashboard", PropertyDashboard);

















// // /** @odoo-module **/

// // import { registry } from "@web/core/registry";
// // import { useService } from "@web/core/utils/hooks";
// // import { Component, onWillStart, useState } from "@odoo/owl";

// // const actionRegistry = registry.category("actions");

// // const POP_MIN_W = 340;
// // const POP_MAX_W = 460;
// // const POP_MARGIN = 8;
// // const ARROW_GAP  = 12;

// // export class PropertyDashboard extends Component {
// //     setup() {
// //         this.orm = useService("orm");
// //         this.action = useService("action");

// //         this.state = useState({
// //             floors: [],
// //             propertiesByFloor: {},
// //             sites: [],
// //             selectedSite: "",
// //             selectedStates: [],
// //             pop: { visible:false, sticky:false, kind:null, propId:null, left:0, top:0, arrowX:0, placement:'above', info:{} },
// //             cache: {},
// //             hoverTimerId: null,
// //         });

// //         onWillStart(async () => { await this.loadDashboard(); });

// //         window.addEventListener('scroll', () => this.hidePopup(false), { passive:true });
// //         window.addEventListener('resize', () => this.hidePopup(false), { passive:true });
// //     }

// //     /* ------- formatters ------- */
// //     formatNumber = (val) => {
// //         if (val === undefined || val === null || val === '') return '-';
// //         const num = Number(val);
// //         if (Number.isNaN(num)) return String(val);
// //         return new Intl.NumberFormat().format(num);
// //     };
// //     formatInt = (val) => (val || val === 0) ? this.formatNumber(parseInt(val)) : '-';
// //     formatArea = (val) => {
// //         if (val === undefined || val === null || val === '') return '-';
// //         const num = Number(val);
// //         if (Number.isNaN(num)) return '-';
// //         return `${new Intl.NumberFormat().format(num)} m²`;
// //     };
// //     formatDateTime = (dt) => {
// //         if (!dt) return '—';
// //         try { return new Date(dt).toLocaleString(); } catch { return String(dt); }
// //     };

// //     /* ------- data ------- */
// //     loadDashboard = async () => {
// //         const sites = await this.orm.searchRead("property.site", [], ["id", "name"]);
// //         this.state.sites = sites;

// //         const domain = [];
// //         if (this.state.selectedSite) domain.push(["site", "=", parseInt(this.state.selectedSite)]);
// //         if (this.state.selectedStates.length) domain.push(["state", "in", this.state.selectedStates]);

// //         const properties = await this.orm.searchRead(
// //             "property.property",
// //             domain,
// //             ["id","name","location","floor_id","state","net_area","gross_area","bedroom","unit_price","site"]
// //         );

// //         const floorsSet = new Set();
// //         const propertiesByFloor = {};
// //         for (const p of properties) {
// //             const fk = p.floor_id && p.floor_id[0];
// //             if (!fk) continue;
// //             floorsSet.add(fk);
// //             (propertiesByFloor[fk] ||= []).push({ ...p, floor_name: p.floor_id ? p.floor_id[1] : null });
// //         }
// //         this.state.floors = Array.from(floorsSet).sort((a,b)=>a-b);
// //         this.state.propertiesByFloor = propertiesByFloor;

// //         if (!this.state.floors.length) this.hidePopup(true);
// //     };

// //     /* ------- filters ------- */
// //     onSiteFilterChange = async (ev) => { this.state.selectedSite = ev.target.value; await this.loadDashboard(); };
// //     toggleState = async (stateVal) => {
// //         const i = this.state.selectedStates.indexOf(stateVal);
// //         if (i === -1) this.state.selectedStates = [...this.state.selectedStates, stateVal];
// //         else { const next = [...this.state.selectedStates]; next.splice(i,1); this.state.selectedStates = next; }
// //         await this.loadDashboard();
// //     };
// //     clearFilters = async () => { this.state.selectedSite = ""; this.state.selectedStates = []; await this.loadDashboard(); };

// //     /* ------- popover ------- */
// //     onCardEnter = (ev, prop) => {
// //         if (prop.state !== "reserved") return;
// //         if (this.state.pop.sticky && this.state.pop.propId === prop.id) return;
// //         const el = ev.currentTarget;
// //         clearTimeout(this.state.hoverTimerId);
// //         this.state.hoverTimerId = setTimeout(() => {
// //             const anchor = (el && el.isConnected) ? el : document.querySelector(`.tp-card[data-prop-id="${prop.id}"]`);
// //             if (!anchor) return;
// //             this.showPopupFor(anchor, prop, false);
// //         }, 1500);
// //     };
// //     onCardLeave = (ev, prop) => {
// //         clearTimeout(this.state.hoverTimerId);
// //         if (this.state.pop.sticky && this.state.pop.propId === prop.id) return;
// //         this.hidePopup();
// //     };
// //     onCardClick = async (ev, prop) => {
// //         if (prop.state === "reserved" || prop.state === "sold") {
// //             if (this.state.pop.sticky && this.state.pop.propId === prop.id) { this.closePopup(); return; }
// //             const el = ev.currentTarget;
// //             const anchor = (el && el.isConnected) ? el : document.querySelector(`.tp-card[data-prop-id="${prop.id}"]`);
// //             if (!anchor) return;
// //             await this.showPopupFor(anchor, prop, true);
// //             return;
// //         }
// //         return this.openProperty(prop.id);
// //     };

// //     async showPopupFor(anchorEl, prop, sticky=false) {
// //         if (!anchorEl || !anchorEl.getBoundingClientRect) return;

// //         const rect = anchorEl.getBoundingClientRect();
// //         const anchorMidX = rect.left + rect.width/2;
// //         const anchorTop  = rect.top;
// //         const anchorBot  = rect.bottom;

// //         const kind = prop.state; // 'reserved' or 'sold'
// //         const key = `${prop.id}:${kind}`;
// //         let info = this.state.cache[key];

// //         if (!info) {
// //             // 1) Get the current reservation for this property and status
// //             const resList = await this.orm.searchRead(
// //                 "property.reservation",
// //                 [["property_id","=", prop.id], ["status","=", kind]],
// //                 ["id","partner_id","salesperson_ids","wing_id","reservation_type_id","expire_date","payment_diff","create_date"],
// //                 { limit: 1, order: "create_date desc" }
// //             );
// //             const rec = resList && resList[0];

// //             // Build base info from reservation
// //             info = {
// //                 customer: rec?.partner_id ? rec.partner_id[1] : "",
// //                 salesperson: rec?.salesperson_ids ? rec.salesperson_ids[1] : "",
// //                 wing: rec?.wing_id ? rec.wing_id[1] : "",
// //                 reservation_type: rec?.reservation_type_id ? rec.reservation_type_id[1] : "",
// //                 expire_date: rec?.expire_date || null,
// //                 payment_diff: rec?.payment_diff ?? null,   // fallback value
// //             };

// //             // 2) If RESERVED, try to override with transfer-history payment_diff (like your form)
// //             if (kind === "reserved" && rec?.id) {
// //                 const transfer = await this.orm.searchRead(
// //                     "property.reservation.transfer.history",
// //                     [["reservation_id","=", rec.id], ["status","in",["draft","pending"]]],
// //                     ["payment_diff","status","create_date"],
// //                     { limit: 1, order: "create_date desc" }
// //                 );
// //                 if (transfer && transfer[0] && transfer[0].payment_diff !== undefined && transfer[0].payment_diff !== null) {
// //                     info.payment_diff = transfer[0].payment_diff;
// //                 }
// //             }

// //             this.state.cache[key] = info;
// //         }

// //         // Provisional placement (above)
// //         this.state.pop = {
// //             visible:true, sticky, kind, propId:prop.id,
// //             left: Math.max(POP_MARGIN, anchorMidX - POP_MAX_W/2),
// //             top:  Math.max(POP_MARGIN, anchorTop - 260),
// //             arrowX: 0, placement: 'above', info,
// //         };

// //         // Next frame: measure and clamp
// //         await new Promise(requestAnimationFrame);
// //         const popEl = document.querySelector('.pop-card');
// //         if (!popEl) return;

// //         const popW = Math.min(Math.max(popEl.offsetWidth || POP_MIN_W, POP_MIN_W), POP_MAX_W);
// //         const popH = popEl.offsetHeight || 220;
// //         const vw = window.innerWidth;
// //         const vh = window.innerHeight;

// //         let placement = 'above';
// //         let top = anchorTop - popH - ARROW_GAP;
// //         if (top < POP_MARGIN) {
// //             placement = 'below';
// //             top = Math.min(vh - popH - POP_MARGIN, anchorBot + ARROW_GAP);
// //         }

// //         let left = anchorMidX - popW / 2;
// //         left = Math.max(POP_MARGIN, Math.min(left, vw - popW - POP_MARGIN));

// //         let arrowX = anchorMidX - left;
// //         arrowX = Math.max(12, Math.min(arrowX, popW - 12));

// //         this.state.pop = { ...this.state.pop, left, top, arrowX, placement };
// //     }

// //     hidePopup(force=false) {
// //         if (!force && this.state.pop.sticky) return;
// //         this.state.pop = { visible:false, sticky:false, kind:null, propId:null, left:0, top:0, arrowX:0, placement:'above', info:{} };
// //     }
// //     closePopup = () => this.hidePopup(true);

// //     openProperty(id) {
// //         this.action.doAction({
// //             type: "ir.actions.act_window",
// //             res_model: "property.property",
// //             res_id: id,
// //             views: [[false, "form"]],
// //             target: "current",
// //         });
// //     }
// // }

// // PropertyDashboard.template = "property_dashboard.template";
// // actionRegistry.add("property_dashboard", PropertyDashboard);







// /** @odoo-module **/

// import { registry } from "@web/core/registry";
// import { useService } from "@web/core/utils/hooks";
// import { Component, onWillStart, useState } from "@odoo/owl";

// const actionRegistry = registry.category("actions");

// const POP_MIN_W = 340;
// const POP_MAX_W = 460;
// const POP_MARGIN = 8;
// const ARROW_GAP  = 12;

// export class PropertyDashboard extends Component {
//     setup() {
//         this.orm = useService("orm");
//         this.action = useService("action");

//         this.state = useState({
//             floors: [],
//             propertiesByFloor: {},
//             sites: [],
//             selectedSite: "",
//             selectedStates: [],
//             pop: { visible:false, sticky:false, kind:null, propId:null, left:0, top:0, arrowX:0, placement:'above', info:{} },
//             cache: {},
//             hoverTimerId: null,
//         });

//         onWillStart(async () => { await this.loadDashboard(); });

//         window.addEventListener('scroll', () => this.hidePopup(false), { passive:true });
//         window.addEventListener('resize', () => this.hidePopup(false), { passive:true });
//     }

//     /* ---------- formatters ---------- */
//     formatNumber = (val) => {
//         if (val === undefined || val === null || val === '') return '-';
//         const num = Number(val);
//         if (Number.isNaN(num)) return String(val);
//         return new Intl.NumberFormat().format(num);
//     };
//     formatInt = (val) => (val || val === 0) ? this.formatNumber(parseInt(val)) : '-';
//     formatArea = (val) => {
//         if (val === undefined || val === null || val === '') return '-';
//         const num = Number(val);
//         if (Number.isNaN(num)) return '-';
//         return `${new Intl.NumberFormat().format(num)} m²`;
//     };
//     formatDateTime = (dt) => {
//         if (!dt) return '—';
//         try { return new Date(dt).toLocaleString(); } catch { return String(dt); }
//     };

//     /* ---------- data ---------- */
//     loadDashboard = async () => {
//         const sites = await this.orm.searchRead("property.site", [], ["id", "name"]);
//         this.state.sites = sites;

//         const domain = [];
//         if (this.state.selectedSite) domain.push(["site", "=", parseInt(this.state.selectedSite)]);
//         if (this.state.selectedStates.length) domain.push(["state", "in", this.state.selectedStates]);

//         const properties = await this.orm.searchRead(
//             "property.property",
//             domain,
//             ["id","name","location","floor_id","state","net_area","gross_area","bedroom","unit_price","site"]
//         );

//         const floorsSet = new Set();
//         const propertiesByFloor = {};
//         for (const p of properties) {
//             const fk = p.floor_id && p.floor_id[0];
//             if (!fk) continue;
//             floorsSet.add(fk);
//             (propertiesByFloor[fk] ||= []).push({ ...p, floor_name: p.floor_id ? p.floor_id[1] : null });
//         }
//         this.state.floors = Array.from(floorsSet).sort((a,b)=>a-b);
//         this.state.propertiesByFloor = propertiesByFloor;

//         if (!this.state.floors.length) this.hidePopup(true);
//     };

//     /* ---------- filters ---------- */
//     onSiteFilterChange = async (ev) => { this.state.selectedSite = ev.target.value; await this.loadDashboard(); };
//     toggleState = async (stateVal) => {
//         const i = this.state.selectedStates.indexOf(stateVal);
//         if (i === -1) this.state.selectedStates = [...this.state.selectedStates, stateVal];
//         else { const next = [...this.state.selectedStates]; next.splice(i,1); this.state.selectedStates = next; }
//         await this.loadDashboard();
//     };
//     clearFilters = async () => { this.state.selectedSite = ""; this.state.selectedStates = []; await this.loadDashboard(); };

//     /* ---------- popover ---------- */
//     onCardEnter = (ev, prop) => {
//         if (prop.state !== "reserved") return;
//         if (this.state.pop.sticky && this.state.pop.propId === prop.id) return;
//         const el = ev.currentTarget;
//         clearTimeout(this.state.hoverTimerId);
//         this.state.hoverTimerId = setTimeout(() => {
//             const anchor = (el && el.isConnected) ? el : document.querySelector(`.tp-card[data-prop-id="${prop.id}"]`);
//             if (!anchor) return;
//             this.showPopupFor(anchor, prop, false);
//         }, 1500);
//     };
//     onCardLeave = (ev, prop) => {
//         clearTimeout(this.state.hoverTimerId);
//         if (this.state.pop.sticky && this.state.pop.propId === prop.id) return;
//         this.hidePopup();
//     };
//     onCardClick = async (ev, prop) => {
//         if (prop.state === "reserved" || prop.state === "sold") {
//             if (this.state.pop.sticky && this.state.pop.propId === prop.id) { this.closePopup(); return; }
//             const el = ev.currentTarget;
//             const anchor = (el && el.isConnected) ? el : document.querySelector(`.tp-card[data-prop-id="${prop.id}"]`);
//             if (!anchor) return;
//             await this.showPopupFor(anchor, prop, true);
//             return;
//         }
//         return this.openProperty(prop.id);
//     };

//     async showPopupFor(anchorEl, prop, sticky=false) {
//         if (!anchorEl || !anchorEl.getBoundingClientRect) return;

//         const rect = anchorEl.getBoundingClientRect();
//         const anchorMidX = rect.left + rect.width/2;
//         const anchorTop  = rect.top;
//         const anchorBot  = rect.bottom;

//         const kind = prop.state; // 'reserved' or 'sold'
//         const key = `${prop.id}:${kind}`;
//         let info = this.state.cache[key];

//         if (!info) {
//             // Get latest reservation in this state
//             const resList = await this.orm.searchRead(
//                 "property.reservation",
//                 [["property_id","=", prop.id], ["status","=", kind]],
//                 ["id","partner_id","salesperson_ids","wing_id","reservation_type_id","expire_date","create_date"],
//                 { limit: 1, order: "create_date desc" }
//             );
//             const rec = resList && resList[0];

//             info = {
//                 customer: rec?.partner_id ? rec.partner_id[1] : "",
//                 salesperson: rec?.salesperson_ids ? rec.salesperson_ids[1] : "",
//                 wing: rec?.wing_id ? rec.wing_id[1] : "",
//                 reservation_type: rec?.reservation_type_id ? rec.reservation_type_id[1] : "",
//                 expire_date: rec?.expire_date || null,
//                 first_payment_amount: null,
//             };

//             // If RESERVED, fetch the first payment amount (earliest by transaction_date, then create_date)
//             if (kind === "reserved" && rec?.id) {
//                 const pay = await this.orm.searchRead(
//                     "property.reservation.payment",
//                     [["reservation_id","=", rec.id], ["payment_status","!=", "canceled"]],
//                     ["amount","transaction_date","create_date"],
//                     { limit: 1, order: "transaction_date asc, create_date asc" }
//                 );
//                 if (pay && pay[0]) {
//                     info.first_payment_amount = pay[0].amount;
//                 }
//             }

//             this.state.cache[key] = info;
//         }

//         // Provisional placement (above)
//         this.state.pop = {
//             visible:true, sticky, kind, propId:prop.id,
//             left: Math.max(POP_MARGIN, anchorMidX - POP_MAX_W/2),
//             top:  Math.max(POP_MARGIN, anchorTop - 260),
//             arrowX: 0, placement: 'above', info,
//         };

//         // Measure and clamp next frame
//         await new Promise(requestAnimationFrame);
//         const popEl = document.querySelector('.pop-card');
//         if (!popEl) return;

//         const popW = Math.min(Math.max(popEl.offsetWidth || POP_MIN_W, POP_MIN_W), POP_MAX_W);
//         const popH = popEl.offsetHeight || 220;
//         const vw = window.innerWidth;
//         const vh = window.innerHeight;

//         let placement = 'above';
//         let top = anchorTop - popH - ARROW_GAP;
//         if (top < POP_MARGIN) {
//             placement = 'below';
//             top = Math.min(vh - popH - POP_MARGIN, anchorBot + ARROW_GAP);
//         }

//         let left = anchorMidX - popW / 2;
//         left = Math.max(POP_MARGIN, Math.min(left, vw - popW - POP_MARGIN));

//         let arrowX = anchorMidX - left;
//         arrowX = Math.max(12, Math.min(arrowX, popW - 12));

//         this.state.pop = { ...this.state.pop, left, top, arrowX, placement };
//     }

//     hidePopup(force=false) {
//         if (!force && this.state.pop.sticky) return;
//         this.state.pop = { visible:false, sticky:false, kind:null, propId:null, left:0, top:0, arrowX:0, placement:'above', info:{} };
//     }
//     closePopup = () => this.hidePopup(true);

//     openProperty(id) {
//         this.action.doAction({
//             type: "ir.actions.act_window",
//             res_model: "property.property",
//             res_id: id,
//             views: [[false, "form"]],
//             target: "current",
//         });
//     }
// }

// PropertyDashboard.template = "property_dashboard.template";
// actionRegistry.add("property_dashboard", PropertyDashboard);








/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

const actionRegistry = registry.category("actions");

const POP_MIN_W = 340;
const POP_MAX_W = 460;
const POP_MARGIN = 8;
const ARROW_GAP  = 12;

export class PropertyDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        this.state = useState({
            floors: [],
            propertiesByFloor: {},
            sites: [],
            selectedSite: "",
            selectedStates: [],
            pop: { visible:false, sticky:false, kind:null, propId:null, left:0, top:0, arrowX:0, placement:'above', info:{} },
            cache: {},
            hoverTimerId: null,
        });

        onWillStart(async () => { await this.loadDashboard(); });

        window.addEventListener('scroll', () => this.hidePopup(false), { passive:true });
        window.addEventListener('resize', () => this.hidePopup(false), { passive:true });
    }

    /* ---------- formatters ---------- */
    formatNumber = (val) => {
        if (val === undefined || val === null || val === '') return '-';
        const num = Number(val);
        if (Number.isNaN(num)) return String(val);
        return new Intl.NumberFormat().format(num);
    };
    formatInt = (val) => (val || val === 0) ? this.formatNumber(parseInt(val)) : '-';
    formatArea = (val) => {
        if (val === undefined || val === null || val === '') return '-';
        const num = Number(val);
        if (Number.isNaN(num)) return '-';
        return `${new Intl.NumberFormat().format(num)} m²`;
    };

    // Parse Odoo UTC "YYYY-MM-DD HH:MM:SS" safely -> local datetime string
    formatDateTime = (dt) => {
        if (!dt) return '—';
        try {
            // If it already looks ISO-like, let Date handle it.
            if (typeof dt === 'string' && dt.includes('T')) {
                const d = new Date(dt);
                return isNaN(d) ? String(dt) : d.toLocaleString();
            }
            // Handle Odoo "YYYY-MM-DD HH:MM:SS" (UTC, no TZ)
            if (typeof dt === 'string') {
                const m = dt.match(/^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})$/);
                if (m) {
                    const [ , Y, M, D, h, mnt, s ] = m.map(Number);
                    // Create as UTC then render in local TZ
                    const d = new Date(Date.UTC(Y, M - 1, D, h, mnt, s));
                    return d.toLocaleString();
                }
            }
            // Fallback for Date objects or other strings
            const d = new Date(dt);
            return isNaN(d) ? String(dt) : d.toLocaleString();
        } catch {
            return String(dt);
        }
    };

    /* ---------- data ---------- */
    loadDashboard = async () => {
        const sites = await this.orm.searchRead("property.site", [], ["id", "name"]);
        this.state.sites = sites;

        const domain = [];
        if (this.state.selectedSite) domain.push(["site", "=", parseInt(this.state.selectedSite)]);
        if (this.state.selectedStates.length) domain.push(["state", "in", this.state.selectedStates]);

        const properties = await this.orm.searchRead(
            "property.property",
            domain,
            ["id","name","location","floor_id","state","net_area","gross_area","bedroom","unit_price","site"]
        );

        const floorsSet = new Set();
        const propertiesByFloor = {};
        for (const p of properties) {
            const fk = p.floor_id && p.floor_id[0];
            if (!fk) continue;
            floorsSet.add(fk);
            (propertiesByFloor[fk] ||= []).push({ ...p, floor_name: p.floor_id ? p.floor_id[1] : null });
        }
        this.state.floors = Array.from(floorsSet).sort((a,b)=>a-b);
        this.state.propertiesByFloor = propertiesByFloor;

        if (!this.state.floors.length) this.hidePopup(true);
    };

    /* ---------- filters ---------- */
    onSiteFilterChange = async (ev) => { this.state.selectedSite = ev.target.value; await this.loadDashboard(); };
    toggleState = async (stateVal) => {
        const i = this.state.selectedStates.indexOf(stateVal);
        if (i === -1) this.state.selectedStates = [...this.state.selectedStates, stateVal];
        else { const next = [...this.state.selectedStates]; next.splice(i,1); this.state.selectedStates = next; }
        await this.loadDashboard();
    };
    clearFilters = async () => { this.state.selectedSite = ""; this.state.selectedStates = []; await this.loadDashboard(); };

    /* ---------- popover ---------- */
    onCardEnter = (ev, prop) => {
        if (prop.state !== "reserved") return;
        if (this.state.pop.sticky && this.state.pop.propId === prop.id) return;
        const el = ev.currentTarget;
        clearTimeout(this.state.hoverTimerId);
        this.state.hoverTimerId = setTimeout(() => {
            const anchor = (el && el.isConnected) ? el : document.querySelector(`.tp-card[data-prop-id="${prop.id}"]`);
            if (!anchor) return;
            this.showPopupFor(anchor, prop, false);
        }, 1500);
    };
    onCardLeave = (ev, prop) => {
        clearTimeout(this.state.hoverTimerId);
        if (this.state.pop.sticky && this.state.pop.propId === prop.id) return;
        this.hidePopup();
    };
    onCardClick = async (ev, prop) => {
        if (prop.state === "reserved" || prop.state === "sold") {
            if (this.state.pop.sticky && this.state.pop.propId === prop.id) { this.closePopup(); return; }
            const el = ev.currentTarget;
            const anchor = (el && el.isConnected) ? el : document.querySelector(`.tp-card[data-prop-id="${prop.id}"]`);
            if (!anchor) return;
            await this.showPopupFor(anchor, prop, true);
            return;
        }
        return this.openProperty(prop.id);
    };

    async showPopupFor(anchorEl, prop, sticky=false) {
        if (!anchorEl || !anchorEl.getBoundingClientRect) return;

        const rect = anchorEl.getBoundingClientRect();
        const anchorMidX = rect.left + rect.width/2;
        const anchorTop  = rect.top;
        const anchorBot  = rect.bottom;

        const kind = prop.state; // 'reserved' or 'sold'
        const key = `${prop.id}:${kind}`;
        let info = this.state.cache[key];

        if (!info) {
            // Get latest reservation in this state (includes expire_date)
            const resList = await this.orm.searchRead(
                "property.reservation",
                [["property_id","=", prop.id], ["status","=", kind]],
                ["id","partner_id","salesperson_ids","wing_id","reservation_type_id","expire_date","create_date"],
                { limit: 1, order: "create_date desc" }
            );
            const rec = resList && resList[0];

            info = {
                customer: rec?.partner_id ? rec.partner_id[1] : "",
                salesperson: rec?.salesperson_ids ? rec.salesperson_ids[1] : "",
                wing: rec?.wing_id ? rec.wing_id[1] : "",
                reservation_type: rec?.reservation_type_id ? rec.reservation_type_id[1] : "",
                // <- use property.reservation.expire_date directly
                expire_date: rec?.expire_date || null,
                first_payment_amount: null,
            };

            // If RESERVED, fetch the first payment amount (earliest)
            if (kind === "reserved" && rec?.id) {
                const pay = await this.orm.searchRead(
                    "property.reservation.payment",
                    [["reservation_id","=", rec.id], ["payment_status","!=", "canceled"]],
                    ["amount","transaction_date","create_date"],
                    { limit: 1, order: "transaction_date asc, create_date asc" }
                );
                if (pay && pay[0]) {
                    info.first_payment_amount = pay[0].amount;
                }
            }

            this.state.cache[key] = info;
        }

        // Provisional placement (above)
        this.state.pop = {
            visible:true, sticky, kind, propId:prop.id,
            left: Math.max(POP_MARGIN, anchorMidX - POP_MAX_W/2),
            top:  Math.max(POP_MARGIN, anchorTop - 260),
            arrowX: 0, placement: 'above', info,
        };

        // Measure and clamp next frame
        await new Promise(requestAnimationFrame);
        const popEl = document.querySelector('.pop-card');
        if (!popEl) return;

        const popW = Math.min(Math.max(popEl.offsetWidth || POP_MIN_W, POP_MIN_W), POP_MAX_W);
        const popH = popEl.offsetHeight || 220;
        const vw = window.innerWidth;
        const vh = window.innerHeight;

        let placement = 'above';
        let top = anchorTop - popH - ARROW_GAP;
        if (top < POP_MARGIN) {
            placement = 'below';
            top = Math.min(vh - popH - POP_MARGIN, anchorBot + ARROW_GAP);
        }

        let left = anchorMidX - popW / 2;
        left = Math.max(POP_MARGIN, Math.min(left, vw - popW - POP_MARGIN));

        let arrowX = anchorMidX - left;
        arrowX = Math.max(12, Math.min(arrowX, popW - 12));

        this.state.pop = { ...this.state.pop, left, top, arrowX, placement };
    }

    hidePopup(force=false) {
        if (!force && this.state.pop.sticky) return;
        this.state.pop = { visible:false, sticky:false, kind:null, propId:null, left:0, top:0, arrowX:0, placement:'above', info:{} };
    }
    closePopup = () => this.hidePopup(true);

    openProperty(id) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "property.property",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

PropertyDashboard.template = "property_dashboard.template";
actionRegistry.add("property_dashboard", PropertyDashboard);
