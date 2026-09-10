from odoo import models, fields

class CollectionSmsTemplate(models.Model):
    _name = 'collection.sms.template'
    _description = 'Collection SMS Template'

    name = fields.Char(string="Template Name", required=True)
    template_type = fields.Selection([
        ('first', 'First Reminder (Manual via Wizard)'),
        ('second', 'Second Reminder (Auto on Due Date)'),
        ('third', 'Third Reminder (Auto when Overdue)'),
        ('thank_you', 'Thank You (Auto on Payment)')
    ], string="Template Type", required=True)
    
    body = fields.Html(
        string="Message Body", 
        required=True,
        help="Use placeholders: {company_name}, {company_name_amharic}, {amount}, {due_date}, {due_date_ec}"
    )