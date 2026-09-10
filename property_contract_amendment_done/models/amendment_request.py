from odoo import models, fields
from markupsafe import Markup

class PropertyScheduleAmendmentRequest(models.Model):
    _inherit = 'property.schedule.amendment.request'

    state = fields.Selection(selection_add=[
        ('done', 'Done')
    ], ondelete={'done': 'set default'})

    def action_mark_done(self):
        for record in self:
            record.write({'state': 'done'})
            record.message_post(body=Markup("<b>Amendment Completed</b><br/>The contract team has marked this amendment as done."))