from odoo import models, fields

class WingStructureList(models.Model):
    _name = 'wing.structure.list'
    _description = 'Wing Structure Report (All Sales Persons per Supervisor)'
    _auto = False  # Use SQL view, not a physical table

    wing_name = fields.Char("Wing Name", readonly=True)
    wing_manager_name = fields.Char("Wing Manager Name", readonly=True)
    supervisor_name = fields.Char("Supervisor Name", readonly=True)
    sales_manager = fields.Char("Sales Manager", readonly=True)
    sales_person = fields.Char("Sales Person", readonly=True)

    def init(self):
        self.env.cr.execute("DROP VIEW IF EXISTS wing_structure_list;")
        # self.env.cr.execute("""
        #     CREATE OR REPLACE VIEW wing_structure_list AS (
        #         WITH filtered_leads AS (
        #             SELECT cl.id, cl.stage_id, cl.user_id, cl.supervisor_id, cl.wing_id, cl.sales_team_id
        #             FROM crm_lead cl
        #         ),
        #         lead_events AS (
        #             SELECT
        #                 fl.id AS lead_id,
        #                 rp.name AS sales_person,
        #                 rp_sup.name AS supervisor_name,
        #                 rp_wing.name AS wing_manager_name,
        #                 COALESCE(psw.name, 'No Wing') AS wing_name,
        #                 rp_mgr.name AS sales_manager
        #             FROM filtered_leads fl
        #             JOIN crm_stage stage ON fl.stage_id = stage.id
        #             JOIN res_users ru ON fl.user_id = ru.id
        #             JOIN res_partner rp ON ru.partner_id = rp.id
        #             JOIN property_sales_supervisor pss ON fl.supervisor_id = pss.id
        #             LEFT JOIN property_sales_team pst ON fl.sales_team_id = pst.id
        #             LEFT JOIN res_users ru_mgr ON pst.manager_id = ru_mgr.id
        #             LEFT JOIN res_partner rp_mgr ON ru_mgr.partner_id = rp_mgr.id
        #             JOIN res_users ru_sup ON pss.name = ru_sup.id
        #             JOIN res_partner rp_sup ON ru_sup.partner_id = rp_sup.id
        #             LEFT JOIN property_sales_wing psw ON fl.wing_id = psw.id
        #             LEFT JOIN res_users ru_wing ON psw.manager_id = ru_wing.id
        #             LEFT JOIN res_partner rp_wing ON ru_wing.partner_id = rp_wing.id
        #         ),
        #         activity_events AS (
        #             SELECT 
        #                 cl.id AS lead_id,
        #                 rp.name AS sales_person,
        #                 rp_sup.name AS supervisor_name,
        #                 rp_wing.name AS wing_manager_name,
        #                 COALESCE(psw.name, 'No Wing') AS wing_name,
        #                 rp_mgr.name AS sales_manager
        #             FROM crm_lead cl
        #             JOIN filtered_leads fl ON cl.id = fl.id
        #             JOIN res_users ru ON cl.user_id = ru.id
        #             JOIN res_partner rp ON ru.partner_id = rp.id
        #             JOIN mail_message mm ON mm.model = 'crm.lead' AND mm.res_id = cl.id
        #             LEFT JOIN mail_tracking_value mtv ON mm.id = mtv.mail_message_id
        #             JOIN property_sales_supervisor pss ON cl.supervisor_id = pss.id
        #             LEFT JOIN property_sales_team pst ON fl.sales_team_id = pst.id
        #             LEFT JOIN res_users ru_mgr ON pst.manager_id = ru_mgr.id
        #             LEFT JOIN res_partner rp_mgr ON ru_mgr.partner_id = rp_mgr.id
        #             JOIN res_users ru_sup ON pss.name = ru_sup.id
        #             JOIN res_partner rp_sup ON ru_sup.partner_id = rp_sup.id
        #             LEFT JOIN property_sales_wing psw ON cl.wing_id = psw.id
        #             LEFT JOIN res_users ru_wing ON psw.manager_id = ru_wing.id
        #             LEFT JOIN res_partner rp_wing ON ru_wing.partner_id = rp_wing.id
        #             WHERE 
        #                 TRIM(BOTH FROM LOWER(COALESCE(mtv.old_value_char, ''))) <> 'sales'
        #                 AND mm.subtype_id <> 5
        #         ),
        #         unioned_events AS (
        #             SELECT * FROM lead_events
        #             UNION ALL
        #             SELECT * FROM activity_events
        #         )
        #         SELECT
        #             ROW_NUMBER() OVER (ORDER BY sales_manager, supervisor_name, sales_person) as id,
        #             wing_name,
        #             wing_manager_name,
        #             supervisor_name,
        #             sales_manager,
        #             sales_person
        #         FROM (
        #             SELECT DISTINCT
        #                 wing_name,
        #                 wing_manager_name,
        #                 supervisor_name,
        #                 sales_manager,
        #                 sales_person
        #             FROM unioned_events
        #             WHERE supervisor_name IS NOT NULL AND sales_person IS NOT NULL
        #         ) AS unique_pairs
        #         ORDER BY sales_manager, supervisor_name, sales_person
        #     );
        # """)

        self.env.cr.execute("""
            CREATE OR REPLACE VIEW wing_structure_list AS (
                WITH lead_events AS (
                    -- Get hierarchy data from all leads, including the last modification date
                    SELECT
                        cl.id AS lead_id,
                        rp.name AS sales_person,
                        rp_sup.name AS supervisor_name,
                        rp_wing.name AS wing_manager_name,
                        COALESCE(psw.name, 'No Wing') AS wing_name,
                        rp_mgr.name AS sales_manager,
                        cl.write_date AS event_date -- Use the lead's modification date for ranking
                    FROM crm_lead cl
                    JOIN crm_stage stage ON cl.stage_id = stage.id
                    JOIN res_users ru ON cl.user_id = ru.id
                    JOIN res_partner rp ON ru.partner_id = rp.id
                    JOIN property_sales_supervisor pss ON cl.supervisor_id = pss.id
                    LEFT JOIN property_sales_team pst ON cl.sales_team_id = pst.id
                    LEFT JOIN res_users ru_mgr ON pst.manager_id = ru_mgr.id
                    LEFT JOIN res_partner rp_mgr ON ru_mgr.partner_id = rp_mgr.id
                    JOIN res_users ru_sup ON pss.name = ru_sup.id
                    JOIN res_partner rp_sup ON ru_sup.partner_id = rp_sup.id
                    LEFT JOIN property_sales_wing psw ON cl.wing_id = psw.id
                    LEFT JOIN res_users ru_wing ON psw.manager_id = ru_wing.id
                    LEFT JOIN res_partner rp_wing ON ru_wing.partner_id = rp_wing.id
                ),
                activity_events AS (
                    -- Get hierarchy data from leads with specific activities, including the activity date
                    SELECT 
                        cl.id AS lead_id,
                        rp.name AS sales_person,
                        rp_sup.name AS supervisor_name,
                        rp_wing.name AS wing_manager_name,
                        COALESCE(psw.name, 'No Wing') AS wing_name,
                        rp_mgr.name AS sales_manager,
                        mm.date AS event_date -- Use the message/activity date for ranking
                    FROM crm_lead cl
                    JOIN res_users ru ON cl.user_id = ru.id
                    JOIN res_partner rp ON ru.partner_id = rp.id
                    JOIN mail_message mm ON mm.model = 'crm.lead' AND mm.res_id = cl.id
                    LEFT JOIN mail_tracking_value mtv ON mm.id = mtv.mail_message_id
                    JOIN property_sales_supervisor pss ON cl.supervisor_id = pss.id
                    LEFT JOIN property_sales_team pst ON cl.sales_team_id = pst.id
                    LEFT JOIN res_users ru_mgr ON pst.manager_id = ru_mgr.id
                    LEFT JOIN res_partner rp_mgr ON ru_mgr.partner_id = rp_mgr.id
                    JOIN res_users ru_sup ON pss.name = ru_sup.id
                    JOIN res_partner rp_sup ON ru_sup.partner_id = rp_sup.id
                    LEFT JOIN property_sales_wing psw ON cl.wing_id = psw.id
                    LEFT JOIN res_users ru_wing ON psw.manager_id = ru_wing.id
                    LEFT JOIN res_partner rp_wing ON ru_wing.partner_id = rp_wing.id
                    WHERE 
                        TRIM(BOTH FROM LOWER(COALESCE(mtv.old_value_char, ''))) <> 'sales'
                        AND mm.subtype_id <> 5
                ),
                unioned_events AS (
                    -- Combine both sets of events
                    SELECT * FROM lead_events
                    UNION ALL
                    SELECT * FROM activity_events
                ),
                ranked_events AS (
                    -- For each salesperson, rank their records by date in descending order
                    -- The latest record will get a rank of 1
                    SELECT
                        *,
                        ROW_NUMBER() OVER(PARTITION BY sales_person ORDER BY event_date DESC) as rnk
                    FROM unioned_events
                    WHERE supervisor_name IS NOT NULL AND sales_person IS NOT NULL
                )
                -- Final selection: choose only the records ranked as #1 for each salesperson
                SELECT
                    ROW_NUMBER() OVER (ORDER BY sales_manager, supervisor_name, sales_person) as id,
                    wing_name,
                    wing_manager_name,
                    supervisor_name,
                    sales_manager,
                    sales_person
                FROM ranked_events
                WHERE rnk = 1
                ORDER BY sales_manager, supervisor_name, sales_person
            );
        """)
