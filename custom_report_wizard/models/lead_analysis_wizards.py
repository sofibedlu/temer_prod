# -*- coding: utf-8 -*-
"""
Lead-Analysis PDF Wizard – v2.1
Odoo 17  © 2025
"""

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import date, timedelta
import logging
import base64

_logger = logging.getLogger(__name__)

class LeadAnalysisWizard(models.TransientModel):
    _name = "lead.analysis.wizard"
    _description = "Lead Analysis Report Wizard"

    date_filter = fields.Selection([
            ('custom', 'Custom'),
            ('this_week', 'This Week'),
            ('this_month', 'This Month'),
        ], string="Date Filter", default='custom')

    date_from = fields.Date(
        string="From",
        required=True,
        default=lambda self: fields.Date.context_today(self),
    )
    date_to = fields.Date(
        string="To",
        required=True,
        default=lambda self: fields.Date.context_today(self),
    )
    report_by = fields.Selection(
        selection='_get_report_by_selection',
        string='Report By',
        required=True,
    )
    wing_id = fields.Selection(
        selection='_get_wing_selection',
        string='Wing',
        required=True,
    )

    @api.onchange('date_filter')
    def _onchange_date_filter(self):
        today = fields.Date.context_today(self)
        if self.date_filter == 'this_week':
            start = today - timedelta(days=today.weekday())
            end = start + timedelta(days=6)
            self.date_from = start
            self.date_to = end
        elif self.date_filter == 'this_month':
            start = today.replace(day=1)
            if start.month == 12:
                end = start.replace(year=start.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end = start.replace(month=start.month + 1, day=1) - timedelta(days=1)
            self.date_from = start
            self.date_to = end

    @api.model
    def _get_report_by_selection(self):
        user = self.env.user
        if user.has_group('custom_report_wizard.lead_analysis_report'):
            return [
                ('wing', 'Wing'),
                ('supervisor', 'Supervisor'),
                ('salesperson', 'Salesperson'),
            ]
        elif user.has_group('temer_structure.access_property_sales_supervisor_group'):
            return [
                ('supervisor', 'Supervisor'),
                ('salesperson', 'Salesperson'),
            ]
        else:
            return []
        
    @api.model
    def _get_wing_selection(self):
        """
        Dynamically show wings based on user group access.
        """
        user = self.env.user
        wings = []
        # Always add No Wing if allowed
        if user.has_group('custom_report_wizard.group_no_wing_access'):
            wings.append(('no_wing', 'No Wing'))
        # Fetch from DB
        self.env.cr.execute("SELECT id, name FROM property_sales_wing ORDER BY name")
        for w_id, w_name in self.env.cr.fetchall():
            name_lower = w_name.strip().lower()
            # Match against lowercase strings!
            if name_lower == "team - ajwa" and user.has_group('custom_report_wizard.group_team_ajwa_access'):
                wings.append((str(w_id), w_name))
            if name_lower == "team - taj" and user.has_group('custom_report_wizard.group_team_taj_access'):
                wings.append((str(w_id), w_name))
            if name_lower == "team - raha" and user.has_group('custom_report_wizard.group_team_Raha_access'):
                wings.append((str(w_id), w_name))
        return wings

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        selection = self._get_report_by_selection()
        if selection:
            res['report_by'] = selection[0][0]
        return res

    def _validate(self):
        self.ensure_one()
        allowed = [x[0] for x in self._get_report_by_selection()]
        if self.report_by not in allowed:
            raise UserError(_("You are not allowed to select this report type."))
        if self.date_from > self.date_to:
            raise UserError(_("`From` date must be before `To` date."))
        if not self.wing_id:
            raise UserError(_("Please select a Wing to view its analysis."))
    
    def _fetch_raw(self):
        # ... (keep your existing _fetch_raw method exactly as it is) ...
        self.ensure_one()
        self._validate()

        # --- Wing Filter Construction ---
        wing_condition = ""
        wing_param = None
        if self.wing_id:
            if self.wing_id == 'no_wing':
                wing_condition = " AND cl.wing_id IS NULL"
            else:
                wing_condition = " AND psw.id = %s"
                wing_param = int(self.wing_id)

        date_from = self.date_from
        date_to = self.date_to

        # Prepare params: first for filtered_leads, then for reservation_counts
        params = [date_from, date_to]
        if wing_param is not None:
            params.append(wing_param)
        params += [date_from, date_to]
        if wing_param is not None:
            params.append(wing_param)

        query = f"""
            WITH all_supervisors AS (
                SELECT DISTINCT
                    pss.id    AS supervisor_id,
                    rp_sup.name AS supervisor_name
                FROM property_sales_supervisor pss
                JOIN res_users ru_sup     ON pss.name          = ru_sup.id
                JOIN res_partner rp_sup   ON ru_sup.partner_id = rp_sup.id
                WHERE EXISTS (
                    SELECT 1
                    FROM crm_lead
                    WHERE supervisor_id = pss.id
                )
            ),

            filtered_leads AS (
                SELECT 
                    cl.id                     AS lead_id,
                    cl.create_date,
                    cl.stage_id,
                    s.name::jsonb->>'en_US'   AS stage_name,
                    cl.user_id,
                    up.name                   AS sales_person,
                    cl.supervisor_id,
                    COALESCE(asup.supervisor_name, 'No Supervisor') AS supervisor_name,
                    COALESCE(psw.name, 'No Wing')   AS wing_name,
                    COALESCE(rp_wing.name, '')      AS wing_manager_name
                FROM crm_lead cl
                LEFT JOIN all_supervisors asup ON cl.supervisor_id = asup.supervisor_id
                LEFT JOIN crm_stage        s    ON cl.stage_id       = s.id
                LEFT JOIN res_users        u    ON cl.user_id        = u.id
                LEFT JOIN res_partner      up   ON u.partner_id      = up.id
                LEFT JOIN property_sales_wing psw ON cl.wing_id     = psw.id
                LEFT JOIN res_users        ru_wing ON psw.manager_id = ru_wing.id
                LEFT JOIN res_partner      rp_wing ON ru_wing.partner_id = rp_wing.id
                WHERE cl.create_date BETWEEN %s AND %s
                {wing_condition}
            ),

            -- capture wings that have NO supervisor assigned
            no_supervisor_wings AS (
                SELECT DISTINCT
                    wing_name,
                    wing_manager_name
                FROM filtered_leads
                WHERE supervisor_id IS NULL
            ),

            lead_events AS (
                SELECT
                    lead_id,
                    sales_person,
                    supervisor_name,
                    wing_manager_name,
                    wing_name,
                    CASE
                        WHEN stage_name IS NULL                      THEN NULL
                        WHEN LOWER(stage_name) LIKE '%%expired%%'      THEN 'Expired'
                        WHEN LOWER(stage_name) LIKE '%%reservation%%'  THEN 'Reservation'
                        WHEN LOWER(stage_name) LIKE '%%follow%%'       THEN 'Follow Up'
                        WHEN LOWER(stage_name) LIKE '%%prospect%%'     THEN 'Prospect'
                        WHEN LOWER(stage_name) LIKE '%%lost%%'         THEN 'Lost'
                    END AS event_type
                FROM filtered_leads
            ),

            activity_events AS (
                SELECT
                    fl.lead_id,
                    fl.sales_person,
                    fl.supervisor_name,
                    fl.wing_manager_name,
                    fl.wing_name,
                    'Lost' AS event_type
                FROM mail_message mm
                JOIN filtered_leads fl       ON mm.res_id         = fl.lead_id
                JOIN mail_tracking_value mtv ON mm.id             = mtv.mail_message_id
                WHERE mm.model     = 'crm.lead'
                AND mm.subtype_id <> 5
                AND mtv.new_value_char = 'Lost'
                AND TRIM(LOWER(COALESCE(mtv.old_value_char, ''))) <> 'sales'
            ),

            unioned_events AS (
                SELECT * FROM lead_events
                UNION ALL
                SELECT * FROM activity_events
            ),

            event_counts AS (
                SELECT
                    wing_name,
                    wing_manager_name,
                    supervisor_name,
                    sales_person,
                    event_type,
                    CASE
                        WHEN event_type = 'Lost' THEN COUNT(DISTINCT lead_id)
                        ELSE COUNT(*)
                    END AS count
                FROM unioned_events
                WHERE event_type IS NOT NULL
                GROUP BY wing_name, wing_manager_name, supervisor_name, sales_person, event_type
            ),

            reservation_counts AS (
                SELECT 
                    COALESCE(psw.name, 'No Wing')            AS wing_name,
                    COALESCE(rp_wing.name, '')               AS wing_manager_name,
                    COALESCE(rp_sup.name, 'No Supervisor')   AS supervisor_name,
                    rp.name                                  AS sales_person,
                    COUNT(pr.id)                             AS reservation_count,
                    SUM(CASE WHEN pr.status = 'sold'      THEN 1 ELSE 0 END) AS sold_reservation_count,
                    SUM(CASE WHEN pr.status = 'requested' THEN 1 ELSE 0 END) AS requested_reservation_count,
                    SUM(CASE WHEN pr.status = 'expired'   THEN 1 ELSE 0 END) AS expired_reservation_count,
                    SUM(CASE WHEN pr.status = 'canceled'  THEN 1 ELSE 0 END) AS canceled_reservation_count
                FROM property_reservation pr
                JOIN crm_lead                    cl     ON pr.crm_lead_id    = cl.id
                JOIN res_users                  ru     ON cl.user_id        = ru.id
                JOIN res_partner                rp     ON ru.partner_id     = rp.id
                LEFT JOIN property_sales_supervisor pss ON cl.supervisor_id = pss.id
                LEFT JOIN res_users             ru_sup ON pss.name           = ru_sup.id
                LEFT JOIN res_partner           rp_sup ON ru_sup.partner_id = rp_sup.id
                LEFT JOIN property_sales_wing   psw   ON cl.wing_id         = psw.id
                LEFT JOIN res_users             ru_wing ON psw.manager_id    = ru_wing.id
                LEFT JOIN res_partner           rp_wing ON ru_wing.partner_id = rp_wing.id
                WHERE pr.create_date BETWEEN %s AND %s
                {wing_condition}
                GROUP BY wing_name, wing_manager_name, supervisor_name, sales_person
            ),

            final_summary AS (
                SELECT
                    COALESCE(ec.wing_name, rc.wing_name, 'No Wing')              AS wing_name,
                    COALESCE(ec.wing_manager_name, rc.wing_manager_name, '')     AS wing_manager_name,
                    COALESCE(ec.supervisor_name, rc.supervisor_name, '')         AS supervisor_name,
                    COALESCE(ec.sales_person, rc.sales_person, '')               AS sales_person,
                    COALESCE(MAX(CASE WHEN ec.event_type = 'Prospect'     THEN ec.count END), 0) AS prospect,
                    COALESCE(MAX(CASE WHEN ec.event_type = 'Follow Up'    THEN ec.count END), 0) AS follow_up,
                    COALESCE(MAX(rc.reservation_count),                  0)       AS reservation_count,
                    COALESCE(MAX(rc.sold_reservation_count),             0)       AS sold_reservation_count,
                    COALESCE(MAX(rc.requested_reservation_count),        0)       AS requested_reservation_count,
                    COALESCE(MAX(rc.expired_reservation_count),          0)       AS expired_reservation_count,
                    COALESCE(MAX(rc.canceled_reservation_count),         0)       AS canceled_reservation_count,
                    COALESCE(MAX(CASE WHEN ec.event_type = 'Expired' THEN ec.count END), 0)   AS expired,
                    COALESCE(MAX(CASE WHEN ec.event_type = 'Lost'    THEN ec.count END), 0)   AS lost,
                    0                                                              AS current_reservation,
                                    (
                        COALESCE(MAX(CASE WHEN ec.event_type = 'Prospect' THEN ec.count END), 0)
                        + COALESCE(MAX(CASE WHEN ec.event_type = 'Follow Up' THEN ec.count END), 0)
                        + COALESCE(MAX(rc.reservation_count), 0)
                        + COALESCE(MAX(rc.sold_reservation_count), 0)
                        + COALESCE(MAX(CASE WHEN ec.event_type = 'Expired' THEN ec.count END), 0)
                        + COALESCE(MAX(CASE WHEN ec.event_type = 'Lost' THEN ec.count END), 0)
                    ) AS total,
                    CASE 
                        WHEN COALESCE(ec.wing_name, rc.wing_name, 'No Wing') = 'No Wing'
                        AND COALESCE(ec.wing_manager_name, rc.wing_manager_name, '') <> ''
                        THEN '🟡 Missing wing_name'
                        ELSE '✅ OK'
                    END                                                             AS data_flag
                FROM event_counts ec
                FULL OUTER JOIN reservation_counts rc 
                ON ec.sales_person       = rc.sales_person
                AND ec.supervisor_name    = rc.supervisor_name
                AND ec.wing_name          = rc.wing_name
                AND ec.wing_manager_name  = rc.wing_manager_name
                GROUP BY 
                    COALESCE(ec.wing_name, rc.wing_name, 'No Wing'),
                    COALESCE(ec.wing_manager_name, rc.wing_manager_name, ''),
                    COALESCE(ec.supervisor_name, rc.supervisor_name, ''),
                    COALESCE(ec.sales_person, rc.sales_person, '')
            )

            SELECT * FROM final_summary

            UNION ALL

            -- add wings with no supervisor (all metrics zero)
            SELECT
                nsw.wing_name,
                nsw.wing_manager_name,
                'No Supervisor'  AS supervisor_name,
                ''               AS sales_person,
                0 AS prospect,
                0 AS follow_up,
                0 AS reservation_count,
                0 AS sold_reservation_count,
                0 AS requested_reservation_count,
                0 AS expired_reservation_count,
                0 AS canceled_reservation_count,
                0 AS expired,
                0 AS lost,
                0 AS current_reservation,
                0 AS total,
                '✅ OK' AS data_flag
            FROM no_supervisor_wings nsw
            WHERE NOT EXISTS (
                SELECT 1 
                FROM final_summary fs
                WHERE fs.wing_name         = nsw.wing_name
                AND fs.wing_manager_name = nsw.wing_manager_name
                AND fs.supervisor_name   = 'No Supervisor'
            )

            ORDER BY wing_name, wing_manager_name;
            """

        self.env.cr.execute(query, tuple(params))
        return self.env.cr.fetchall()

    def _prepare_report_data(self):
        """Prepare report data for both print and preview actions"""
        self._validate()
        rows_raw = self._fetch_raw()
        rows = []
        totals = {
            "prospect": 0,
            "follow_up": 0,
            "reservation_count": 0,
            "sold_reservation_count": 0,
            "expired": 0,
            "lost": 0,
            "current_reservation": 0,
            "total": 0,
        }
        all_fields = ['wing_name', 'wing_manager_name', 'supervisor_name', 'sales_person']
        if self.report_by == 'wing':
            group_fields = ['wing_name', 'wing_manager_name']
        elif self.report_by == 'supervisor':
            group_fields = ['wing_name', 'wing_manager_name', 'supervisor_name']
        else:
            group_fields = ['wing_name', 'wing_manager_name', 'supervisor_name', 'sales_person']

        grouped = {}
        for row in rows_raw:
            row_dict = {
                "wing_name": row[0] or '',
                "wing_manager_name": row[1] or '',
                "supervisor_name": row[2] or '',
                "sales_person": row[3] or '',
                "prospect": int(row[4] or 0),
                "follow_up": int(row[5] or 0),
                "reservation_count": int(row[6] or 0),
                "sold_reservation_count": int(row[7] or 0),
                "requested_reservation_count": int(row[8] or 0),
                "expired_reservation_count": int(row[9] or 0),
                "canceled_reservation_count": int(row[10] or 0),
                "expired": int(row[11] or 0),  # event count
                "lost": int(row[12] or 0),
                "current_reservation": int(row[13] or 0),
                "total": int(row[14] or 0),
                "data_flag": row[15],
            }
            # Calculate grand total as sum of required fields
            totals["prospect"] += row_dict["prospect"]
            totals["follow_up"] += row_dict["follow_up"]
            totals["reservation_count"] += row_dict["reservation_count"]
            totals["sold_reservation_count"] += row_dict["sold_reservation_count"]
            totals["expired"] += row_dict["expired"]
            totals["lost"] += row_dict["lost"]
            totals["current_reservation"] += row_dict["current_reservation"]
            # Correct grand total calculation
            totals["total"] += (
                row_dict["prospect"]
                + row_dict["follow_up"]
                + row_dict["reservation_count"]
                + row_dict["sold_reservation_count"]
                + row_dict["expired"]
                + row_dict["lost"]
            )
            key = tuple(row_dict[field] for field in group_fields)
            if key in grouped:
                grouped[key]["prospect"] += row_dict["prospect"]
                grouped[key]["follow_up"] += row_dict["follow_up"]
                grouped[key]["reservation_count"] += row_dict["reservation_count"]
                grouped[key]["sold_reservation_count"] += row_dict["sold_reservation_count"]
                grouped[key]["expired"] += row_dict["expired"]
                grouped[key]["lost"] += row_dict["lost"]
                grouped[key]["current_reservation"] += row_dict["current_reservation"]
                grouped[key]["total"] += (
                    row_dict["prospect"]
                    + row_dict["follow_up"]
                    + row_dict["reservation_count"]
                    + row_dict["sold_reservation_count"]
                    + row_dict["expired"]
                    + row_dict["lost"]
                )
            else:
                grouped[key] = {f: row_dict[f] for f in all_fields}
                grouped[key].update({
                    "prospect": row_dict["prospect"],
                    "follow_up": row_dict["follow_up"],
                    "reservation_count": row_dict["reservation_count"],
                    "sold_reservation_count": row_dict["sold_reservation_count"],
                    "expired": row_dict["expired"],
                    "lost": row_dict["lost"],
                    "current_reservation": row_dict["current_reservation"],
                    "total": (
                        row_dict["prospect"]
                        + row_dict["follow_up"]
                        + row_dict["reservation_count"]
                        + row_dict["sold_reservation_count"]
                        + row_dict["expired"]
                        + row_dict["lost"]
                    ),
                    "data_flag": row_dict["data_flag"],
                })
                for unused in set(all_fields) - set(group_fields):
                    if unused not in grouped[key]:
                        grouped[key][unused] = ''
        rows = list(grouped.values())

        wing_dict = dict(self._get_wing_selection())
        selected_wing_name = wing_dict.get(self.wing_id, '') if self.wing_id else ''

        data = {
            "rows": rows,
            "totals": totals,
            "date_from": str(self.date_from),
            "date_to": str(self.date_to),
            "report_by": self.report_by,
            "wing_name": selected_wing_name,
        }
        return data

    def action_print(self):
        """Generate PDF for download"""
        data = self._prepare_report_data()
        return self.env.ref('custom_report_wizard.lead_analysis_pdf').report_action(self, data=data)

    def action_preview(self):
        """Generate HTML for browser preview"""
        data = self._prepare_report_data()
        return self.env.ref('custom_report_wizard.lead_analysis_html').report_action(self, data=data)