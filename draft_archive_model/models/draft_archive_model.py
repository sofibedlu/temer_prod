from odoo import models, fields, api


class DraftContractArchive(models.Model):
    _name = "draft.contract.archive"
    _description = "Draft Contract Archive"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    sale_id = fields.Many2one(
        "property.sale",
        string="Property Sale",
        readonly=True,
    )
    name = fields.Char(
        related="sale_id.contract_number",
        string="Contract Number",
        readonly=True,
    )
    customer_name = fields.Char(string="Customer Name", tracking=True)
    property_name = fields.Char(string="Property Name")
    sales_no = fields.Char(string="Sales Number")
    date_created = fields.Date(
        string="Date Created",
        default=fields.Date.today,
    )
    status = fields.Selection(
        [
            ("active", "Active"),
            ("signed", "Signed"),
            ("void", "Void"),
        ],
        default="active",
        string="Status",
        tracking=True,
    )
    article_ids = fields.Many2many(
        "draft.contract.archive.line",
        "draft_contract_archive_rel",
        "contract_id",
        "article_id",
        string="Contract Articles",
    )
    rendered_html = fields.Html(string="Rendered HTML", sanitize=False)

    # ── Link to the source contract.archive ──
    source_archive_id = fields.Many2one(
        "contract.archive",
        string="Source Archive",
        readonly=True,
        help="The original contract.archive this draft was cloned from.",
    )

    def action_set_signed(self):
        self.ensure_one()
        self.write({"status": "signed"})

    def action_set_void(self):
        self.ensure_one()
        self.write({"status": "void"})

    def action_promote_to_archive(self):
        """
        Copy the draft's articles and rendered_html back to the source archive.
        """
        self.ensure_one()
        if not self.source_archive_id:
            return
        archive = self.source_archive_id
        if self.rendered_html:
            archive.write({"rendered_html": self.rendered_html})
        # Sync article content back
        for draft_line in self.article_ids:
            matching = archive.article_ids.filtered(
                lambda a: a.main_title == draft_line.main_title
            )[:1]
            if matching and draft_line.content:
                matching.write({"content": draft_line.content})

    @api.model
    def create_from_archive(self, archive_id):
        """
        Clone a contract.archive record into a new draft.contract.archive.
        Returns the new draft record.
        """
        archive = self.env["contract.archive"].browse(archive_id)
        if not archive.exists():
            return self.browse()

        # Clone article lines
        article_commands = []
        for line in archive.article_ids.sorted("sequence"):
            article_commands.append((0, 0, {
                "main_title":        line.main_title or "",
                "subtitle":          line.subtitle or "",
                "content":           line.content or "",
                "sequence":          line.sequence,
                "is_title_printed":  line.is_title_printed,
                "is_dynamic_content": line.is_dynamic_content,
                "is_active":         line.is_active,
                "dynamic_code":      line.dynamic_code or "",
            }))

        draft = self.create({
            "sale_id":          archive.sale_id.id if archive.sale_id else False,
            "customer_name":    archive.customer_name or "",
            "property_name":    archive.property_name or "",
            "sales_no":         archive.sales_no or "",
            "status":           "active",
            "rendered_html":    archive.rendered_html or "",
            "source_archive_id": archive.id,
            "article_ids":      article_commands,
        })
        return draft


class DraftContractArchiveLine(models.Model):
    _name = "draft.contract.archive.line"
    _description = "Draft Contract Article Line"
    _order = "sequence"
    _rec_name = "main_title"

    contract_ids = fields.Many2many(
        "draft.contract.archive",
        "draft_contract_archive_rel",
        "article_id",
        "contract_id",
        string="Draft Contracts",
    )
    sequence = fields.Integer(string="Sequence", default=10)
    main_title = fields.Char(string="Main Title", required=True)
    subtitle = fields.Char(string="Subtitle")
    content = fields.Html(string="Article Content", sanitize=False)
    is_title_printed = fields.Boolean(string="Is Title Printed", default=False)
    is_dynamic_content = fields.Boolean(string="Is Dynamic Content", default=False)
    is_active = fields.Boolean(string="Active", default=True)
    dynamic_code = fields.Text(string="Dynamic Code")
