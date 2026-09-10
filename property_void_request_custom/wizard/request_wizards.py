from odoo import models, fields

class AmendmentRequestWizard(models.TransientModel):
    _inherit = 'amendment.request.wizard'

    attached_file = fields.Binary(string='Attachment', attachment=True)
    attached_file_name = fields.Char(string='File Name')

    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')

    def action_submit_request(self):
        res = super(AmendmentRequestWizard, self).action_submit_request()
        
        if self.attachment_ids:
            new_request = self.env['property.schedule.amendment.request'].search([
                ('collection_id', '=', self.collection_id.id)
            ], order='id desc', limit=1)
            
            if new_request:
                new_request.sudo().write({
                    'attachment_ids': [(6, 0, self.attachment_ids.ids)]
                })

                # Update attachment ownership
                self.attachment_ids.sudo().write({
                    'res_model': 'property.schedule.amendment.request',
                    'res_id': new_request.id
                })
                
        return res


class VoidContractWizard(models.TransientModel):
    _inherit = 'void.contract.wizard'

    attached_file = fields.Binary(string='Attachment', attachment=True)
    attached_file_name = fields.Char(string='File Name')

    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')

    def action_submit_request(self): 
        res = super(VoidContractWizard, self).action_submit_request()
        
        if self.attachment_ids:
            # Build domain
            domain = []
            if hasattr(self, 'sale_id') and self.sale_id:
                domain.append(('sale_id', '=', self.sale_id.id))
            elif hasattr(self, 'collection_id') and self.collection_id:
                domain.append(('collection_id', '=', self.collection_id.id))
            
            new_request = self.env['property.contract.void.request'].search(domain, order='id desc', limit=1)
            
            if new_request:
                new_request.sudo().write({
                    'attachment_ids': [(6, 0, self.attachment_ids.ids)]
                })

                # Update attachment ownership
                self.attachment_ids.sudo().write({
                    'res_model': 'property.contract.void.request',
                    'res_id': new_request.id
                })
                
        return res