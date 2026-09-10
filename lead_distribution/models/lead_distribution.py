from odoo import models, fields, tools


class LeadDistribution(models.Model):
    _name = "lead.distribution"
    _description = "Lead Distribution Report"
    _auto = False
    _order = "assign_date desc"

    customer_name = fields.Char(readonly=True)
    lead_type = fields.Selection(
        [
            ("affiliate", "Affiliate"),
            ("website", "Website"),
            ("reception", "Reception"),
            ("callcenter", "Call Center"),
        ],
        readonly=True,
    )

    assigned_salesperson_id = fields.Many2one(
        "res.users", string="Salesperson", readonly=True
    )
    assigned_wing_id = fields.Many2one(
        "property.wing.config", string="Assigned Wing", readonly=True
    )

    assign_date = fields.Datetime(string="Assignment Date", readonly=True)
    is_current_week = fields.Boolean(readonly=True)
    day_of_week = fields.Selection(
        [
            ("0", "Sunday"),
            ("1", "Monday"),
            ("2", "Tuesday"),
            ("3", "Wednesday"),
            ("4", "Thursday"),
            ("5", "Friday"),
            ("6", "Saturday"),
        ],
        string="Day of Week",
        readonly=True,
    )

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            """
            CREATE OR REPLACE VIEW %s AS (
                SELECT 
                    row_number() OVER () AS id,
                    customer_name,
                    lead_source AS lead_type,
                    assigned_salesperson_id,
                    assigned_wing_id,
                    assign_date,
                    CAST(CAST(EXTRACT(DOW FROM assign_date) AS INTEGER) AS TEXT) AS day_of_week,
                    CASE 
                        WHEN date_trunc('week', assign_date) = date_trunc('week', CURRENT_DATE) 
                        THEN True ELSE False 
                    END AS is_current_week
                FROM (
                    SELECT customer_name, 'affiliate' as lead_source, assigned_salesperson_id, assigned_wing_id, create_date as assign_date FROM crm_affilater WHERE state_crm = 'sent'
                    UNION ALL
                    SELECT customer_name, 'website' as lead_source, assigned_salesperson_id, assigned_wing_id, create_date as assign_date FROM crm_website WHERE state_crm = 'sent'
                    UNION ALL
                    SELECT customer_name, 'reception' as lead_source, assigned_salesperson_id, assigned_wing_id, create_date as assign_date FROM crm_reception WHERE state_crm = 'sent'
                    UNION ALL
                    SELECT customer_name, 'callcenter' as lead_source, assigned_salesperson_id, assigned_wing_id, create_date as assign_date FROM crm_callcenter WHERE state_crm = 'sent'
                ) AS subquery
            )
        """
            % self._table
        )
