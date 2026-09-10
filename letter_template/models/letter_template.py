from odoo import models, fields
from markupsafe import Markup


class LetterTemplate(models.Model):
    """
    Full letter template: one Header/Footer + ordered Body sections.
    render_full_letter(record, extra_values) assembles the complete HTML.
    """
    _name = 'letter.template'
    _description = 'Letter Template'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'name'

    name = fields.Char(string='Template Name', required=True, tracking=True)
    active = fields.Boolean(default=True, tracking=True)

    # ── Composition ───────────────────────────────────────────────────────────
    header_footer_id = fields.Many2one(
        'letter.header.footer',
        string='Header & Footer',
        ondelete='set null',
        tracking=True,
    )
    body_ids = fields.Many2many(
        'letter.body',
        'letter_template_body_rel',
        'template_id',
        'body_id',
        string='Letter Bodies',
    )

    subject = fields.Char(string='Subject', tracking=True)
    letter_type_id = fields.Many2one(
        'letter.type',
        string='Letter Type',
        ondelete='set null',
        tracking=True,
    )
    site_id = fields.Many2one(
        'property.site',
        string='Site',
        tracking=True,
        required=True,
    )
    director_id = fields.Many2one(
        'letter.director',
        string='Director',
        tracking=True,
    )
    notes = fields.Text(string='Internal Notes')

    # ── Inverse back-reference from the print wizard ──────────────────────────
    wizard_ids = fields.One2many(
        comodel_name='property.print.letter.wizard',
        inverse_name='letter_template_id',
        string='Used in Wizards',
        readonly=True,
    )

    # ── Render body only (for PDF — header/footer handled via fixed CSS) ─────
    def render_body_only(self, record=None, extra_values=None):
        """Renders only the body sections — no header or footer HTML."""
        self.ensure_one()
        from markupsafe import Markup
        parts = []
        for body in self.body_ids.sorted('sequence'):
            rendered = body.render_body(record=record, extra_values=extra_values)
            parts.append(Markup('<div class="letter-body-section" style="margin-bottom:15px;">'))
            parts.append(rendered)
            parts.append(Markup('</div>'))
        return Markup('').join(parts)

    # ── Render full (header + body + footer inline — for DOCX / preview) ─────
    def render_full_letter(self, record=None, extra_values=None):
        """
        Assemble the complete letter HTML:
            header (logo left | title center | hr below)
            → body sections (sorted by sequence)
            → footer (hr above | stamp + content centered)
        """
        self.ensure_one()
        parts = []
        hf = self.header_footer_id

        # ── Header ────────────────────────────────────────────────────────────
        if hf:
            logo_uri = hf.get_logo_data_uri()
            logo_html = (
                f'<img src="{logo_uri}" style="max-height:80px; width:auto;" alt="Logo"/>'
                if logo_uri else ''
            )
            center_html = str(hf.header_html) if hf.header_html else ''

            parts.append(Markup(
                '<div class="letter-header">'
                '<table style="width:100%; border-collapse:collapse; margin-bottom:6px;">'
                '<tr>'
                f'<td style="width:25%; text-align:left; vertical-align:middle;">{logo_html}</td>'
                f'<td style="width:50%; text-align:center; vertical-align:middle;">{center_html}</td>'
                '<td style="width:25%;"></td>'
                '</tr>'
                '</table>'
                '<hr style="border:none; border-top:2px solid #000; margin:4px 0 16px 0;"/>'
                '</div>'
            ))

        # ── Bodies ────────────────────────────────────────────────────────────
        for body in self.body_ids.sorted('sequence'):
            rendered_body = body.render_body(record=record, extra_values=extra_values)
            parts.append(Markup('<div class="letter-body-section" style="margin-bottom:15px;">'))
            parts.append(rendered_body)
            parts.append(Markup('</div>'))

        # ── Footer ────────────────────────────────────────────────────────────
        if hf:
            stamp_uri = hf.get_stamp_data_uri()
            stamp_html = (
                f'<img src="{stamp_uri}" style="max-height:120px; width:auto;" alt="Stamp"/>'
                if stamp_uri else ''
            )
            footer_content = str(hf.footer_html) if hf.footer_html else ''

            parts.append(Markup(
                '<div class="letter-footer">'
                '<hr style="border:none; border-top:2px solid #000; margin:0 0 10px 0;"/>'
                '<div style="text-align:center; width:100%;">'
                + (f'<div style="margin-bottom:6px;">{stamp_html}</div>' if stamp_html else '')
                + (f'<div>{footer_content}</div>' if footer_content else '')
                + '</div>'
                '</div>'
            ))

        return Markup('').join(parts)
