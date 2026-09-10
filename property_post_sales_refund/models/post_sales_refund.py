from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from markupsafe import Markup

class PostSalesRefundRequest(models.Model):
    _name = 'post.sales.refund.request'
    _description = 'Post Sales Refund Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Refund Reference', required=True, copy=False, readonly=True, default='New')
    contract_number = fields.Char(string='Contract Number', required=True, tracking=True)
    void_request_id = fields.Many2one(
        'property.contract.void.request', 
        string='Void Contract Request', 
        required=True, 
        tracking=True
    )

    partner_id = fields.Many2one(related='void_request_id.partner_id', string='Customer', store=True)
    property_id = fields.Many2one(related='void_request_id.property_id', string='Property', store=True)
    buyer_name = fields.Html(related='void_request_id.buyer_name', string='Buyer Names', readonly=True)
    currency_id = fields.Many2one('res.currency', related='void_request_id.currency_id')
    
    collected_amount = fields.Monetary(
        string="Total Amount Collected", 
        compute='_compute_collected_amount', 
        store=True, 
        currency_field='currency_id'
    )
    
    penalty_percent = fields.Float(string="Penalty (%)", default=0.0, compute='_compute_penalty_percent', store=True, tracking=True)
    penalty_amount = fields.Monetary(
        string="Penalty Amount", 
        compute='_compute_penalty_amount',
        store=True, 
        readonly=False,
        tracking=True,
        currency_field='currency_id'
    )
    refund_amount = fields.Monetary(string="Expected Refund Amount", compute='_compute_refund_amounts', store=True, currency_field='currency_id')
    
    pay_date = fields.Date(string="Expected Refund Date", tracking=True)
    credit_note_id = fields.Many2one('account.move', string="Generated Credit Note", readonly=True)
    attachment_ids = fields.Many2many(
        'ir.attachment', 
        string='Attachments',
        help="Attach supporting documents here."
    )


    state = fields.Selection([
        ('draft', 'Draft'),
        ('after_sales_checked', 'After Sales Checked'),
        ('collection_checked', 'Collection Head'),
        ('finance_approved', 'Finance Approved'),
        ('refunded', 'Refunded'),
        ('rejected', 'Rejected')
    ], string='Status', default='draft', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('post.sales.refund.request') or 'New'
        
        records = super().create(vals_list)
        
        for record in records:
            if record.attachment_ids:
                record.attachment_ids.sudo().write({
                    'res_model': self._name,
                    'res_id': record.id
                })
                
        return records

    def write(self, vals):
        res = super().write(vals)
        
        if 'attachment_ids' in vals:
            for record in self:
                if record.attachment_ids:
                    orphan_attachments = record.attachment_ids.filtered(
                        lambda a: a.res_model != self._name or a.res_id != record.id
                    )
                    if orphan_attachments:
                        orphan_attachments.sudo().write({
                            'res_model': self._name,
                            'res_id': record.id
                        })
        return res

    @api.constrains('void_request_id', 'state')
    def _check_unique_refund_request(self):
        for rec in self:
            if rec.state != 'rejected':
                domain = [
                    ('void_request_id', '=', rec.void_request_id.id),
                    ('state', '!=', 'rejected'),
                    ('id', '!=', rec.id)
                ]
                if self.search_count(domain) > 0:
                    raise ValidationError(_("An active Refund Request already exists for this Void Request."))

    @api.onchange('contract_number')
    def _onchange_contract_number(self):
        if self.contract_number:
            input_number = self.contract_number.strip()

            domain = [
                ('state', '=', 'approved'),
                '|', '|',
                ('contract_number', '=ilike', input_number),
                ('contract_number', '=ilike', f"{input_number}-VOID"),
                ('contract_number', '=ilike', f"{input_number}-VOID-%")
            ]

            void_req = self.env['property.contract.void.request'].search(domain, order='create_date desc', limit=1)
            
            if void_req:
                self.void_request_id = void_req.id
            else:
                self.void_request_id = False
                return {
                    'warning': {
                        'title': _('Not Found'),
                        'message': _('No Approved Void Request found for the exact Contract Number "%s". Please ensure you entered the full original contract number.', input_number)
                    }
                }
        else:
            self.void_request_id = False

    @api.depends('void_request_id')
    def _compute_collected_amount(self):
        for rec in self:
            if rec.void_request_id:
                order = getattr(rec.void_request_id, 'collection_id', False) or (rec.void_request_id.sale_id.collection_order_id if rec.void_request_id.sale_id else False)
                rec.collected_amount = sum(order.installment_ids.mapped('amount_paid')) if order else 0.0
            else:
                rec.collected_amount = 0.0

    @api.depends('penalty_percent', 'collected_amount')
    def _compute_penalty_amount(self):
        for rec in self:
            rec.penalty_amount = (rec.collected_amount * rec.penalty_percent) / 100.0

    @api.depends('penalty_amount', 'collected_amount')
    def _compute_penalty_percent(self):
        for rec in self:
            if rec.collected_amount > 0:
                rec.penalty_percent = (rec.penalty_amount / rec.collected_amount) * 100.0
            else:
                rec.penalty_percent = 0.0

    @api.depends('collected_amount', 'penalty_amount', 'penalty_percent')
    def _compute_refund_amounts(self):
        for rec in self:
            rec.refund_amount = rec.collected_amount - rec.penalty_amount

            
    def action_after_sales_check(self):
        self.write({'state': 'after_sales_checked'})
        self.message_post(body="Request checked by After Sales Director.")

    def action_collection_check(self):
        if not self.pay_date:
            raise UserError(_("Please set the Expected Refund Date before proceeding to Finance."))
        self.write({'state': 'collection_checked'})
        self.message_post(body="Request checked by Collection Department.")

    def action_finance_approve(self):
        for req in self:
            if req.refund_amount <= 0:
                raise UserError(_("Refund amount must be greater than zero to approve."))
            
            # Draft Credit Note
            move_vals = {
                'move_type': 'out_refund',
                'partner_id': req.partner_id.id,
                'invoice_date': req.pay_date or fields.Date.context_today(self),
                'ref': f"Post Sales Refund - {req.name}",
                'is_void_refund': True,
                'void_penalty_amount': req.penalty_amount,
                'invoice_line_ids': [(0, 0, {
                    'name': f"Refund for Voided Contract {req.contract_number or ''}",
                    'quantity': 1,
                    'price_unit': req.refund_amount,
                })]
            }
            move = self.env['account.move'].sudo().create(move_vals)
            req.credit_note_id = move.id
            req.write({'state': 'finance_approved'})
            req.message_post(body=f"Request approved by Finance. Credit Note {move.name or 'created'} generated.")

    def action_mark_refunded(self):
        for req in self:
            req.write({'state': 'refunded'})

            notification_body = Markup(
                "<b>Refund Successfully Processed</b><br/>"
                "The expected refund amount of %s has been paid to the client.<br/>"
            ) % (req.refund_amount)

            req.message_post(body=notification_body, subtype_xmlid='mail.mt_note')

            # 2. Notify Collection and After Sales Teams
            collection_group = self.env.ref('property_post_sales_refund.group_refund_collection_user', raise_if_not_found=False)
            after_sales_group = self.env.ref('property_post_sales_refund.group_refund_after_sales_director', raise_if_not_found=False)
            collection_mgr_group = self.env.ref('property_post_sales_refund.group_refund_collection_manager', raise_if_not_found=False)
            
            users_to_notify = self.env['res.users']
            if collection_group:
                users_to_notify |= collection_group.users
            if after_sales_group:
                users_to_notify |= after_sales_group.users
            if collection_mgr_group:
                users_to_notify |= collection_mgr_group.users

            if users_to_notify:
                partner_ids = users_to_notify.mapped('partner_id').ids
                req.message_post(
                    body="The client has been successfully refunded.",
                    partner_ids=partner_ids,
                    subtype_xmlid='mail.mt_comment'
                )


            void_req = req.void_request_id
            sale_order = void_req.sale_id
            collection_order = void_req.collection_id or (sale_order.collection_order_id if sale_order else False)
            
            cross_log_body = Markup(
                "<b>Post Sales Refund Completed</b><br/>"
                "Refund Reference: <a href='#' data-oe-model='post.sales.refund.request' data-oe-id='%s'>%s</a><br/>"
                "Refund Amount: %s<br/>"
                "The finance department has marked the refund as completed and paid."
            ) % (req.id, req.name, req.refund_amount)

            # Log to Sale Order
            if sale_order:
                sale_order.sudo().message_post(
                    body=cross_log_body, 
                    subtype_xmlid='mail.mt_note'
                )
            
            # Log to Collection Order
            if collection_order:
                collection_order.sudo().message_post(
                    body=cross_log_body, 
                    subtype_xmlid='mail.mt_note'
                )

    def action_reject(self):
        self.write({'state': 'rejected'})
        self.message_post(body="Refund request has been rejected.")