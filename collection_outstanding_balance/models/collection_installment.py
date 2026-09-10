from odoo import models, fields, api
from dateutil.relativedelta import relativedelta

class CollectionInstallment(models.Model):
    _inherit = 'collection.installment'

    is_outstanding_progress = fields.Boolean(
        string="Is Outstanding Progress",
        compute="_compute_is_outstanding_progress",
        search="_search_is_outstanding_progress",
        help="True if it's a progress installment and Today is between (Due Date - Shift Days) and the Due Date."
    )

    def _compute_is_outstanding_progress(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if not rec.is_progress_based or not rec.due_date or rec.state == 'paid':
                rec.is_outstanding_progress = False
                continue
            
            # Find the shift configuration for this specific site
            shift_days = 30
            if rec.site_id:
                cfg = self.env['collection.progress.shift.config'].search([
                    ('site_id', '=', rec.site_id.id), 
                    ('active', '=', True)
                ], limit=1)
                if cfg:
                    shift_days = cfg.shift_days or 30

            start_date = rec.due_date - relativedelta(days=shift_days)
            
            if start_date <= today <= rec.due_date:
                rec.is_outstanding_progress = True
            else:
                rec.is_outstanding_progress = False

    def _search_is_outstanding_progress(self, operator, value):
        """ 
        Search method to use the computed field in XML domains!
        """
        today = fields.Date.context_today(self)
        
        # only unpaid, progress-based installments that actually have a due date
        installments = self.search([
            ('is_progress_based', '=', True), 
            ('due_date', '!=', False), 
            ('state', '!=', 'paid')
        ])
        
        valid_ids = []
        for rec in installments:
            shift_days = 30
            if rec.site_id:
                cfg = self.env['collection.progress.shift.config'].search([
                    ('site_id', '=', rec.site_id.id), 
                    ('active', '=', True)
                ], limit=1)
                if cfg:
                    shift_days = cfg.shift_days or 30
            
            start_date = rec.due_date - relativedelta(days=shift_days)
            
            # Check if Today is in the window
            if start_date <= today <= rec.due_date:
                valid_ids.append(rec.id)
        
        # Return the appropriate domain based on whether they searched for True or False
        if operator == '=' and value:
            return [('id', 'in', valid_ids)]
        else:
            return [('id', 'not in', valid_ids)]


    def action_open_collection_order_outstanding(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Collection Order',
            'res_model': 'collection.order',
            'view_mode': 'form',
            'res_id': self.collection_id.id,
            'target': 'current',
        }