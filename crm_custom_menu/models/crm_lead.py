from odoo import models, fields,_

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # internal_rating = fields.Selection([
    #     ('low', 'Low'),
    #     ('medium', 'Medium'),
    #     ('high', 'High'),
    # ], string='Internal Rating')
    def action_save_crm_records(self):
 
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'current',
        }
 #   source_id = fields.Many2one('utm.source', string="Source", tracking=True, required=True)
