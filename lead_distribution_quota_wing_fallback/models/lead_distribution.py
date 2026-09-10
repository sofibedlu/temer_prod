from odoo import models, tools


class LeadDistribution(models.Model):
    _inherit = "lead.distribution"

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
                    SELECT
                        caf.customer_name,
                        'affiliate' AS lead_source,
                        caf.assigned_salesperson_id,
                        caf.assigned_wing_id AS assigned_wing_id,
                        caf.create_date AS assign_date
                    FROM crm_affilater caf
                    WHERE caf.state_crm = 'sent'

                    UNION ALL

                    SELECT
                        cw.customer_name,
                        'website' AS lead_source,
                        cw.assigned_salesperson_id,
                        COALESCE(
                            cw.assigned_wing_id,
                            (
                                SELECT pwc.id
                                FROM property_wing_config pwc
                                JOIN utm_source us ON us.id = pwc.source_id
                                WHERE us.name = 'Website'
                                  AND pwc.wing_id = cw.assigned_sales_wing_id
                                ORDER BY pwc.id
                                LIMIT 1
                            )
                        ) AS assigned_wing_id,
                        cw.create_date AS assign_date
                    FROM crm_website cw
                    WHERE cw.state_crm = 'sent'

                    UNION ALL

                    SELECT
                        cr.customer_name,
                        'reception' AS lead_source,
                        cr.assigned_salesperson_id,
                        COALESCE(
                            cr.assigned_wing_id,
                            (
                                SELECT pwc.id
                                FROM property_wing_config pwc
                                JOIN utm_source us ON us.id = pwc.source_id
                                WHERE us.name = 'Walk In'
                                  AND pwc.wing_id = cr.assigned_sales_wing_id
                                ORDER BY pwc.id
                                LIMIT 1
                            )
                        ) AS assigned_wing_id,
                        cr.create_date AS assign_date
                    FROM crm_reception cr
                    WHERE cr.state_crm = 'sent'

                    UNION ALL

                    SELECT
                        cc.customer_name,
                        'callcenter' AS lead_source,
                        cc.assigned_salesperson_id,
                        COALESCE(
                            cc.assigned_wing_id,
                            (
                                SELECT pwc.id
                                FROM property_wing_config pwc
                                JOIN utm_source us ON us.id = pwc.source_id
                                WHERE us.name = '6033'
                                  AND pwc.wing_id = cc.assigned_sales_wing_id
                                ORDER BY pwc.id
                                LIMIT 1
                            )
                        ) AS assigned_wing_id,
                        cc.create_date AS assign_date
                    FROM crm_callcenter cc
                    WHERE cc.state_crm = 'sent'
                ) AS subquery
            )
        """
            % self._table
        )
