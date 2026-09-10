import base64
import imghdr

from odoo import models, fields


class LetterHeaderFooter(models.Model):
    _name = 'letter.header.footer'
    _description = 'Letter Header & Footer'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'name'

    name = fields.Char(string='Name', required=True, tracking=True)
    active = fields.Boolean(default=True, tracking=True)

    # ── Header ────────────────────────────────────────────────────────────────
    header_html = fields.Html(
        string='Header Content',
        sanitize=False,
        help="HTML content rendered at the top of the letter.",
    )
    header_logo = fields.Binary(string='Header Logo', attachment=True)
    header_logo_filename = fields.Char(string='Logo Filename')

    # ── Footer ────────────────────────────────────────────────────────────────
    footer_html = fields.Html(
        string='Footer Content',
        sanitize=False,
        help="HTML content rendered at the bottom of the letter.",
    )
    footer_stamp = fields.Binary(
        string='Footer Stamp / Signature Image',
        attachment=True,
    )
    footer_stamp_filename = fields.Char(string='Stamp Filename')

    notes = fields.Text(string='Internal Notes')

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _binary_to_data_uri(self, binary_value, filename=None):
        """
        Convert a Binary field value (bytes or base64 string) to a
        data URI string suitable for use in an <img src="..."> attribute.

        Odoo Binary fields with attachment=True return the value as a
        base64-encoded string (not raw bytes). This method handles both
        cases safely and auto-detects the MIME type from the image data.
        """
        if not binary_value:
            return ''

        # Normalise to a base64 string
        if isinstance(binary_value, bytes):
            # Could be raw bytes or base64-encoded bytes
            try:
                # Try to decode as UTF-8 base64 string first
                b64_str = binary_value.decode('utf-8')
                # Validate it is actually base64 by decoding
                raw = base64.b64decode(b64_str)
            except Exception:
                # It's raw binary — encode it
                raw = binary_value
                b64_str = base64.b64encode(raw).decode('utf-8')
        else:
            # Already a string (Odoo attachment=True returns str)
            b64_str = binary_value
            try:
                raw = base64.b64decode(b64_str)
            except Exception:
                return ''

        # Detect MIME type from raw bytes
        mime = 'image/png'  # safe default
        try:
            img_type = imghdr.what(None, h=raw)
            if img_type:
                mime = f'image/{img_type}'
        except Exception:
            pass

        # Fallback: use filename extension if imghdr failed
        if mime == 'image/png' and filename:
            ext = (filename.rsplit('.', 1)[-1] or '').lower()
            mime_map = {
                'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
                'png': 'image/png',  'gif': 'image/gif',
                'webp': 'image/webp', 'svg': 'image/svg+xml',
            }
            mime = mime_map.get(ext, mime)

        return f'data:{mime};base64,{b64_str}'

    def get_logo_data_uri(self):
        """Return a data URI for the header logo."""
        self.ensure_one()
        return self._binary_to_data_uri(self.header_logo, self.header_logo_filename)

    def get_stamp_data_uri(self):
        """Return a data URI for the footer stamp."""
        self.ensure_one()
        return self._binary_to_data_uri(self.footer_stamp, self.footer_stamp_filename)
