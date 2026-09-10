# -*- coding: utf-8 -*-

from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class TemerLeadAnalysisWizard(models.TransientModel):
    _inherit = 'temer.lead.analysis.wizard'

    @api.model
    def _get_wing_selection(self):
        """
        Dynamically show wings from database.
        Override to fetch all wings from property_sales_wing table.
        """
        user = self.env.user
        wings = []
        # Fetch all wings from DB first
        self.env.cr.execute("SELECT id, name FROM property_sales_wing ORDER BY name")
        db_wings = {}
        for w_id, w_name in self.env.cr.fetchall():
            if w_name and w_name.strip():  # Only add if name is not empty
                db_wings[w_id] = w_name.strip()
                wings.append((str(w_id), w_name.strip()))
        
        # Add "No Wing" option if allowed and not already in database
        if user.has_group('custom_report_wizard.group_no_wing_access'):
            # Check if "No wing" or "No Wing" already exists in database
            has_no_wing = any(name.lower() in ['no wing'] for name in db_wings.values())
            if not has_no_wing:
                wings.append(('no_wing', 'No Wing'))
        
        return wings

