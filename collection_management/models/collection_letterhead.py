from odoo import fields, models
import base64

class CollectionLetterhead(models.Model):
    _name = "collection.letterhead"
    _description = "Collection Letterhead"
    _rec_name = "header_title"

    header_title = fields.Char(string="Header Company Name", required=True)
    stamp_image = fields.Binary(string="Stamp Image", attachment=True)

    note = fields.Text()

    def get_stamp_data_uri(self):
        """Return a safe <img src="..."> value for QWeb."""
        self.ensure_one()
        if not self.stamp_image:
            return False

        img = self.stamp_image
        if isinstance(img, bytes):
            try:
                img = img.decode("utf-8")
            except Exception:
                img = base64.b64encode(img).decode("utf-8")
        return f"data:image/png;base64,{img}"