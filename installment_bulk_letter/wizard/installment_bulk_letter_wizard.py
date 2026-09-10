import base64
import io
import re
import zipfile
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class InstallmentBulkLetterLine(models.TransientModel):
    """
    One selectable row per installment shown in the wizard list.
    Each row represents a single collection.installment record.
    """
    _name = 'installment.bulk.letter.line'
    _description = 'Installment Bulk Letter Line'
    _order = 'installment_id'

    wizard_id = fields.Many2one(
        'installment.bulk.letter.wizard',
        string='Wizard',
        ondelete='cascade',
        required=True,
    )
    selected = fields.Boolean(string='Select', default=True)

    installment_id = fields.Many2one(
        'collection.installment',
        string='Installment',
        readonly=True,
    )
    installment_name = fields.Char(
        string='Installment Name',
        related='installment_id.name',
        readonly=True,
    )
    collection_ref = fields.Char(
        string='Collection Ref',
        related='installment_id.collection_id.name',
        readonly=True,
    )
    partner_name = fields.Char(
        string='Customer',
        related='installment_id.collection_id.partner_id.name',
        readonly=True,
    )
    property_name = fields.Char(
        string='Property',
        related='installment_id.property_id.name',
        readonly=True,
    )
    contract_number = fields.Char(
        string='Contract No.',
        related='installment_id.collection_id.contract_number',
        readonly=True,
    )
    due_date = fields.Date(
        string='Due Date',
        related='installment_id.due_date',
        readonly=True,
    )
    amount_residual = fields.Monetary(
        string='Remaining',
        related='installment_id.amount_residual',
        readonly=True,
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='installment_id.currency_id',
        readonly=True,
    )
    state = fields.Selection(
        related='installment_id.state',
        string='Status',
        readonly=True,
    )


class InstallmentBulkLetterWizard(models.TransientModel):
    """
    Wizard to generate bulk DOCX letters per installment.

    Flow:
      1. Pick a Site.
      2. Pick an Installment Name (filtered to that site) — loads all
         installments across all active collection orders that share that name.
      3. Pick a Letter Type → the matching template auto-resolves.
      4. Set a Letter Date (defaults to today).
      5. The list below shows every matching installment with a checkbox.
      6. Click «Generate Letters» → one DOCX per selected installment,
         all bundled in a ZIP download.
    """
    _name = 'installment.bulk.letter.wizard'
    _description = 'Installment Bulk Letter Wizard'

    # ── Header filters ────────────────────────────────────────────────────────
    site_id = fields.Many2one(
        'property.site',
        string='Site',
        required=True,
    )

    installment_name_filter = fields.Many2one(
        'collection.installment',
        string='Installment Name',
        help='Select an installment to load only rows sharing that name across all orders for this site.',
        domain="[('collection_id.site_id', '=', site_id)]",
        context={'active_test': False},
    )

    letter_type_id = fields.Many2one(
        'letter.type',
        string='Letter Type',
        required=True,
    )
    letter_template_id = fields.Many2one(
        'letter.template',
        string='Letter Template',
        domain="[('letter_type_id', '=', letter_type_id), ('site_id', '=', site_id)]",
        help='Auto-resolved when you pick a Letter Type + Site. You can override it.',
    )
    letter_date = fields.Date(
        string='Letter Date',
        required=True,
        default=fields.Date.context_today,
    )

    # ── Installment lines ─────────────────────────────────────────────────────
    line_ids = fields.One2many(
        'installment.bulk.letter.line',
        'wizard_id',
        string='Installments',
    )

    # ── Output ────────────────────────────────────────────────────────────────
    generated_file = fields.Binary(string='Generated ZIP', readonly=True)
    generated_filename = fields.Char(readonly=True)
    state = fields.Selection(
        [('draft', 'Draft'), ('done', 'Done')],
        default='draft',
    )
    
    # Hidden fields to prevent onchange from firing on random UI reloads
    loaded_site_id = fields.Many2one('property.site')
    loaded_filter_id = fields.Many2one('collection.installment')

    # ── Onchange: clear installment filter when site changes ─────────────────
    @api.onchange('site_id')
    def _onchange_site_id(self):
        self.installment_name_filter = False

    # ── Onchange: auto-resolve template ───────────────────────────────────────
    @api.onchange('letter_type_id', 'site_id')
    def _onchange_letter_type_or_site(self):
        self.letter_template_id = False
        if self.letter_type_id and self.site_id:
            template = self.env['letter.template'].search([
                ('letter_type_id', '=', self.letter_type_id.id),
                ('site_id', '=', self.site_id.id),
                ('active', '=', True),
            ], limit=1)
            if template:
                self.letter_template_id = template.id

    # ── Onchange: auto-load installments ──────────────────────────────────────
    @api.onchange('site_id', 'installment_name_filter')
    def _onchange_filters_load_lines(self):
        """Automatically load matching installments when filters change."""
        if not self.site_id:
            self.line_ids = [(5, 0, 0)]
            self.loaded_site_id = False
            self.loaded_filter_id = False
            return

        # Only reload if the filter actually changed!
        # This prevents the UI from randomly wiping out manual selection states (like Deselect All).
        if self.site_id == self.loaded_site_id and self.installment_name_filter == self.loaded_filter_id:
            return

        self.loaded_site_id = self.site_id
        self.loaded_filter_id = self.installment_name_filter

        self.line_ids = [(5, 0, 0)]  # Clear existing

        domain = [
            ('site_id', '=', self.site_id.id),
            ('collection_id.state', '=', 'active'),
        ]
        if self.installment_name_filter:
            domain.append(('name', '=', self.installment_name_filter.name))

        installments = self.env['collection.installment'].with_context(active_test=False).search(
            domain,
            order='due_date asc, id asc',
        )

        lines = []
        for inst in installments:
            lines.append((0, 0, {
                'installment_id': inst.id,
                'selected': True,
            }))
        
        self.line_ids = lines

    # ── Load installments button ───────────────────────────────────────────────
    def action_load_installments(self):
        """
        Query collection.installment records for the selected site,
        optionally filtered by installment_name_filter, and populate line_ids.
        """
        self.ensure_one()
        if not self.site_id:
            raise UserError(_('Please select a Site first.'))

        domain = [
            ('site_id', '=', self.site_id.id),
            ('collection_id.state', '=', 'active'),
        ]
        # filter_name comes from the selected installment record's .name
        # so all installments that share that name across every order are loaded.
        if self.installment_name_filter:
            domain.append(('name', '=', self.installment_name_filter.name))

        installments = self.env['collection.installment'].with_context(active_test=False).search(
            domain,
            order='due_date asc, id asc',
        )

        # Delete existing lines via SQL to bypass ORM cache, then create fresh ones.
        # Using write() with (5,0,0) on a transient model that was just saved
        # can silently fail if the ORM still holds unsaved state in memory.
        self.env['installment.bulk.letter.line'].search(
            [('wizard_id', '=', self.id)]
        ).unlink()

        lines = []
        for inst in installments:
            lines.append((0, 0, {
                'installment_id': inst.id,
                'selected': True,
            }))
        # Use write() so the DB rows are committed before the reload
        self.write({'line_ids': lines})

        # Re-open wizard so the list is visible
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }

    # ── Select / deselect all ─────────────────────────────────────────────────
    def action_select_all(self):
        self.action_load_installments()  # Ensure lines exist in DB
        for line in self.line_ids:
            line.selected = True
        return self._reload()

    def action_deselect_all(self):
        self.action_load_installments()  # Ensure lines exist in DB
        for line in self.line_ids:
            line.selected = False
        return self._reload()

    def _reload(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }

    # ── Main generation action ────────────────────────────────────────────────
    def action_generate_letters(self):
        """
        For every selected installment line:
          1. Render the letter HTML via letter.template.render_full_letter.
          2. Wrap it in a minimal DOCX (altChunk approach — no extra libraries).
          3. Add it to a ZIP.
        Then serve the ZIP as a file download.
        """
        self.ensure_one()

        if not self.letter_template_id:
            raise UserError(_('Please select a Letter Template.'))

        # ── Read selected lines directly from DB to avoid ORM cache issues ──
        # self.line_ids on a transient model can be stale after the form
        # saves; querying by wizard_id guarantees we see the latest values.
        selected_lines = self.env['installment.bulk.letter.line'].search([
            ('wizard_id', '=', self.id),
            ('selected', '=', True),
            ('installment_id', '!=', False),
        ])
        if not selected_lines:
            raise UserError(_(
                'No installments are selected. '
                'Make sure you loaded the list and checked at least one row.'
            ))

        # ── Resolve letter-number components once ─────────────────────────
        generator = self.env['letter.number.generator'].search([
            ('letter_type_id', '=', self.letter_type_id.id),
            ('active', '=', True),
        ], limit=1)

        site_code = self._compute_site_code()
        type_prefix = self._compute_type_prefix()
        dir_code = self._compute_dir_code()

        letter_date = self.letter_date or fields.Date.context_today(self)

        # ── Build ZIP ─────────────────────────────────────────────────────
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for line in selected_lines:
                installment = line.installment_id

                # ── Unique, strictly-incrementing letter number per doc ───
                # generator.next_number() does SELECT FOR UPDATE + write(),
                # but Odoo's ORM caches current_value in memory, so repeated
                # calls within the same transaction would read the cached
                # value and produce the same number.  Invalidating the record
                # cache after each write forces the next SELECT to hit the DB.
                if generator:
                    letter_number = generator.next_number(
                        site_code=site_code,
                        director_code=dir_code,
                        type_prefix=type_prefix,
                    )
                    # Force the ORM to discard its cached current_value so
                    # the next iteration reads the freshly-written DB value.
                    generator.invalidate_recordset()
                else:
                    letter_number = 'N/A'

                html_str = self._render_letter_html(
                    installment, letter_number, letter_date
                )
                html_str = self._post_process_html(html_str)
                docx_bytes = self._build_docx(html_str)

                filename = self._make_filename(installment, letter_number)
                zf.writestr(filename, docx_bytes)

        zip_data = base64.b64encode(zip_buffer.getvalue())
        zip_name = (
            f"Letters_{self.site_id.name}_{self.letter_date}.zip"
            .replace(' ', '_')
        )
        self.write({
            'generated_file': zip_data,
            'generated_filename': zip_name,
            'state': 'done',
        })

        return self._download_action()

    # ── Download action (also callable from the "Download" button) ────────────
    def action_download(self):
        self.ensure_one()
        if not self.generated_file:
            raise UserError(_('No file generated yet. Click «Generate Letters» first.'))
        return self._download_action()

    def _download_action(self):
        attachment = self.env['ir.attachment'].create({
            'name': self.generated_filename or 'letters.zip',
            'type': 'binary',
            'datas': self.generated_file,
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/zip',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    # ── Letter-number helpers ─────────────────────────────────────────────────
    def _compute_site_code(self):
        tmpl = self.letter_template_id
        if not tmpl or not tmpl.site_id:
            return 'XXX'
        company = tmpl.site_id.company_id
        if company and getattr(company, 'abbreviation', None):
            return company.abbreviation.upper()
        letters = ''.join(c for c in (tmpl.site_id.name or '') if c.isalpha())
        return letters[:3].upper().ljust(3, 'X') if letters else 'XXX'

    def _compute_type_prefix(self):
        if not self.letter_type_id:
            return ''
        rec = self.env['letter.type.prefix'].search(
            [('letter_type_id', '=', self.letter_type_id.id)], limit=1
        )
        return rec.prefix if rec else ''

    def _compute_dir_code(self):
        tmpl = self.letter_template_id
        if tmpl and tmpl.director_id and tmpl.director_id.name:
            return tmpl.director_id.name.upper()
        return ''

    # ── HTML rendering ────────────────────────────────────────────────────────
    def _render_letter_html(self, installment, letter_number, letter_date):
        extra = {
            'letter_number': letter_number,
            'letter_date': str(letter_date),
        }
        try:
            html = self.letter_template_id.render_full_letter(
                record=installment, extra_values=extra
            )
            return (
                '<!DOCTYPE html>'
                '<html><head><meta charset="utf-8"></head>'
                f'<body>{html}</body></html>'
            )
        except Exception as exc:
            _logger.error(
                'Letter render failed for installment %s: %s', installment.id, exc
            )
            return (
                '<!DOCTYPE html><html><head><meta charset="utf-8"></head>'
                f'<body><p>Letter generation failed for installment: '
                f'{installment.name}</p></body></html>'
            )

    def _post_process_html(self, html_str):
        """Fix image sizes, inject minimal font CSS, strip inline footers."""
        html_str = html_str.replace(
            'style="max-height:100px;"',
            'width="150" height="80" style="width:150px; height:80px;"',
        )
        html_str = html_str.replace(
            'style="max-height: 140px; width: auto;"',
            'width="180" height="140" style="width:180px; height:140px;"',
        )

        font_css = (
            '<style>'
            "body { font-family: 'Arial Unicode MS', 'Noto Sans Ethiopic', sans-serif;"
            ' font-size: 11pt; }'
            ' table { border-collapse: collapse; width: 100%; }'
            '</style>'
        )
        if '</head>' in html_str:
            html_str = html_str.replace('</head>', font_css + '</head>')
        else:
            html_str = font_css + html_str

        # Remove any stray footer divs that duplicate the DOCX footer
        html_str = re.sub(
            r'<div[^>]*class=["\']footer["\'][^>]*>.*?</div>',
            '',
            html_str,
            flags=re.DOTALL | re.IGNORECASE,
        )
        return html_str

    # ── DOCX builder (pure stdlib — no python-docx or extra libs) ────────────
    def _build_docx(self, html_str):
        """
        Produce a valid .docx using the Open XML altChunk approach:
        the HTML is embedded directly in the zip as chunk.htm and referenced
        from document.xml via <w:altChunk>.  Word/LibreOffice will render it.
        """
        docx_io = io.BytesIO()
        with zipfile.ZipFile(docx_io, 'w', zipfile.ZIP_DEFLATED) as zf:

            zf.writestr('[Content_Types].xml', (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                '<Default Extension="xml"  ContentType="application/xml"/>'
                '<Default Extension="htm"  ContentType="text/html"/>'
                '<Override PartName="/word/document.xml"'
                '  ContentType="application/vnd.openxmlformats-officedocument'
                '.wordprocessingml.document.main+xml"/>'
                '<Override PartName="/word/settings.xml"'
                '  ContentType="application/vnd.openxmlformats-officedocument'
                '.wordprocessingml.settings+xml"/>'
                '</Types>'
            ))

            zf.writestr('_rels/.rels', (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1"'
                '  Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"'
                '  Target="word/document.xml"/>'
                '</Relationships>'
            ))

            zf.writestr('word/_rels/document.xml.rels', (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="htmlChunk"'
                '  Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/aFChunk"'
                '  Target="chunk.htm"/>'
                '<Relationship Id="rIdSettings"'
                '  Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings"'
                '  Target="settings.xml"/>'
                '</Relationships>'
            ))

            zf.writestr('word/document.xml', (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
                '            xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                '<w:body>'
                '<w:altChunk r:id="htmlChunk"/>'
                '<w:sectPr>'
                '  <w:pgMar w:top="720" w:right="720" w:bottom="720" w:left="720"/>'
                '</w:sectPr>'
                '</w:body>'
                '</w:document>'
            ))

            zf.writestr('word/settings.xml', (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                '<w:compat>'
                '  <w:compatSetting w:name="compatibilityMode"'
                '    w:uri="http://schemas.microsoft.com/office/word" w:val="15"/>'
                '</w:compat>'
                '</w:settings>'
            ))

            # UTF-8 BOM so Word decodes Ethiopic script correctly
            zf.writestr('word/chunk.htm', html_str.encode('utf-8-sig'))

        return docx_io.getvalue()

    # ── Filename helper ────────────────────────────────────────────────────────
    @staticmethod
    def _make_filename(installment, letter_number):
        def safe(s):
            return re.sub(r'[^\w\s-]', '', str(s or '')).strip().replace(' ', '_')

        partner = safe(installment.collection_id.partner_id.name or 'Customer')
        col_ref = safe(installment.collection_id.name or installment.collection_id.id)
        inst_name = safe(installment.name or 'Installment')
        lnum = safe(letter_number)
        return f'{partner}_{col_ref}_{inst_name}_{lnum}_{installment.id}.docx'
