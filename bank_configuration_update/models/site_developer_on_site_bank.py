from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PropertySiteInherit(models.Model):
    _inherit = 'property.site'

    developer_id = fields.Many2one('site.developer', string="Site Developer")


class BankDocumentType(models.Model):
    _inherit = 'bank.document.type'

    is_international = fields.Boolean(
        string="International Transfer",
        help="Indicates this document type is for international money transfers"
    )


class BankInherit(models.Model):
    _inherit = 'bank.configuration'

    developer_id_bank = fields.Many2one('site.developer', string="Site Developer")
    bank_ethiopian = fields.Many2one('ethiopian.bank', string="Ethiopian Bank", required=False)
    bank_type = fields.Selection([
        ('none', 'None'),
        ('cpo', 'CPO'),
        ('cheque', 'Cheque'),
        ('international', 'International'),
    ], string="Bank Type", default='none')

    # rec_name = fields.Char(string="Bank Code", compute='_compute_rec_name', store=True)
    # @api.depends('bank', 'account_number', 'developer_id_bank')
    # def _compute_rec_name(self):
    #     for rec in self:
    #         dev_name = rec.developer_id_bank.name if rec.developer_id_bank else ''
    #         rec.rec_name = f"{dev_name} - {rec.bank or ''} - {rec.account_number or ''}"

    # @api.depends('bank', 'account_number', 'developer_id_bank')
    # def _compute_rec_name(self):
    #     for rec in self:
    #         dev_name = rec.developer_id_bank.name if rec.developer_id_bank else ''
    #         rec.rec_name = f"{dev_name} - {rec.bank or ''} - {rec.account_number or ''}"

    @api.depends('bank_ethiopian', 'developer_id_bank', 'account_number')
    def _compute_name(self):
        for rec in self:
            dev_name = rec.developer_id_bank.name if rec.developer_id_bank.name else ''
            rec.rec_name = f"{dev_name} - {rec.bank_ethiopian.name or ''} - {rec.account_number or ''}"
            rec.bank = f"{rec.bank_ethiopian.name or ''} - {dev_name}"

    @api.onchange('bank_ethiopian', 'developer_id_bank', 'account_number')
    def on_change_name(self):
        for rec in self:
            dev_name = rec.developer_id_bank.name if rec.developer_id_bank.name else ''
            rec.rec_name = f"{dev_name} - {rec.bank_ethiopian.name or ''} - {rec.account_number or ''}"
            rec.bank = f"{rec.bank_ethiopian.name or ''} - {dev_name}"


class PropertyPaymentInherit(models.Model):
    _inherit = 'property.reservation.payment'

    bank_id = fields.Many2one('bank.configuration', string="Bank", required=False, store=True)
    bank_ethiopian = fields.Many2one('ethiopian.bank', string="Ethiopian Bank", required=False)
    developer_id = fields.Many2one(
        'site.developer',
        string="Site Developer",
        related='reservation_id.property_id.site.developer_id',
        store=True,
    )
    company_filtered = fields.Boolean(
        string="Is company bank",
        compute='_compute_company_filtered',
        store=False, default=False
    )

    @api.depends('document_type_id')
    def _compute_company_filtered(self):
        for line in self:
            name = (line.document_type_id.name or '').strip().lower()
            # True when NOT CPO or Cheque
            line.company_filtered = bool(line.document_type_id) and name in ('cpo', 'cheque')

    @api.onchange('bank_id')
    def _check_bank_developer(self):
        for rec in self:
            if not rec.is_international and not rec.company_filtered and rec.developer_id and rec.bank_id:
                if rec.bank_id.developer_id_bank.id != rec.developer_id.id:
                    raise ValidationError(
                        _("Selected bank does not match the site developer for company bank.")
                    )

    is_international = fields.Boolean(
        related='document_type_id.is_international',
        string="Is International Transfer",
        store=False
    )

    @api.onchange('document_type_id')
    def _onchange_document_type_id(self):
        for line in self:
            # Reset bank
            line.bank_id = False
            line.bank_ethiopian = False

            dt = line.document_type_id
            if not dt:
                return {'domain': {'bank_id': []}}

            name = (dt.name or '').strip().lower()
            dev_id = line.developer_id.id if line.developer_id else False

            domain = []

            # CASE A: Cheque → pick default cheque bank
            if name == 'cheque':
                domain = [('bank_type', '=', 'cheque')]
                default_bank = self.env['bank.configuration'].search(domain, limit=1)
                if default_bank:
                    line.bank_id = default_bank.id

            # CASE B: CPO → pick default cpo bank
            elif name == 'cpo':
                domain = [('bank_type', '=', 'cpo')]
                default_bank = self.env['bank.configuration'].search(domain, limit=1)
                if default_bank:
                    line.bank_id = default_bank.id

            # CASE C: International → pick default international bank
            elif dt.is_international:
                domain = [('bank_type', '=', 'international')]
                default_bank = self.env['bank.configuration'].search(domain, limit=1)
                if default_bank:
                    line.bank_id = default_bank.id

    # @api.onchange('document_type_id')
    # def _onchange_document_type_id(self):
    #     for line in self:
    #         # Reset bank
    #         line.bank_id = False
    #
    #         dt = line.document_type_id
    #         if not dt:
    #             return {'domain': {'bank_id': []}}
    #
    #         name = (dt.name or '').strip().lower()
    #         dev_id = line.developer_id.id if line.developer_id else False
    #
    #         domain = []
    #
    #         # CASE A: Cheque → pick default cheque bank
    #         if name == 'cheque':
    #             domain = [('bank_type', '=', 'cheque')]
    #             default_bank = self.env['bank.configuration'].search(domain, limit=1)
    #             if default_bank:
    #                 line.bank_id = default_bank
    #             return {'domain': {'bank_id': domain}}
    #
    #         # CASE B: CPO → pick default cpo bank
    #         elif name == 'cpo':
    #             domain = [('bank_type', '=', 'cpo')]
    #             default_bank = self.env['bank.configuration'].search(domain, limit=1)
    #             if default_bank:
    #                 line.bank_id = default_bank
    #             return {'domain': {'bank_id': domain}}
    #
    #         # CASE C: International → pick default international bank
    #         elif dt.is_international:
    #             domain = [('bank_type', '=', 'international')]
    #             default_bank = self.env['bank.configuration'].search(domain, limit=1)
    #             if default_bank:
    #                 line.bank_id = default_bank
    #             return {'domain': {'bank_id': domain}}
    #
    #         # CASE D: Otherwise → restrict by developer
    #         else:
    #             domain = [('developer_id_bank', '=', dev_id)]
    #             return {'domain': {'bank_id': domain}}
