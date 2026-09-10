from odoo import models, fields, api

class ContractArchive(models.Model):
    _name = "contract.archive"
    _description = "Permanent Editable Contract"
    _inherit = ["mail.thread", "mail.activity.mixin"]
     
    sale_id = fields.Many2one('property.sale', string='Property Sale', readonly=True)

    name = fields.Char(related='sale_id.contract_number', string='Contract Number', readonly=True)
    customer_name = fields.Char(string="Customer Name", tracking=True)
    property_name = fields.Char(string="Property Name")
    sales_no = fields.Char(string="Sales Number")
    date_created = fields.Date(string="Date Created", default=fields.Date.today)
    
    status = fields.Selection([
        ('active', 'Active'),
        ('signed', 'Signed'),
        ('void', 'Void'),
    ], default='active', string="Status", tracking=True)


    article_ids = fields.Many2many(
        "contract.archive.line", 
        "contract_archive_rel", 
        "contract_id",         
        "article_id",          
        string="Contract Articles"
    )
    rendered_html = fields.Html(string="Rendered HTML", sanitize=False)

    def action_set_signed(self):
            """Updates status to Signed for a single record"""
            self.ensure_one()  
            self.write({'status': 'signed'})
           
            
    def action_set_void(self):
        """Updates status to Void for a single record"""
        self.ensure_one()  
        self.write({'status': 'void'})

        
class ContractArchiveLine(models.Model):
    _name = "contract.archive.line" 
    _description = "Contract Article Line"
    _order = "sequence"
    _rec_name = "main_title"  

    contract_ids = fields.Many2many(
        "contract.archive", 
        "contract_archive_rel", 
        "article_id", 
        "contract_id", 
        string="Contracts"
    )
    
    sequence = fields.Integer(string="Sequence", default=10)
    main_title = fields.Char(string='Main Title', required=True)
    subtitle = fields.Char(string='Subtitle') 
    content = fields.Html(string="Article Content", sanitize=False)
    
    is_title_printed = fields.Boolean(string='Is Title Printed', default=False)
    is_dynamic_content = fields.Boolean(string='Is Dynamic Content', default=False)
    is_active = fields.Boolean(string="Active", default=True)
    dynamic_code = fields.Text(string='Dynamic Code')