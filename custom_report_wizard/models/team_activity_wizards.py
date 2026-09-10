from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import date, timedelta
import logging

_logger = logging.getLogger(__name__)

class TeamActivityWizard(models.TransientModel):
    _name = "team.activity.wizard"
    _description = "Team Activity Report Wizard"

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
        default='salesperson',
    )
    wing_id = fields.Selection(
        selection='_get_wing_selection',
        string='Wing',
        required=True,
    )
    date_filter_2 = fields.Selection([
            ('custom', 'Custom'),
            ('this_week', 'This Week'),
            ('this_month', 'This Month'),
        ], string="Date Filter", default='custom')
    
    @api.onchange('date_filter_2')
    def _onchange_date_filter_2(self):
        today = fields.Date.context_today(self)
        if self.date_filter_2 == 'this_week':
            start = today - timedelta(days=today.weekday())
            end = start + timedelta(days=6)
            self.date_from = start
            self.date_to = end
        elif self.date_filter_2 == 'this_month':
            start = today.replace(day=1)
            if start.month == 12:
                end = start.replace(year=start.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end = start.replace(month=start.month + 1, day=1) - timedelta(days=1)
            self.date_from = start
            self.date_to = end
    @api.onchange('report_by')
    def _onchange_report_by(self):
        # You can hide/show the field in XML using invisible on the view, but for logic:
        if not self.wing_id:
            self.wing_id = False

    @api.model
    def _get_report_by_selection(self):
        user = self.env.user
        if user.has_group('custom_report_wizard.team_activity_report'):
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
            raise UserError(_("Please select a Wing."))

    def _fetch_raw(self):
        self.ensure_one()
        self._validate()
        wing_condition = ""
        params = [self.date_from, self.date_to]

        if self.wing_id:
            if self.wing_id == 'no_wing':
                wing_condition = " AND cl.wing_id IS NULL"
            else:
                wing_condition = " AND cl.wing_id = %s"
                params.append(int(self.wing_id))

        query = f"""
        WITH filtered_leads AS (
            SELECT cl.id, cl.stage_id, cl.user_id, cl.supervisor_id, cl.wing_id
            FROM crm_lead cl
            WHERE cl.create_date BETWEEN %s AND %s {wing_condition}
        ),
        lead_events AS (
            SELECT
                fl.id AS lead_id,
                rp.name AS sales_person,
                rp_sup.name AS supervisor_name,
                rp_wing.name AS wing_manager_name,
                COALESCE(psw.name, 'No Wing') AS wing_name,
                CASE
                    WHEN stage.name::jsonb ->> 'en_US' ILIKE '%%expired%%'     THEN 'Expired'
                    WHEN stage.name::jsonb ->> 'en_US' ILIKE '%%won%%'         THEN 'Won'
                    WHEN stage.name::jsonb ->> 'en_US' ILIKE '%%reservation%%' THEN 'Reservation'
                    WHEN stage.name::jsonb ->> 'en_US' ILIKE '%%follow%%'      THEN 'Follow Up'
                    WHEN stage.name::jsonb ->> 'en_US' ILIKE '%%prospect%%'    THEN 'Prospect'
                    ELSE NULL
                END AS event_type
            FROM filtered_leads fl
            JOIN crm_stage stage ON fl.stage_id = stage.id
            JOIN res_users ru ON fl.user_id = ru.id
            JOIN res_partner rp ON ru.partner_id = rp.id
            JOIN property_sales_supervisor pss ON fl.supervisor_id = pss.id
            JOIN res_users ru_sup ON pss.name = ru_sup.id
            JOIN res_partner rp_sup ON ru_sup.partner_id = rp_sup.id
            LEFT JOIN property_sales_wing psw ON fl.wing_id = psw.id
            LEFT JOIN res_users ru_wing ON psw.manager_id = ru_wing.id
            LEFT JOIN res_partner rp_wing ON ru_wing.partner_id = rp_wing.id
        ),
        activity_events AS (
            SELECT
                cl.id AS lead_id,
                rp.name AS sales_person,
                rp_sup.name AS supervisor_name,
                rp_wing.name AS wing_manager_name,
                COALESCE(psw.name, 'No Wing') AS wing_name,
                CASE
                    WHEN mm.subtype_id = 3 AND mtv.new_value_char IS NULL THEN
                        CASE mm.mail_activity_type_id
                            WHEN 1 THEN 'Email'
                            WHEN 2 THEN 'SMS'
                            WHEN 4 THEN 'Call'
                            WHEN 8 THEN 'Office Visit'
                            WHEN 9 THEN 'Site Visit'
                            ELSE NULL
                        END
                    WHEN mtv.new_value_char = 'Won' THEN 'Won'
                    ELSE NULL
                END AS event_type
            FROM crm_lead cl
            JOIN filtered_leads fl ON fl.id = cl.id
            JOIN res_users ru ON cl.user_id = ru.id
            JOIN res_partner rp ON ru.partner_id = rp.id
            JOIN mail_message mm ON mm.model = 'crm.lead' AND mm.res_id = cl.id
            LEFT JOIN mail_tracking_value mtv ON mtv.mail_message_id = mm.id
            JOIN property_sales_supervisor pss ON cl.supervisor_id = pss.id
            JOIN res_users ru_sup ON pss.name = ru_sup.id
            JOIN res_partner rp_sup ON ru_sup.partner_id = rp_sup.id
            LEFT JOIN property_sales_wing psw ON cl.wing_id = psw.id
            LEFT JOIN res_users ru_wing ON psw.manager_id = ru_wing.id
            LEFT JOIN res_partner rp_wing ON ru_wing.partner_id = rp_wing.id
            WHERE TRIM(BOTH FROM LOWER(COALESCE(mtv.old_value_char, ''))) <> 'sales'
                AND mm.subtype_id <> 5
        ),
        unioned_events AS (
            SELECT * FROM lead_events
            UNION ALL
            SELECT * FROM activity_events
        ),
        reservation_summary AS (
            SELECT
                COALESCE(psw.name, 'No Wing') AS wing_name,
                rp_wing.name AS wing_manager_name,
                rp_sup.name AS supervisor_name,
                rp.name AS sales_person,
                COUNT(pr.id) AS reservation_count
            FROM property_reservation pr
            JOIN crm_lead cl ON cl.id = pr.crm_lead_id
            JOIN filtered_leads fl ON fl.id = cl.id
            JOIN res_users ru ON ru.id = cl.user_id
            JOIN res_partner rp ON rp.id = ru.partner_id
            JOIN property_sales_supervisor pss ON pss.id = cl.supervisor_id
            JOIN res_users ru_sup ON ru_sup.id = pss.name
            JOIN res_partner rp_sup ON rp_sup.id = ru_sup.partner_id
            LEFT JOIN property_sales_wing psw ON psw.id = cl.wing_id
            LEFT JOIN res_users ru_wing ON ru_wing.id = psw.manager_id
            LEFT JOIN res_partner rp_wing ON rp_wing.id = ru_wing.partner_id
            GROUP BY wing_name, wing_manager_name, supervisor_name, sales_person
        )
        SELECT
            ue.wing_name, ue.wing_manager_name, ue.supervisor_name, ue.sales_person,
            COUNT(*) FILTER (WHERE ue.event_type = 'Office Visit') AS office_visit_count,
            COUNT(*) FILTER (WHERE ue.event_type = 'Site Visit')   AS site_visit_count,
            COUNT(*) FILTER (WHERE ue.event_type = 'Call')         AS call_count,
            COUNT(*) FILTER (WHERE ue.event_type = 'Email')        AS email_count,
            COUNT(*) FILTER (WHERE ue.event_type = 'SMS')          AS sms_count,
            (
                COUNT(*) FILTER (WHERE ue.event_type = 'Office Visit') +
                COUNT(*) FILTER (WHERE ue.event_type = 'Site Visit') +
                COUNT(*) FILTER (WHERE ue.event_type = 'Call') +
                COUNT(*) FILTER (WHERE ue.event_type = 'Email') +
                COUNT(*) FILTER (WHERE ue.event_type = 'SMS')
            ) AS total_key_events
        FROM unioned_events ue
        LEFT JOIN reservation_summary rs
        ON ue.wing_name = rs.wing_name
        AND ue.wing_manager_name = rs.wing_manager_name
        AND ue.supervisor_name = rs.supervisor_name
        AND ue.sales_person = rs.sales_person
        WHERE ue.event_type IS NOT NULL
        GROUP BY ue.wing_name, ue.wing_manager_name, ue.supervisor_name, ue.sales_person
        ORDER BY ue.wing_name, ue.wing_manager_name, ue.supervisor_name, ue.sales_person;
        """
        # Add wing_id param if it's not 'no_wing'
        if wing_condition.endswith("= %s"):
            self.env.cr.execute(query, tuple(params))
        else:
            self.env.cr.execute(query, (self.date_from, self.date_to))
        return self.env.cr.fetchall()

    def action_print(self):
        self._validate()
        rows_raw = self._fetch_raw()
        rows = []
        totals = {
            "office_visit_count": 0,
            "site_visit_count": 0,
            "call_count": 0,
            "email_count": 0,
            "sms_count": 0,
            "total_key_events": 0,
        }

        if self.report_by == 'wing':
            group_fields = ['wing_name', 'wing_manager_name']
        elif self.report_by == 'supervisor':
            group_fields = ['wing_name', 'wing_manager_name', 'supervisor_name']
        else:
            group_fields = ['wing_name', 'wing_manager_name', 'supervisor_name', 'sales_person']

        grouped = {}

        for row in rows_raw:
            row_dict = {
                "wing_name": row[0],
                "wing_manager_name": row[1],
                "supervisor_name": row[2],
                "sales_person": row[3],
                "office_visit_count": int(row[4] or 0),
                "site_visit_count": int(row[5] or 0),
                "call_count": int(row[6] or 0),
                "email_count": int(row[7] or 0),
                "sms_count": int(row[8] or 0),
                "total_key_events": int(row[9] or 0),
            }

            totals["office_visit_count"] += row_dict["office_visit_count"]
            totals["site_visit_count"] += row_dict["site_visit_count"]
            totals["call_count"] += row_dict["call_count"]
            totals["email_count"] += row_dict["email_count"]
            totals["sms_count"] += row_dict["sms_count"]
            totals["total_key_events"] += row_dict["total_key_events"]

            key = tuple(row_dict[field] for field in group_fields)
            if key in grouped:
                grouped[key]["office_visit_count"] += row_dict["office_visit_count"]
                grouped[key]["site_visit_count"] += row_dict["site_visit_count"]
                grouped[key]["call_count"] += row_dict["call_count"]
                grouped[key]["email_count"] += row_dict["email_count"]
                grouped[key]["sms_count"] += row_dict["sms_count"]
                grouped[key]["total_key_events"] += row_dict["total_key_events"]
            else:
                grouped[key] = {f: row_dict[f] for f in group_fields}
                grouped[key].update({
                    "office_visit_count": row_dict["office_visit_count"],
                    "site_visit_count": row_dict["site_visit_count"],
                    "call_count": row_dict["call_count"],
                    "email_count": row_dict["email_count"],
                    "sms_count": row_dict["sms_count"],
                    "total_key_events": row_dict["total_key_events"],
                })

        rows = list(grouped.values())

        # For report context, also add selected wing name
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
        return self.env.ref('custom_report_wizard.team_activity_pdf').report_action(self, data=data)
