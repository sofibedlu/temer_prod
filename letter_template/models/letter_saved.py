from odoo import models, fields


class LetterSaved(models.Model):
    """
    Permanent record of a rendered letter.
    Created automatically when the user prints (PDF) or downloads (DOCX)
    from the Letter Preview Wizard.
    """
    _name = 'letter.saved'
    _description = 'Saved Letter'
    _rec_name = 'letter_number'
    _order = 'create_date desc'

    # ── Links ─────────────────────────────────────────────────────────────────
    collection_id = fields.Many2one(
        'collection.order',
        string='Collection Order',
        ondelete='cascade',
        index=True,
    )
    installment_id = fields.Many2one(
        'collection.installment',
        string='Installment',
        ondelete='set null',
    )
    letter_template_id = fields.Many2one(
        'letter.template',
        string='Letter Template',
        ondelete='set null',
    )
    letter_type_id = fields.Many2one(
        'letter.type',
        string='Letter Type',
        related='letter_template_id.letter_type_id',
        store=True,
    )

    # ── Letter metadata ───────────────────────────────────────────────────────
    letter_number = fields.Char(string='Letter Number', required=True)
    letter_date = fields.Date(string='Letter Date')
    printed_by = fields.Many2one(
        'res.users',
        string='Printed By',
        default=lambda self: self.env.user,
        readonly=True,
    )
    action = fields.Selection(
        [('pdf', 'PDF'), ('docx', 'DOCX'), ('saved', 'Saved Manually')],
        string='Action',
        required=True,
    )

    # ── Rendered content ──────────────────────────────────────────────────────
    content_html = fields.Html(
        string='Letter Content',
        sanitize=False,
    )
