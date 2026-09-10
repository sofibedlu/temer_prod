from odoo.exceptions import ValidationError
import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class PropertyType(models.Model):
    _inherit = 'property.type'

    site_id = fields.Many2one(
        'property.site',
        string='Site',
        required=False,
        index=True
    )

    def init(self):
        if not self.env.cr or self._name != 'property.type':
            return
        cr = self.env.cr
        table = self._table
        cr.execute(f"""
            ALTER TABLE "{table}"
            DROP CONSTRAINT IF EXISTS property_type_unique_code
        """)
        _logger.debug("---------------------------[%s]----------------" + str(table))

    @api.constrains('code', 'site_id')
    def _check_unique_code_per_site(self):
        for rec in self:
            if not rec.code or not rec.site_id:
                continue
            # Changed to single site check (no loop needed)
            domain = [
                ('id', '!=', rec.id),
                ('code', '=', rec.code),
                ('site_id', '=', rec.site_id.id),
            ]
            clash = self.search(domain, limit=1)
            if clash:
                raise ValidationError(_(
                    "Code ‘%s’ is already in use for site ‘%s’ "
                    "by record %s."
                ) % (rec.code, rec.site_id.name, clash.display_name))


class SitPropertyTypeLine(models.Model):
    _inherit = 'site.property.type.line'

    property_type_id = fields.Many2one(
        'property.type', string="Typography",
        required=True,
        domain="[('site_id','=', site)]"
    )


class PropertySite(models.Model):
    _inherit = 'property.site'

    is_fixed_price = fields.Boolean(
        string="Fixed Price",
        default=False,
        help="If enabled, property prices can be manually set instead of being calculated"
    )


class PropertyProperty(models.Model):
    _inherit = 'property.property'

    payment_structure_id = fields.Many2one(
        'property.payment.term',
        string="Payment Structured",
        compute='_compute_payment_structure',
        store=True
    )

    @api.depends('site', 'property_type_id')
    def _compute_payment_structure(self):
        for rec in self:
            if not rec.site.site_type.multi_payment_method:
                rec.payment_structure_id = rec.site.payment_structure_id
            else:
                line = self.env['property.payment.type'].search([
                    ('site_id', '=', rec.site.id),
                    ('property_type', '=', rec.property_type_id.id)
                ], limit=1)
                rec.payment_structure_id = line.payment_term_id or False

    property_type = fields.Selection(
        [
            ("residential", "Residential"),
            ("commercial", "Commercial"),
        ],
        string="Property Type",
        required=True,
        help="The type of the property"
    )

    is_property_type_readonly = fields.Boolean(
        compute='_compute_property_type_editability',
        string="Is property Fixed", defualt=False
    )
    is_property_mixed = fields.Boolean(
        compute='_compute_is_property_mixed',
        string="Is property type mixed", defualt=False
    )

    is_single_block = fields.Boolean(compute='_compute_is_single_block', string="Single Block Site",
                                     defualt=False)

    @api.depends('site.block_number')
    def _compute_is_single_block(self):
        for rec in self:
            rec.is_single_block = bool(rec.site and rec.site.block_number == 1)

    # @api.onchange('site', 'is_single_block')
    # def _onchange_site_auto_block(self):
    #     for rec in self:
    #         if rec.is_single_block:
    #             first = self.env['property.block'].search(
    #                 [('site', '=', rec.site.id)], limit=1
    #             )
    #             rec.block = first.id or False
    #         else:
    #             rec.block = False

    @api.depends('site', 'site.is_fixed_price')
    def _compute_property_type_editability(self):
        for record in self:
            if not record.site:
                record.is_property_type_readonly = False
                return
            if record.site.site_type.property_type == 'mixed':
                record.is_property_type_readonly = False
            else:
                record.is_property_type_readonly = True

            site_type = record.site.is_fixed_price
            record.is_property_type_readonly = site_type
            if site_type:
                record.gross_area = 0
                record.net_area = 0

    @api.onchange('site', 'site.site_type')
    def _onchange_site_set_property_type(self):
        for record in self:
            if record.site:
                site_type = record.site.site_type.property_type
                if site_type == 'residential':
                    record.property_type = 'residential'
                elif site_type == 'commercial':
                    record.property_type = 'commercial'

    @api.depends('site', 'site.site_type.property_type')
    def _compute_is_property_mixed(self):
        for record in self:
            if record.site and record.site.site_type.property_type == 'mixed':
                record.is_property_mixed = True
            else:
                record.is_property_mixed = False

    unit_price = fields.Monetary(
        string="Sales Price",
        compute='compute_total_price',
        help="Selling price of the Property.",
    )

    manual_unit_price = fields.Monetary(
        string="Sales Price", store=True,
        help="Manually set selling price of the property"
    )

    @api.depends('site.is_fixed_price', 'manual_unit_price', 'site', 'gross_area', 'sale_rent', 'price')
    def compute_total_price(self):
        for rec in self:
            if rec.site and rec.site.is_fixed_price:
                rec.unit_price = rec.manual_unit_price or 0.0
                rec.rent_month = 0.0
            else:
                if rec.sale_rent == 'for_sale':
                    rec.unit_price = (rec.price or 0.0) * (rec.gross_area or 0.0)
                    rec.rent_month = 0.0
                elif rec.sale_rent == 'for_tenancy':
                    rec.unit_price = 0.0
                    rec.rent_month = (rec.price or 0.0) * (rec.gross_area or 0.0)
                else:
                    rec.unit_price = 0.0
                    rec.rent_month = 0.0

    @api.constrains('gross_area', 'net_area')
    def validate_gross_and_net_area(self):
        for rec in self:
            if rec.site and not rec.site.is_fixed_price:
                if rec.gross_area <= 0:
                    raise ValidationError("Gross Area Must be > 0")
                if rec.net_area <= 0:
                    raise ValidationError("Net Area Must be > 0")

    # price = fields.Float('Price(m2)', compute="compute_price", store=True)

    @api.depends('site', 'payment_structure_id', 'site_payment_structure_id')
    def compute_price(self):
        for rec in self:
            if rec.site and rec.site.is_fixed_price:
                rec.price = 0.0
            else:
                if rec.site.site_type.multi_payment_method:
                    if rec.site_payment_structure_id:
                        rec.price = rec.site_payment_structure_id.price
                    else:
                        rec.price = 0
                else:
                    rec.price = rec.site.price_per_m2
