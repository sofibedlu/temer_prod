from odoo import models, fields

class PropertyScheduleAmendmentRequest(models.Model):
    _inherit = 'property.schedule.amendment.request'

    attached_file = fields.Binary(string='Attachment', attachment=True)
    attached_file_name = fields.Char(string='File Name')

    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')