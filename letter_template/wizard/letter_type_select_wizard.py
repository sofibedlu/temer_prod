from odoo import models, fields, _


def _site_code_from_collection(collection):
    """
    Extract the first 3 uppercase letters from the site's COMPANY name linked to
    the collection order's property.
    """
    try:
        company_name = (
            collection.sale_id.property_id.site.company_id.name
            if collection and collection.sale_id and
               collection.sale_id.property_id and
               collection.sale_id.property_id.site and
               collection.sale_id.property_id.site.company_id
            else ''
        )
    except Exception:
        company_name = ''

    if not company_name:
        return ''
    letters = ''.join(c for c in company_name if c.isalpha())
    return letters[:3].upper().ljust(3, 'X') if letters else ''


class LetterTypeSelectWizard(models.TransientModel):
    """
    Step-1 wizard: user picks a Letter Type from a card-grid list.

    On confirm:model
      1. Resolves the site code from the collection order's property site
         (first 3 letters of site name, uppercased — e.g. Filtema → FIL)
      2. Looks up letter.type.prefix for the selected type (e.g. DL)
      3. Looks up letter.number.generator for the selected type
      4. Calls next_number(site_code, type_prefix) to atomically get the
         next formatted number — e.g. FIL/DL/0001/18
      5. Opens the Print Letter wizard pre-filled with type + number
    """
    _name = 'letter.type.select.wizard'
    _description = 'Select Letter Type'

    collection_id = fields.Many2one(
        'collection.order',
        string='Collection Order',
        required=True,
    )
    letter_type_id = fields.Many2one(
        'letter.type',
        string='Letter Type',
        required=True,
    )

    def action_confirm(self):
        self.ensure_one()

        # We generate the number in the next step (Print Letter Wizard) when the
        # template is selected, because the site code and director depend on the template.
        letter_number = 'Draft'
        
        import logging
        _logger = logging.getLogger(__name__)

        # Attempt to find the site of the collection order
        site_id = False
        if getattr(self.collection_id, 'site_id', False):
            site_id = self.collection_id.site_id.id
        elif getattr(self.collection_id, 'property_id', False) and getattr(self.collection_id.property_id, 'site', False):
            site_id = self.collection_id.property_id.site.id
        elif getattr(self.collection_id, 'sale_id', False) and getattr(self.collection_id.sale_id, 'property_id', False) and getattr(self.collection_id.sale_id.property_id, 'site', False):
            site_id = self.collection_id.sale_id.property_id.site.id

        _logger.info("Found site_id %s for collection_id %s", site_id, self.collection_id.id)

        template_id = False
        if site_id:
            # Look for a template that matches the selected letter type and the site
            template = self.env['letter.template'].search([
                ('letter_type_id', '=', self.letter_type_id.id),
                ('site_id', '=', site_id),
                ('active', '=', True)
            ], limit=1)
            
            _logger.info("Found template %s for letter_type_id %s and site_id %s", template, self.letter_type_id.id, site_id)
            
            if template:
                template_id = template.id

        context = {
            'default_collection_id': self.collection_id.id,
            'default_letter_type_id': self.letter_type_id.id,
            'default_letter_number': letter_number,
        }
        if template_id:
            context['default_letter_template_id'] = template_id

        # ── 5. Open Print Letter wizard ───────────────────────────────────────
        return {
            'type': 'ir.actions.act_window',
            'name': _('Print Collection Letter'),
            'res_model': 'property.print.letter.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': context,
        }
