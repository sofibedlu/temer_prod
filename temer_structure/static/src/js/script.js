odoo.define('temer_structure.no_drilldown_pivot', function (require) {
    "use strict";

    var PivotView = require('web.PivotView');

    PivotView.include({
        _onCellClick: function (event) {
            // Prevent the default drilldown behavior completely.
            event.preventDefault();
            event.stopPropagation();
            
            // Completely stop any further processing of the click event
            return; // Do nothing further
        },
        
        // Optionally, you can override other methods if necessary
        // _onCellClick: function (event) {
        //     // Custom logic to prevent clicks
        // },
    });
});