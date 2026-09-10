from odoo import models, fields, api
from datetime import date


def _ethiopian_year_today():
    """Return the last 2 digits of the current Ethiopian year."""
    today = date.today()
    if today.month > 9 or (today.month == 9 and today.day >= 11):
        eth_year = today.year - 7
    else:
        eth_year = today.year - 8
    return str(eth_year)[-2:]


def _site_code(site_name):
    """
    Return the first 3 uppercase letters of a site name.
    Example: 'Filtema' → 'FIL'
    Falls back to 'XXX' if the name is too short or empty.
    """
    if not site_name:
        return 'XXX'
    letters = ''.join(c for c in site_name if c.isalpha())
    return letters[:3].upper().ljust(3, 'X')


class LetterNumberGenerator(models.Model):
    """
    Configurable letter number sequence per letter type.

    Full number format:
        <SITE_CODE> / <TYPE_PREFIX> / <ZERO_PADDED_SEQ> / <ETH_YEAR>

    Example (site=Filtema, prefix=DL, seq=1, year=18):
        FIL/DL/0001/18

    The site code is passed at generation time from the collection order.
    The type prefix comes from letter.type.prefix.
    """
    _name = 'letter.number.generator'
    _description = 'Letter Number Generator'
    _rec_name = 'letter_type_id'
    _order = 'letter_type_id'

    # ── Configuration ─────────────────────────────────────────────────────────
    letter_type_id = fields.Many2one(
        'letter.type',
        string='Letter Type',
        required=True,
        ondelete='cascade',
    )
    length = fields.Integer(
        string='Number Length',
        default=4,
        help="Total digits for the numeric part, zero-padded. Example: 4 → 0001",
    )
    start_from = fields.Integer(
        string='Start From',
        default=1,
        help="The first number to use when the sequence is reset or first created.",
    )
    current_value = fields.Integer(
        string='Current Value',
        default=0,
        help="Last number that was issued. 0 means no number has been generated yet.",
    )
    suffix = fields.Char(
        string='Suffix (Ethiopian Year)',
        default=lambda self: _ethiopian_year_today(),
        help="Last 2 digits of the Ethiopian year. Auto-filled on creation.",
    )
    director_id = fields.Many2one(
        'letter.director',
        string='Director',
        ondelete='set null',
        help="Director whose name code (first 3 letters) appears after the site code.",
    )
    active = fields.Boolean(default=True)

    # ── Preview (without site — site is dynamic at generation time) ───────────
    preview = fields.Char(
        string='Next Number Preview',
        compute='_compute_preview',
        store=False,
    )

    @api.depends('length', 'current_value', 'start_from', 'suffix', 'letter_type_id', 'director_id')
    def _compute_preview(self):
        for rec in self:
            nxt = (rec.current_value or 0) + 1
            if nxt < (rec.start_from or 1):
                nxt = rec.start_from or 1
            prefix_rec = rec.env['letter.type.prefix'].search(
                [('letter_type_id', '=', rec.letter_type_id.id)], limit=1
            )
            prefix = prefix_rec.prefix if prefix_rec else ''
            # Director code from the linked director record
            dir_code = ''
            if rec.director_id and rec.director_id.name:
                dir_code = rec.director_id.name.upper()
            rec.preview = rec._format(nxt, site_code='SITE', director_code=dir_code, type_prefix=prefix)

    # ── Constraints ───────────────────────────────────────────────────────────
    _sql_constraints = [
        ('letter_type_uniq', 'unique(letter_type_id)',
         'A number generator already exists for this Letter Type.'),
    ]

    # ── Public API ────────────────────────────────────────────────────────────
    def next_number(self, site_code='', director_code='', type_prefix=''):
        """
        Atomically increments current_value and returns the formatted number.

        Args:
            site_code     : first 3 letters of the site name (e.g. 'FIL')
            director_code : first 3 letters of the director name (e.g. 'AHM')
            type_prefix   : letter type prefix (e.g. 'DL')

        Returns:
            str — e.g. 'FIL/AHM/DL/0001/18'
        """
        self.ensure_one()
        self.env.cr.execute(
            'SELECT current_value FROM letter_number_generator '
            'WHERE id = %s FOR UPDATE',
            (self.id,)
        )
        row = self.env.cr.fetchone()
        current = row[0] if row else 0
        nxt = current + 1
        if nxt < (self.start_from or 1):
            nxt = self.start_from or 1
        self.write({'current_value': nxt})
        return self._format(nxt, site_code=site_code, director_code=director_code, type_prefix=type_prefix)

    def reset_sequence(self):
        """Resets current_value to 0 so the next call starts from start_from."""
        self.ensure_one()
        self.current_value = 0

    # ── Internal ──────────────────────────────────────────────────────────────
    def _format(self, number, site_code='', director_code='', type_prefix=''):
        """
        Build the full letter number:
            SITE / DIRECTOR / TYPE_PREFIX / ZERO_PADDED_SEQ / ETH_YEAR

        Parts that are empty are omitted.
        Example: FIL/AHM/DL/0001/18
        """
        self.ensure_one()
        length = max(1, self.length or 4)
        num_str = str(number).zfill(length)

        parts = []
        if site_code:
            parts.append(site_code.upper())
        if director_code:
            parts.append(director_code.upper())
        if type_prefix:
            parts.append(type_prefix)
        parts.append(num_str)
        if self.suffix:
            parts.append(self.suffix)

        return '/'.join(parts)
