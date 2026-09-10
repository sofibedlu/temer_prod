from odoo import _, models, fields
from odoo.exceptions import UserError
from markupsafe import Markup
import re
import logging

_logger = logging.getLogger(__name__)

class PropertySale(models.Model):
    _inherit = "property.sale"

    contract_section_template_id = fields.Many2one(
        "contract.section",
        string="Contract Template Section",
        required=True,
        help="Select the contract section to apply to this sale.",
    )
    contract_archive_id = fields.Many2one(
        "contract.archive", 
        string="Current Contract Archive"
    )
    
    def get_full_name(self):
        if not self.contract_id:
            return "—"
        
        names = []
        for person in self.contract_id:
            fname = getattr(person, 'first_name', '') or ''
            mname = getattr(person, 'father_name', '') or ''
            lname = getattr(person, 'gfather_name', '') or ''
            
            full = f"{fname} {mname} {lname}".strip()
            if full:
                names.append(full)
                
        return ", ".join(names) if names else "—"
    
    def action_print_contract(self):
        self.ensure_one()

        if not self.contract_section_template_id:
            raise UserError(_("A Contract Template must be selected before you can print."))

        return {
            "type": "ir.actions.act_window",
            "name": _("Contract Preview"),
            "res_model": "contract.preview.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_sale_id": self.id,
            },
        }
      
    def action_view_contract_details(self):
                """ 
                Finds the related Contract Archive and opens the form.
                """
                self.ensure_one()
                _logger.info("DEBUG: Searching for Archive with sales_no = %s", self.name)
                
        
                archive = self.env['contract.archive'].search([('sales_no', '=', self.name)], limit=1)
                
                if not archive:
                    _logger.warning("DEBUG: No archive found for %s", self.name)
                    raise UserError(_("No Contract Archive found for this sale number (%s).") % self.name)

            

                return {
                    'name': _('Contract Archive Details'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'contract.archive',
                    'view_mode': 'form',
                    'res_id': archive.id,            
                    'target': 'current', 
                    'context': {
                        'create': False,
                        'default_contract_ids': [(4, archive.id)] 
                    },    
                }
                
                
    def action_confirm(self):
        """ 
        Overloading the standard confirm action to 
        automatically create a contract archive.
        """
    
        res = super(PropertySale, self).action_confirm()

    
        if self.contract_section_template_id:
            try:
                self._create_contract_archive()
                self.message_post(body=_("Contract Archive generated successfully during confirmation."))
            except Exception as e:
            
                _logger.error("Failed to create contract archive: %s", str(e))
        
        return res            
    

    def action_approve_sale(self):
        self.ensure_one()
        
        res = super(PropertySale, self).action_approve_sale()

        contract_rec = self.env["contract.archive"].search(
            [("property_name", "=", self.property_id.name)],
            order="create_date desc",
            limit=1
        )

        if contract_rec:
            contract_rec.action_set_signed()
        else:
            _logger.warning(
                "No Contract Archive found for property: %s (Sale: %s)",
                self.property_id.name,
                self.name
            )

        return res
  
    def _create_contract_archive(self):
        self.ensure_one()
        contract = self.contract_id
        if not contract:
            return False

   
        buyer = contract.person_ids.filtered(lambda p: p.person_type == "buyers")[:1]
        full_buyer_name = f"{buyer.first_name or ''} {buyer.father_name or ''} {buyer.gfather_name or ''}".strip()

    
        article_commands = []
        
   
        template_sections = self.contract_section_template_id.section_content_ids.sorted('sequence')
        
        for section in template_sections:
            article_commands.append((0, 0, {
                'main_title': section.main_title or "No Title",
                'subtitle': section.subtitle or "",
                'content': section.content or "",
                'sequence': section.sequence,
                # Mapping additional fields from your model definition
                'is_title_printed': getattr(section, 'is_title_printed', False),
                'is_dynamic_content': getattr(section, 'is_dynamic_content', False),
                'is_active': True,
                'dynamic_code': getattr(section, 'dynamic_code', ''),
            }))


        archive_vals = {
            'sale_id': self.id,
            'name': contract.name or self.name or "New Archive",
            'customer_name': full_buyer_name or "Unknown",
            'property_name': self.property_id.name or "—",
            'sales_no': self.name or "—",
            'status': 'active',
            'article_ids': article_commands,
        }

        return self.env['contract.archive'].create(archive_vals)