from odoo import models, fields, tools, api

class CollectionSegmentationReport(models.Model):
    _name = 'collection.segmentation.report'
    _description = 'Collection Segmentation Report'
    _auto = False
    _order = 'id desc'

    collection_id = fields.Many2one('collection.order', string="Collection Order", readonly=True)

    # --- 1. Product Segmentation ---
    property_type = fields.Selection(related='collection_id.property_id.property_type', string="Property Type", readonly=True)
    site_id = fields.Many2one('property.site', related='collection_id.property_id.site', string="Site", readonly=True)
    unit_type = fields.Char(string="Unit Type", compute='_compute_blank_strings')
    floor_number = fields.Char(related='collection_id.property_id.floor_id.name', string="Floor Number", readonly=True)
    unit_number = fields.Char(related='collection_id.property_id.unit_number', string="Unit Number", readonly=True)
    gross_area = fields.Float(string="Gross Area", compute="_compute_property_areas")
    net_area = fields.Float(string="Net Area", compute="_compute_property_areas")

    # --- 2. Sales-force Segmentation ---
    officer_id = fields.Many2one('res.users', related='collection_id.sale_id.sales_person', string="Officer", readonly=True)
    supervisor_id = fields.Many2one('property.sales.supervisor', related='collection_id.sale_id.reservation_id.supervisor_id', string="Supervisor", readonly=True)

    # --- 3. Customer Segmentation ---
    customer_name = fields.Char(string="Customer Name", compute='_compute_customer_name')
    agreement_number = fields.Char(related='collection_id.contract_number', string="Agreement Number", readonly=True)
    contact_number = fields.Char(string="Contact Number", compute='_compute_blank_strings')

    # --- 4. Periodical Segmentation ---
    contract_date = fields.Char(related='collection_id.sale_id.contract_id.contract_date_char', string="Contract Date", readonly=True)
    # 🌟 These are now fetched dynamically from the SQL View
    payment_round_number = fields.Integer(string="Last Paid Round", readonly=True)
    paid_date = fields.Date(string="Last Paid Date", readonly=True)

    # --- 5. Effort Metrics ---
    call_follow_up = fields.Char(string="Call Follow-up", compute='_compute_blank_strings')
    text_follow_up = fields.Integer(string="Text Follow-up", readonly=True)
    letter_follow_up = fields.Integer(string="Letter Follow-up", readonly=True)
    services = fields.Char(string="Services", compute='_compute_blank_strings')

    # --- 6. Result & Quality Metrics (Placeholders) ---
    reg_collection = fields.Float(string="Cash Collected - Regular", compute='_compute_zero_metrics')
    penalty_recovery = fields.Float(string="Cash Collected - Penalty Due", compute='_compute_zero_metrics')
    termination_recovery = fields.Float(string="Cash Collected - Termination Due", compute='_compute_zero_metrics')
    other_collection = fields.Float(string="Cash Collected - Other", compute='_compute_zero_metrics')
    collection_rec_rate = fields.Float(string="Collection Recovery Rate", compute='_compute_zero_metrics')
    due_rec_rate = fields.Float(string="Due Recovery Rate", compute='_compute_zero_metrics')
    payment_extensions = fields.Integer(string="Payment Extensions", compute='_compute_zero_metrics')
    advance_remaining = fields.Float(string="Advance Remaining", compute='_compute_zero_metrics')
    void_customers = fields.Integer(string="Void Customers", compute='_compute_zero_metrics')
    term_customers = fields.Integer(string="Terminated Customers", compute='_compute_zero_metrics')
    fully_paid = fields.Integer(string="Fully Paid", compute='_compute_zero_metrics')
    installments_paid = fields.Integer(string="Installments Paid", compute='_compute_zero_metrics')


    @api.depends(
        'collection_id.property_id.property_type_gross_area', 
        'collection_id.property_id.gross_area',
        'collection_id.property_id.property_type_net_area', 
        'collection_id.property_id.net_area'
    )
    def _compute_property_areas(self):
        for rec in self:
            prop = rec.collection_id.property_id
            if prop:
                # If the new field is greater than 0, use it. Otherwise, use the legacy field!
                rec.gross_area = prop.property_type_gross_area if prop.property_type_gross_area else prop.gross_area
                rec.net_area = prop.property_type_net_area if prop.property_type_net_area else prop.net_area
            else:
                rec.gross_area = 0.0
                rec.net_area = 0.0

    @api.depends('collection_id.buyers_name_text', 'collection_id.partner_id.name')
    def _compute_customer_name(self):
        for rec in self:
            b_text = rec.collection_id.buyers_name_text
            if b_text and b_text.strip() != 'No buyers found':
                rec.customer_name = b_text
            else:
                rec.customer_name = rec.collection_id.partner_id.name

    def _compute_blank_strings(self):
        for rec in self:
            rec.unit_type = ""
            rec.contact_number = ""
            rec.call_follow_up = ""
            rec.services = ""

    def _compute_zero_metrics(self):
        for rec in self:
            rec.reg_collection = 0.0
            rec.penalty_recovery = 0.0
            rec.termination_recovery = 0.0
            rec.other_collection = 0.0
            rec.collection_rec_rate = 0.0
            rec.due_rec_rate = 0.0
            rec.payment_extensions = 0
            rec.advance_remaining = 0.0
            rec.void_customers = 0
            rec.term_customers = 0
            rec.fully_paid = 0
            rec.installments_paid = 0

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        
        # 🌟 MAGIC SQL: Finds the absolute latest paid installment for each collection order
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                WITH ranked_installments AS (
                    SELECT
                        id,
                        collection_id,
                        RANK() OVER (PARTITION BY collection_id ORDER BY sequence, id) AS round_num
                    FROM collection_installment
                ),
                latest_paid_installment AS (
                    SELECT DISTINCT ON (ci.collection_id)
                        ci.collection_id,
                        ri.round_num AS last_payment_round_number,
                        cip.payment_date AS last_paid_date
                    FROM collection_installment_payment cip
                    JOIN collection_installment ci ON cip.installment_id = ci.id
                    JOIN ranked_installments ri ON ci.id = ri.id
                    WHERE cip.status = 'paid'
                    ORDER BY ci.collection_id, cip.payment_date DESC, ri.round_num DESC
                )
                SELECT
                    co.id AS id,
                    co.id AS collection_id,
                    (SELECT COUNT(*) FROM collection_sms_log csl 
                     JOIN collection_installment ci ON ci.id = csl.installment_id 
                     WHERE ci.collection_id = co.id) AS text_follow_up,
                    (SELECT COUNT(*) FROM letter_saved ls 
                     JOIN collection_installment ci ON ci.id = ls.installment_id 
                     WHERE ci.collection_id = co.id) AS letter_follow_up,
                    lpi.last_payment_round_number AS payment_round_number,
                    lpi.last_paid_date AS paid_date
                FROM collection_order co
                LEFT JOIN latest_paid_installment lpi ON co.id = lpi.collection_id
            )
        """ % (self._table,))