from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from markupsafe import Markup


class InstallmentUpdateWizard(models.TransientModel):
    _name = 'installment.update.wizard'
    _description = 'Installment Update Dashboard'
    _rec_name = 'site_id'

    # ── Site selector ──────────────────────────────────────────────
    site_id = fields.Many2one(
        'property.site',
        string='Site / Project',
        required=True,
    )

    # ── Helper: related payment structure for domain filtering ────
    payment_structure_id = fields.Many2one(
        'property.payment.term',
        related='site_id.payment_structure_id',
        string='Payment Structure',
    )

    # ── Old Installment selector ───────────────────────────────────
    term_line_id = fields.Many2one(
        'property.payment.term.line',
        string='Old Installment',
        help='Select the installment term line to be replaced.',
    )

    # ── New Installment selector ───────────────────────────────────
    new_installment_id = fields.Many2one(
        'property.payment.term.line',
        string='New Installment',
        help='Select the term line that will replace the old one.',
    )

    # ── Match counts ───────────────────────────────────────────────
    collection_installment_count = fields.Integer(
        string='Collection Installments',
        compute='_compute_match_counts',
    )
    sale_line_count = fields.Integer(
        string='Property Sale Lines',
        compute='_compute_match_counts',
    )
    legacy_line_count = fields.Integer(
        string='Legacy Sale Lines',
        compute='_compute_match_counts',
    )

    # ───────────────────────────────────────────────────────────────
    @api.onchange('site_id')
    def _onchange_site_id(self):
        self.term_line_id = False
        self.new_installment_id = False

    @api.onchange('term_line_id')
    def _onchange_term_line_id(self):
        self.new_installment_id = False

    # ───────────────────────────────────────────────────────────────
    @api.depends('site_id', 'term_line_id')
    def _compute_match_counts(self):
        for rec in self:
            if not rec.site_id or not rec.term_line_id:
                rec.collection_installment_count = 0
                rec.sale_line_count = 0
                rec.legacy_line_count = 0
                continue

            search_name = rec.term_line_id.name or ''

            col_orders = self.env['collection.order'].search([
                ('site_id', '=', rec.site_id.id),
            ])

            import logging
            _logger = logging.getLogger(__name__)
           
            sale_ids = col_orders.mapped('sale_id').ids
         
            if not sale_ids:
                rec.sale_line_count = 0
            else:
                domain = [
                    ('sale_id', 'in', sale_ids),
                    ('payment_term_id.name', '=', rec.term_line_id.name),
                ]
                _logger.info("====== DEBUG property.payment.line domain: %s ======", domain)
                rec.sale_line_count = self.env['property.payment.line'].search_count(domain)
                
                _logger.info("====== DEBUG sale_line_count: %s ======", rec.sale_line_count)    
                _logger.info("====== DEBUG search_name term id: %s ======", rec.term_line_id.id)    
         
            rec.collection_installment_count = self.env['collection.installment'].search_count([
                ('collection_id.site_id', '=', rec.site_id.id),
                ('name', '=', search_name),
            ])


            
            properties = self.env['property.property'].search([('site', '=', rec.site_id.id)])
            legacy_sales = self.env['property.legacy.sale'].search([('property_id', 'in', properties.ids)])
            rec.legacy_line_count = self.env['property.legacy.sale.line'].search_count([
                ('legacy_sale_id', 'in', legacy_sales.ids),
                ('name', '=', search_name),
            ])


    # ── Smart-button actions ────────────────────────────────────────
    def action_view_collection_installments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Matching Collection Installments',
            'res_model': 'collection.installment',
            'view_mode': 'tree,form',
            'domain': [
                ('site_id', '=', self.site_id.id),
                ('name', '=', self.term_line_id.name or ''),
            ],
            'target': 'current',
        }

    def action_view_sale_lines(self):
        self.ensure_one()
        col_orders = self.env['collection.order'].search([('site_id', '=', self.site_id.id)])
        sale_ids = col_orders.mapped('sale_id').ids
        tree_view = self.env.ref('installment_update.view_property_payment_line_tree_standalone')
        form_view = self.env.ref('installment_update.view_property_payment_line_form_standalone')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Matching Property Sale Lines',
            'res_model': 'property.payment.line',
            'view_mode': 'tree,form',
            'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
            'domain': [
                ('sale_id', 'in', sale_ids),
                ('payment_term_id.name', '=', self.term_line_id.name),
            ],
            'target': 'current',
        }

    def action_view_legacy_lines(self):
        self.ensure_one()
        properties = self.env['property.property'].search([('site', '=', self.site_id.id)])
        legacy_sales = self.env['property.legacy.sale'].search([('property_id', 'in', properties.ids)])
        return {
            'type': 'ir.actions.act_window',
            'name': 'Matching Legacy Sale Lines',
            'res_model': 'property.legacy.sale.line',
            'view_mode': 'tree,form',
            'domain': [
                ('legacy_sale_id', 'in', legacy_sales.ids),
                ('name', '=', self.term_line_id.name or ''),
            ],
            'target': 'current',
        }


    def action_update_installments(self):
        self.ensure_one()

     
        if not self.term_line_id:
            raise ValidationError(_("Please select an Old Installment."))
        if not self.new_installment_id:
            raise ValidationError(_("Please select a New Installment."))
        if self.new_installment_id == self.term_line_id:
            raise ValidationError(_("New Installment must be different from the Old Installment."))

        with self.env.cr.savepoint():
            old_name = self.term_line_id.name or ''
            new_name = self.new_installment_id.name or ''
            new_term_line = self.new_installment_id
            old_term_line_id = self.term_line_id.id


            col_orders = self.env['collection.order'].search([
                ('site_id', '=', self.site_id.id),
            ])
            sale_ids = col_orders.mapped('sale_id').ids
            sales = self.env['property.sale'].browse(sale_ids)

            properties = self.env['property.property'].search([('site', '=', self.site_id.id)])
            legacy_sales = self.env['property.legacy.sale'].search([('property_id', 'in', properties.ids)])

            collection_installments = self.env['collection.installment'].search([
                ('collection_id.site_id', '=', self.site_id.id),
                ('name', '=', old_name),
            ])

            sale_lines = self.env['property.payment.line'].search([
                ('sale_id', 'in', sales.ids),
                ('payment_term_id.name', '=', old_name),
            ])
            
            legacy_lines = self.env['property.legacy.sale.line'].search([
                ('legacy_sale_id', 'in', legacy_sales.ids),
                ('name', '=', old_name),
            ])

            if not (collection_installments or sale_lines or legacy_lines):
                raise ValidationError(_("No matching records found for the selected installment."))

            count_ci = len(collection_installments)
            count_sl = len(sale_lines)
            count_ll = len(legacy_lines)

            log_msg = Markup(_(
                '<b>Installment Substitution</b><br/>'
                'Old installment <b>%(old)s</b> replaced by <b>%(new)s</b><br/>'
                'Site: %(site)s &nbsp;|&nbsp; Done by: %(user)s'
            )) % {
                'old': old_name,
                'new': new_name,
                'site': self.site_id.name or '',
                'user': self.env.user.name,
            }

            if collection_installments:
                collection_installments.write({
                    'name': new_name,
                    'payment_term_line_id': new_term_line.id,
                })
                collection_orders = collection_installments.mapped('collection_id')
                for order in collection_orders:
                    order.message_post(body=log_msg)

            if sale_lines:
                sale_lines.write({'payment_term_id': new_term_line.id})
                sale_records = sale_lines.mapped('sale_id')
                for sale in sale_records:
                    sale.message_post(body=log_msg)

            if legacy_lines:
                legacy_lines.write({
                    'name': new_name,
                    'payment_term_line_id': new_term_line.id,
                })
                legacy_sale_records = legacy_lines.mapped('legacy_sale_id')
                for legacy_sale in legacy_sale_records:
                    legacy_sale.message_post(body=log_msg)

            old_term_line = self.env['property.payment.term.line'].browse(old_term_line_id)
            if old_term_line.exists():
                old_term_line.unlink()

            self.env['installment.update.log'].create({
                'site_id':          self.site_id.id,
                'old_installment':  old_name,
                'new_installment':  new_name,
                'substitution_date': fields.Datetime.now(),
                'performed_by':     self.env.user.id,
                'collection_count': count_ci,
                'sale_line_count':  count_sl,
                'legacy_line_count': count_ll,
            })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Installments Updated'),
                'message': _(
                    'Substituted %(count_ci)d collection installment(s), '
                    '%(count_sl)d property sale line(s), and %(count_ll)d legacy line(s). '
                    'Old installment "%(old)s" deleted — "%(new)s" now takes its position.'
                ) % {
                    'count_ci': count_ci,
                    'count_sl': count_sl,
                    'count_ll': count_ll,
                    'old': old_name,
                    'new': new_name,
                },
                'sticky': False,
                'type': 'success',
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
