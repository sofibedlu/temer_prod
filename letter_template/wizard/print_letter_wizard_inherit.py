from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PropertyPrintLetterWizardInherit(models.TransientModel):
    """
    Extends property.print.letter.wizard:
      - Hides  letter_type       (base Selection — replaced by letter_type_id)
      - Hides  letterhead_id     (handled inside letter.template)
      - Hides  custom_template_id (legacy from collection_letter_template)
      - Adds   letter_type_id   → letter.type   (filter templates by type)
      - Adds   letter_template_id → letter.template (filtered by letter_type_id)
      - Adds   action_preview_letter button
    """
    _inherit = 'property.print.letter.wizard'

    @api.model
    def default_get(self, fields_list):
        res = super(PropertyPrintLetterWizardInherit, self).default_get(fields_list)
        
        # If letter_template_id is not already provided but we have type and collection
        if 'letter_template_id' in fields_list and not res.get('letter_template_id'):
            collection_id = res.get('collection_id') or self.env.context.get('default_collection_id')
            letter_type_id = res.get('letter_type_id') or self.env.context.get('default_letter_type_id')
            
            if collection_id and letter_type_id:
                collection = self.env['collection.order'].browse(collection_id)
                site_id = False
                try:
                    site = collection.property_id.site
                    if site:
                        site_id = site.id
                except Exception:
                    pass
                    
                if site_id:
                    template = self.env['letter.template'].search([
                        ('letter_type_id', '=', letter_type_id),
                        ('site_id', '=', site_id),
                        ('active', '=', True)
                    ], limit=1)
                    if template:
                        res['letter_template_id'] = template.id
                        
                        # Also generate the letter number instantly so the UI isn't stuck on "Draft"
                        if 'letter_number' in fields_list:
                            generator = self.env['letter.number.generator'].search(
                                [('letter_type_id', '=', letter_type_id), ('active', '=', True)], limit=1
                            )
                            if generator:
                                site_code = 'XXX'
                                if template.site_id.company_id and template.site_id.company_id.abbreviation:
                                    site_code = template.site_id.company_id.abbreviation.upper()
                                elif template.site_id.name:
                                    letters = ''.join(c for c in template.site_id.name if c.isalpha())
                                    site_code = letters[:3].upper().ljust(3, 'X') if letters else 'XXX'

                                prefix_rec = self.env['letter.type.prefix'].search(
                                    [('letter_type_id', '=', letter_type_id)], limit=1
                                )
                                type_prefix = prefix_rec.prefix if prefix_rec else ''

                                dir_code = ''
                                if template.director_id and template.director_id.name:
                                    dir_code = template.director_id.name.upper()

                                res['letter_number'] = generator.next_number(
                                    site_code=site_code,
                                    director_code=dir_code,
                                    type_prefix=type_prefix
                                )
        return res

    # ── Letter Type — filters the template dropdown ───────────────────────────
    letter_type_id = fields.Many2one(
        comodel_name='letter.type',
        string='Letter Type',
        ondelete='set null',
        help="Select a letter type to filter the available templates.",
    )

    # ── Letter Template — filtered by the selected letter type ────────────────
    letter_template_id = fields.Many2one(
        comodel_name='letter.template',
        string='Letter Template',
        required=True,
        ondelete='restrict',
        domain="letter_type_id and [('letter_type_id', '=', letter_type_id)] or []",
        help="Select a template. Pick a Letter Type first to filter the list.",
    )

    # ── When template changes, generate the letter number ─────────────────────
    @api.onchange('letter_template_id')
    def _onchange_letter_template_id(self):
        if self.letter_template_id and self.letter_type_id:
            # Generate the letter number based on the template's site
            generator = self.env['letter.number.generator'].search(
                [('letter_type_id', '=', self.letter_type_id.id), ('active', '=', True)], limit=1
            )
            if generator:
                # 1. Site code: Use company abbreviation if it exists, otherwise fallback to site name
                site_code = 'XXX'
                if self.letter_template_id.site_id:
                    if self.letter_template_id.site_id.company_id and self.letter_template_id.site_id.company_id.abbreviation:
                        # Use exactly the abbreviation
                        site_code = self.letter_template_id.site_id.company_id.abbreviation.upper()
                    else:
                        # Fallback to the first 3 letters of the site name
                        site_name = self.letter_template_id.site_id.name or ''
                        letters = ''.join(c for c in site_name if c.isalpha())
                        site_code = letters[:3].upper().ljust(3, 'X') if letters else 'XXX'

                # 2. Type prefix
                prefix_rec = self.env['letter.type.prefix'].search(
                    [('letter_type_id', '=', self.letter_type_id.id)], limit=1
                )
                type_prefix = prefix_rec.prefix if prefix_rec else ''

                # 3. Director code from the template's director
                dir_code = ''
                if self.letter_template_id.director_id and self.letter_template_id.director_id.name:
                    dir_code = self.letter_template_id.director_id.name.upper()

                # Generate
                self.letter_number = generator.next_number(
                    site_code=site_code,
                    director_code=dir_code,
                    type_prefix=type_prefix
                )

    # ── When type changes, clear the template so the user picks a new one ─────
    @api.onchange('letter_type_id')
    def _onchange_letter_type_id(self):
        if self.letter_template_id and self.letter_template_id.letter_type_id != self.letter_type_id:
            self.letter_template_id = False

    # ── Preview action ────────────────────────────────────────────────────────
    def action_preview_letter(self):
        """
        Opens the Letter Preview Wizard pre-filled with values from this wizard.
        """
        self.ensure_one()

        if not self.installment_id:
            raise UserError(_("Please select an Installment first."))
        if not self.letter_template_id:
            raise UserError(_("Please select a Letter Template to preview."))

        preview = self.env['letter.preview.wizard'].create({
            'installment_id': self.installment_id.id,
            'letter_template_id': self.letter_template_id.id,
            'letter_date': self.letter_date,
            
            'letter_number': self.letter_number or '',
        })

        preview.preview_html = preview._render()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Letter Preview'),
            'res_model': 'letter.preview.wizard',
            'res_id': preview.id,
            'view_mode': 'form',
            'target': 'new',
        }
