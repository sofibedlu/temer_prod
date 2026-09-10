# -*- coding: utf-8 -*-
import json
import logging
import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from markupsafe import Markup

_logger = logging.getLogger(__name__)

MAX_PROPERTY_SELECTIONS = 50
# Include reserved / pending sales so merge can keep original salespeople.
MERGEABLE_PROPERTY_STATES = (
    "draft",
    "available",
    "reserved",
    "pending_sales",
)
MERGE_CANCEL_RESERVATION_STATUSES = (
    "draft",
    "requested",
    "reserved",
    "pending_sales",
)
PROPERTY_FIELD_NAMES = [
    "property_%s_id" % index
    for index in range(1, MAX_PROPERTY_SELECTIONS + 1)
]
PROPERTY_PREVIEW_DEPENDS = PROPERTY_FIELD_NAMES + [
    "%s.%s" % (field_name, property_field)
    for field_name in PROPERTY_FIELD_NAMES
    for property_field in (
        "gross_area",
        "net_area",
        "bedroom",
        "bathroom",
        "unit_price",
        "rent_month",
    )
]


class ChildProperty(models.Model):
    _name = "child.property"
    _description = "Child Property Copy"
    _order = "create_date desc"

    parent_property_id = fields.Many2one(
        "property.property",
        string="Parent Property",
        required=True,
        ondelete="cascade",
        index=True,
    )
    original_property_id = fields.Many2one(
        "property.property",
        string="Original Property",
        readonly=True,
        index=True,
    )
    original_property_database_id = fields.Integer(string="Original Property ID", readonly=True)
    name = fields.Char(string="Original Property Name", required=True, readonly=True)
    code = fields.Char(string="Original Sequence Reference", readonly=True)
    computed_reference = fields.Char(string="Original Reference Number", readonly=True)
    state = fields.Char(string="Original Status", readonly=True)
    salesperson_id = fields.Many2one(
        "res.users",
        string="Salesperson",
        index=True,
        help="Sold credit for this original unit. Empty after merge; filled with the "
             "parent sold-reservation salesperson when the deal is sold. "
             "Change later in DB/UI to split Sold across people.",
    )

    site_id = fields.Many2one("property.site", string="Site", readonly=True)
    block_id = fields.Many2one("property.block", string="Block No", readonly=True)
    floor_id = fields.Many2one("property.floor", string="Floor #", readonly=True)
    site_property_type_id = fields.Many2one("site.property.type.line", string="Property Type", readonly=True)
    property_type_id = fields.Many2one("property.type", string="Property Type Detail", readonly=True)
    property_kind = fields.Char(string="Type", readonly=True)
    unit_number = fields.Char(string="House Number", readonly=True)

    gross_area = fields.Float(string="Gross Area", readonly=True)
    net_area = fields.Float(string="Net Area", readonly=True)
    bedroom = fields.Integer(string="Bedrooms", readonly=True)
    bathroom = fields.Integer(string="Bathrooms", readonly=True)
    price = fields.Float(string="Price(m2)", readonly=True)
    unit_price = fields.Monetary(string="Sales Price", currency_field="currency_id", readonly=True)
    rent_month = fields.Monetary(string="Rent/Month", currency_field="currency_id", readonly=True)
    currency_id = fields.Many2one(
        "res.currency",
        related="parent_property_id.currency_id",
        readonly=True,
    )
    payment_structure_id = fields.Many2one("property.payment.term", string="Payment Structure", readonly=True)
    site_payment_structure_id = fields.Many2one("property.payment.type", string="Site Payment Structure", readonly=True)

    commercial_location = fields.Char(string="Site Location", readonly=True)
    commercial_rate_range = fields.Char(string="Commercial Rate Range", readonly=True)
    commercial_amount = fields.Float(string="Commercial Amount", readonly=True)
    rate_per_m2 = fields.Float(string="Rate-m²", readonly=True)
    finishing = fields.Char(string="Finishing", readonly=True)
    furnishing = fields.Char(string="Furnishing", readonly=True)

    snapshot_json = fields.Text(string="Full Original Property Copy", readonly=True)


class PropertyProperty(models.Model):
    _inherit = "property.property"

    is_merge = fields.Boolean(string="Is Merge", copy=False, readonly=True)


class PropertyReservation(models.Model):
    _inherit = "property.reservation"

    child_property_id = fields.Many2one(
        "child.property",
        string="Original Property (Merged)",
        readonly=True,
        index=True,
        help="When the original property was merged, this child copy keeps the same "
             "historical property name and details on the reservation.",
    )
    property_display_name = fields.Char(
        string="Property",
        compute="_compute_property_display_name",
        store=True,
    )

    @api.depends(
        "property_id",
        "property_id.name",
        "child_property_id",
        "child_property_id.name",
    )
    def _compute_property_display_name(self):
        for rec in self:
            if rec.child_property_id:
                rec.property_display_name = rec.child_property_id.name
            else:
                rec.property_display_name = (
                    rec.property_id.display_name if rec.property_id else False
                )

    def write(self, vals):
        res = super().write(vals)
        if vals.get("status") == "sold":
            self._assign_merge_child_salesperson_on_sold()
        return res

    def _assign_merge_child_salesperson_on_sold(self):
        """When a merged parent is sold, set children to sold reservation salesperson.

        Only runs if sold salesperson is set. Later DB edits on child.salesperson_id
        are used by the sales report for Sold split.
        """
        Child = self.env["child.property"].sudo()
        for reservation in self:
            if reservation.status != "sold":
                continue
            property_id = reservation.property_id
            if not property_id or not getattr(property_id, "is_merge", False):
                continue
            salesperson = reservation.salesperson_ids
            if not salesperson:
                continue
            children = Child.search([("parent_property_id", "=", property_id.id)])
            if children:
                children.write({"salesperson_id": salesperson.id})
                _logger.info(
                    "Set child salesperson %s on %s child(ren) of sold merge %s",
                    salesperson.display_name,
                    len(children),
                    property_id.display_name,
                )


class ChildPropertyMergeWizard(models.TransientModel):
    _name = "child.property.merge.wizard"
    _description = "Merge Property Wizard"

    name = fields.Char(string="Name", default="Merge Property")
    site_id = fields.Many2one(
        "property.site",
        string="Site",
        required=True,
        domain=[("state", "=", "active")],
    )
    property_slot_count = fields.Integer(default=1)
    for index in range(1, MAX_PROPERTY_SELECTIONS + 1):
        locals()["property_%s_id" % index] = fields.Many2one(
            "property.property",
            string="Property",
            domain=(
                "[('site', '=', site_id), "
                "('state', 'in', ['draft', 'available', 'reserved', 'pending_sales'])]"
            ),
        )
    del index
    target_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("available", "Available"),
        ],
        string="Save New Property As",
        default="draft",
        required=True,
    )

    selected_property_count = fields.Integer(string="Selected Properties", compute="_compute_preview")
    preview_name = fields.Char(string="Name", compute="_compute_preview")
    preview_reference = fields.Char(string="Reference Number", compute="_compute_preview")
    preview_property_id = fields.Integer(string="Property ID", compute="_compute_preview")
    preview_state = fields.Char(string="Status", compute="_compute_preview")
    preview_property_type = fields.Char(string="Type", compute="_compute_preview")
    preview_site_property_type_id = fields.Many2one("site.property.type.line", string="Property Type", compute="_compute_preview")
    preview_block_id = fields.Many2one("property.block", string="Block No", compute="_compute_preview")
    preview_floor_id = fields.Many2one("property.floor", string="Floor #", compute="_compute_preview")
    preview_unit_number = fields.Char(string="House Number", compute="_compute_preview")
    gross_area = fields.Float(string="Gross Area", compute="_compute_preview")
    net_area = fields.Float(string="Net Area", compute="_compute_preview")
    bedroom = fields.Integer(string="Bedrooms", compute="_compute_preview")
    bathroom = fields.Integer(string="Bathrooms", compute="_compute_preview")
    price = fields.Float(string="Price(m2)", compute="_compute_preview")
    unit_price = fields.Monetary(string="Sales Price", compute="_compute_preview", currency_field="currency_id")
    rent_month = fields.Monetary(string="Rent/Month", compute="_compute_preview", currency_field="currency_id")
    currency_id = fields.Many2one("res.currency", related="site_id.currency_id", readonly=True)
    payment_structure_id = fields.Many2one("property.payment.term", string="Payment Structure", compute="_compute_preview")
    site_payment_structure_id = fields.Many2one("property.payment.type", string="Site Payment Structure", compute="_compute_preview")
    commercial_location = fields.Char(string="Site Location", compute="_compute_preview")
    commercial_rate_range = fields.Char(string="Commercial Rate Range", compute="_compute_preview")
    commercial_amount = fields.Float(string="Commercial Amount", compute="_compute_preview")
    rate_per_m2 = fields.Float(string="Rate-m²", compute="_compute_preview")
    finishing = fields.Char(string="Finishing", compute="_compute_preview")
    furnishing = fields.Char(string="Furnishing", compute="_compute_preview")

    @api.depends(*PROPERTY_PREVIEW_DEPENDS)
    def _compute_preview(self):
        for rec in self:
            properties = rec._selected_properties()
            first = properties[:1]
            merged_unit = rec._get_merged_property_unit(properties) if properties else ""

            rec.selected_property_count = rec._selected_property_count()
            rec.preview_property_id = 0
            rec.preview_name = rec._build_preview_name(first, merged_unit) if first else _("New")
            rec.preview_reference = rec._build_merge_reference(first, merged_unit) if first else _("New")
            rec.preview_state = first.state if first else False
            rec.preview_property_type = first.property_type if first else False
            rec.preview_site_property_type_id = first.site_property_type_id if first else False
            rec.preview_block_id = first.block if first else False
            rec.preview_floor_id = first.floor_id if first else False
            rec.preview_unit_number = merged_unit
            rec.gross_area = sum(properties.mapped("gross_area"))
            rec.net_area = sum(properties.mapped("net_area"))
            rec.bedroom = sum(properties.mapped("bedroom"))
            rec.bathroom = sum(properties.mapped("bathroom"))
            rec.unit_price = sum(properties.mapped("unit_price"))
            rec.rent_month = sum(properties.mapped("rent_month"))
            rec.price = rec.unit_price / rec.gross_area if rec.gross_area else 0.0
            rec.payment_structure_id = first.payment_structure_id if first else False
            rec.site_payment_structure_id = first.site_payment_structure_id if first else False
            rec.commercial_location = getattr(first, "commercial_location", False) if first else False
            rec.commercial_rate_range = (
                getattr(getattr(first, "commercial_rate_range_id", False), "display_name", False)
                if first
                else False
            )
            rec.commercial_amount = sum(getattr(prop, "commercial_amount", 0.0) for prop in properties)
            rec.rate_per_m2 = getattr(first, "rate_per_m2", 0.0) if first else 0.0
            rec.finishing = first.finishing if first else False
            rec.furnishing = first.furnishing if first else False

    @api.onchange("site_id")
    def _onchange_site_id(self):
        for rec in self:
            rec.property_slot_count = 1
            for field_name in PROPERTY_FIELD_NAMES:
                rec[field_name] = False
        return self._property_selection_domains()

    @api.onchange(*PROPERTY_FIELD_NAMES)
    def _onchange_property_fields(self):
        return self._property_selection_domains()

    def _property_selection_domains(self):
        self.ensure_one()
        domains = {}
        selected_by_field = {
            field_name: self[field_name].id
            for field_name in PROPERTY_FIELD_NAMES
            if self[field_name]
        }
        for field_name in PROPERTY_FIELD_NAMES:
            excluded_ids = [
                property_id
                for other_field, property_id in selected_by_field.items()
                if other_field != field_name
            ]
            domain = [
                ("site", "=", self.site_id.id or False),
                ("state", "in", list(MERGEABLE_PROPERTY_STATES)),
            ]
            if excluded_ids:
                domain.append(("id", "not in", excluded_ids))
            domains[field_name] = domain
        return {"domain": domains}

    def action_add_property(self):
        self.ensure_one()
        if not self.site_id:
            raise ValidationError(_("Please select a site first."))
        if self.property_slot_count >= MAX_PROPERTY_SELECTIONS:
            raise ValidationError(_("You cannot add more properties in this merge."))
        current_property = self["property_%s_id" % self.property_slot_count]
        if not current_property:
            raise ValidationError(_("Please select the current property before adding another one."))
        self.property_slot_count += 1
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "view_mode": "form",
            "res_id": self.id,
            "target": "current",
        }

    def action_merge_properties(self):
        self.ensure_one()
        properties = self._selected_properties().exists()
        source_names = properties.mapped("display_name")
        _logger.info(
            "Property merge requested from wizard %s for properties: %s",
            self.id,
            ", ".join(source_names),
        )
        self._validate_selected_properties(properties)

        if not self.env.context.get("merge_reservations_confirmed"):
            reservations = self._get_reservations_to_cancel(properties)
            if reservations:
                return self._open_reservation_cancel_warning(reservations)

        return self._do_merge_properties(properties, source_names)

    def _get_reservations_to_cancel(self, properties):
        Reservation = self.env["property.reservation"].sudo().with_context(active_test=False)
        return Reservation.search(
            [
                ("property_id", "in", properties.ids),
                ("status", "in", list(MERGE_CANCEL_RESERVATION_STATUSES)),
            ],
            order="property_id, id",
        )

    def _open_reservation_cancel_warning(self, reservations):
        self.ensure_one()
        Confirm = self.env["child.property.merge.confirm.wizard"]
        confirm = Confirm.create(
            {
                "merge_wizard_id": self.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "reservation_id": reservation.id,
                            "property_id": reservation.property_id.id,
                            "property_name": reservation.property_id.display_name,
                            "status": dict(
                                reservation._fields["status"].selection
                            ).get(reservation.status, reservation.status),
                            "customer_name": reservation.partner_id.display_name
                            if reservation.partner_id
                            else "",
                            "salesperson_name": reservation.salesperson_ids.display_name
                            if reservation.salesperson_ids
                            else "",
                            "created_by_name": reservation.create_uid.display_name
                            if reservation.create_uid
                            else "",
                        },
                    )
                    for reservation in reservations
                ],
            }
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("Warning: Reservations will be canceled"),
            "res_model": "child.property.merge.confirm.wizard",
            "view_mode": "form",
            "res_id": confirm.id,
            "target": "new",
        }

    def _do_merge_properties(self, properties, source_names):
        self.ensure_one()
        merged_property = self._create_merged_property(properties)
        children_by_property = self._create_child_copies(properties, merged_property)
        self._link_reservations_to_children(properties, children_by_property, merged_property)
        self._replace_property_references(properties, merged_property)
        # Clear wizard Many2one fields before unlink so the response/reload does not
        # try to read deleted property.property records.
        for field_name in PROPERTY_FIELD_NAMES:
            self[field_name] = False
        self.property_slot_count = 1
        self._remove_merged_source_properties(properties, source_names=source_names)
        self._log_merge_result(source_names, merged_property)

        return {
            "type": "ir.actions.act_window",
            "name": merged_property.name,
            "res_model": "property.property",
            "view_mode": "form",
            "res_id": merged_property.id,
            "target": "current",
            "context": {"create": False},
        }

    def _selected_properties(self):
        self.ensure_one()
        properties = self.env["property.property"]
        for field_name in PROPERTY_FIELD_NAMES:
            if self[field_name]:
                properties |= self[field_name]
        return properties

    def _selected_property_count(self):
        self.ensure_one()
        return sum(1 for field_name in PROPERTY_FIELD_NAMES if self[field_name])

    def _validate_selected_properties(self, properties):
        if len(properties) < 2:
            raise ValidationError(_("Please select at least two properties to merge."))
        if len(set(properties.ids)) != len(properties):
            raise ValidationError(_("The same property cannot be selected more than once."))

        invalid_state = properties.filtered(
            lambda prop: prop.state not in MERGEABLE_PROPERTY_STATES
        )
        if invalid_state:
            _logger.warning(
                "Property merge blocked by invalid state: %s",
                self._format_property_selection(invalid_state),
            )
            raise ValidationError(
                _(
                    "Only Draft, Available, Reserved and Pending Sales "
                    "properties can be merged: %s"
                )
                % ", ".join(invalid_state.mapped("name"))
            )

        wrong_site = properties.filtered(lambda prop: prop.site != self.site_id)
        if wrong_site:
            details = self._format_property_selection(wrong_site)
            _logger.warning("Property merge blocked by different site: %s", details)
            raise ValidationError(
                _("All selected properties must be from the selected site.\n%s") % details
            )
        if len(self._normalized_many2one_values(properties, "block")) != 1:
            details = self._format_property_selection(properties)
            _logger.warning("Property merge blocked by different block: %s", details)
            raise ValidationError(
                _("All selected properties must be in the same block.\n%s") % details
            )
        if len(self._normalized_many2one_values(properties, "floor_id")) != 1:
            details = self._format_property_selection(properties)
            _logger.warning("Property merge blocked by different floor: %s", details)
            raise ValidationError(
                _("All selected properties must be on the same floor.\n%s") % details
            )
        if len(set(properties.mapped("property_type"))) != 1:
            details = self._format_property_selection(properties)
            _logger.warning("Property merge blocked by different type: %s", details)
            raise ValidationError(
                _("All selected properties must have the same type.\n%s") % details
            )

    def _create_merged_property(self, properties):
        first = properties[0]
        merged_unit = self._get_merged_property_unit(properties)
        total_gross = sum(properties.mapped("gross_area"))
        total_net = sum(properties.mapped("net_area"))
        total_bedroom = sum(properties.mapped("bedroom"))
        total_bathroom = sum(properties.mapped("bathroom"))
        total_sale_price = sum(properties.mapped("unit_price"))
        price_per_m2 = (total_sale_price / total_gross) if total_gross else 0.0
        merged_property_type = self._get_or_create_merged_property_type(properties, merged_unit)
        merged_site_line = self._get_or_create_site_property_type_line(first, merged_property_type)
        merged_payment_type = self._create_merged_payment_type(first, properties, merged_unit)

        Property = self.env["property.property"].sudo()
        vals = {
            "site": first.site.id,
            "block": first.block.id,
            "site_property_type_id": merged_site_line.id,
            "property_type_id": merged_property_type.id,
            "floor_id": first.floor_id.id,
            "property_type": first.property_type,
            "sale_rent": first.sale_rent,
            "payment_structure_id": first.payment_structure_id.id,
            "site_payment_structure_id": merged_payment_type.id if merged_payment_type else first.site_payment_structure_id.id,
            "finishing": first.finishing,
            "furnishing": first.furnishing,
            "responsible_id": first.responsible_id.id,
            "landlord_id": first.landlord_id.id,
            "description": first.description,
            "street": first.street,
            "street2": first.street2,
            "zip": first.zip,
            "city": first.city,
            "country_id": first.country_id.id,
            "state_id": first.state_id.id,
            "company_id": first.company_id.id,
            "image": first.image,
            "is_merge": True,
        }
        if "property_type_gross_area" in Property._fields:
            vals["property_type_gross_area"] = total_gross
        if "property_type_net_area" in Property._fields:
            vals["property_type_net_area"] = total_net
        if "property_type_bedroom" in Property._fields:
            vals["property_type_bedroom"] = total_bedroom
        if "property_type_bathroom" in Property._fields:
            vals["property_type_bathroom"] = total_bathroom
        if "property_type_has_maid_room" in Property._fields:
            vals["property_type_has_maid_room"] = any(properties.mapped("property_type_id.has_maid_room"))
        if "property_type_no_kitchen" in Property._fields:
            vals["property_type_no_kitchen"] = sum(getattr(prop, "property_type_no_kitchen", 0) for prop in properties)
        if "unit_number" in Property._fields:
            vals["unit_number"] = merged_unit
        if "commercial_location" in Property._fields:
            vals["commercial_location"] = getattr(first, "commercial_location", False)
        if "commercial_amount" in Property._fields:
            vals["commercial_amount"] = sum(getattr(prop, "commercial_amount", 0.0) for prop in properties)
        if "commercial_rate_range_id" in Property._fields:
            commercial_rate_range = getattr(first, "commercial_rate_range_id", False)
            vals["commercial_rate_range_id"] = commercial_rate_range.id if commercial_rate_range else False
        if "rate_per_m2" in Property._fields:
            vals["rate_per_m2"] = getattr(first, "rate_per_m2", 0.0)
        if "manual_unit_price" in Property._fields:
            vals["manual_unit_price"] = total_sale_price
        if "use_manual_sale_price" in Property._fields:
            vals["use_manual_sale_price"] = True
        if "override_price_m2" in Property._fields:
            vals["override_price_m2"] = price_per_m2
        if "price" in Property._fields:
            vals["price"] = price_per_m2

        merged_property = Property.create(vals)
        self._force_merged_property_values(
            merged_property,
            total_gross,
            total_net,
            total_bedroom,
            total_bathroom,
            total_sale_price,
            price_per_m2,
        )
        merge_reference = self._build_merge_reference(first, merged_unit)
        if merge_reference and "computed_reference" in Property._fields:
            merged_property.with_context(skip_reference_recompute=True).write({
                "computed_reference": merge_reference,
            })
        if self.target_state == "available":
            merged_property.write({"state": "available"})
        else:
            merged_property.write({"state": "draft"})
        self._copy_property_relations(properties, merged_property)
        return merged_property

    def _force_merged_property_values(
        self,
        merged_property,
        total_gross,
        total_net,
        total_bedroom,
        total_bathroom,
        total_sale_price,
        price_per_m2,
    ):
        vals = {}
        if "property_type_gross_area" in merged_property._fields:
            vals["property_type_gross_area"] = total_gross
        if "property_type_net_area" in merged_property._fields:
            vals["property_type_net_area"] = total_net
        if "property_type_bedroom" in merged_property._fields:
            vals["property_type_bedroom"] = total_bedroom
        if "property_type_bathroom" in merged_property._fields:
            vals["property_type_bathroom"] = total_bathroom
        if "gross_area" in merged_property._fields:
            vals["gross_area"] = total_gross
        if "net_area" in merged_property._fields:
            vals["net_area"] = total_net
        if "bedroom" in merged_property._fields:
            vals["bedroom"] = total_bedroom
        if "bathroom" in merged_property._fields:
            vals["bathroom"] = total_bathroom
        if "manual_unit_price" in merged_property._fields:
            vals["manual_unit_price"] = total_sale_price
        if "use_manual_sale_price" in merged_property._fields:
            vals["use_manual_sale_price"] = True
        if "unit_price" in merged_property._fields:
            vals["unit_price"] = total_sale_price
        if "override_price_m2" in merged_property._fields:
            vals["override_price_m2"] = price_per_m2
        if "price" in merged_property._fields:
            vals["price"] = price_per_m2
        if vals:
            merged_property.sudo().write(vals)

    def _get_or_create_merged_property_type(self, properties, merged_unit):
        PropertyType = self.env["property.type"].sudo()
        existing_type = PropertyType.search([("code", "=", merged_unit)], limit=1)
        vals = {
            "number_be_room": sum(properties.mapped("bedroom")),
            "number_bath_room": sum(properties.mapped("bathroom")),
            "has_maid_room": any(properties.mapped("property_type_id.has_maid_room")),
            "net_area": sum(properties.mapped("net_area")),
            "gross_area": sum(properties.mapped("gross_area")),
            "image": properties[0].property_type_id.image,
        }
        if existing_type:
            existing_type.write(vals)
            return existing_type
        vals["code"] = merged_unit
        return PropertyType.create(vals)

    def _get_or_create_site_property_type_line(self, first, merged_property_type):
        SiteLine = self.env["site.property.type.line"].sudo()
        site_line = SiteLine.search(
            [
                ("site", "=", first.site.id),
                ("property_type_id", "=", merged_property_type.id),
            ],
            limit=1,
        )
        if site_line:
            return site_line
        return SiteLine.create(
            {
                "site": first.site.id,
                "property_type_id": merged_property_type.id,
            }
        )

    def _create_merged_payment_type(self, first, properties, merged_unit):
        if not first.site.site_type.multi_payment_method:
            return self.env["property.payment.type"]

        total_gross = sum(properties.mapped("gross_area"))
        total_price = sum(properties.mapped("unit_price"))
        price_per_m2 = total_price / total_gross if total_gross else 0.0
        payment_term = first.site_payment_structure_id.payment_term_id or first.payment_structure_id
        if not payment_term:
            return self.env["property.payment.type"]

        return self.env["property.payment.type"].sudo().create(
            {
                "name": _("Merged %s") % merged_unit,
                "site_id": first.site.id,
                "property_type": first.property_type,
                "payment_term_id": payment_term.id,
                "price": price_per_m2,
            }
        )

    def _create_child_copies(self, properties, merged_property):
        Child = self.env["child.property"].sudo()
        children_by_property = {}
        for prop in properties:
            child = Child.create(self._child_copy_vals(prop, merged_property))
            children_by_property[prop.id] = child
        return children_by_property

    def _salesperson_for_property(self, prop):
        """Do not auto-fill child salesperson from unit reservations.

        Sold report defaults to the parent sold-reservation salesperson.
        Set child.salesperson_id manually (DB/UI) only when splitting credit.
        """
        return False

    def _link_reservations_to_children(self, properties, children_by_property, merged_property):
        """Link unit reservations to child copies, then cancel them.

        Original properties are deleted after merge, so active reserved /
        pending_sales reservations must not stay live on the new parent.
        Keep the same reservation record (canceled) on child_property_id for
        history. Do not copy reservation salesperson onto child.salesperson_id.
        """
        Reservation = self.env["property.reservation"].sudo().with_context(active_test=False)
        cancel_statuses = MERGE_CANCEL_RESERVATION_STATUSES
        for prop in properties:
            child = children_by_property.get(prop.id)
            if not child:
                continue
            reservations = Reservation.search([("property_id", "=", prop.id)])
            if not reservations:
                continue
            # Write one-by-one: other modules' reservation.write() expect a singleton.
            for reservation in reservations:
                vals = {
                    "child_property_id": child.id,
                    # Keep a live property.property FK so required fields / site related
                    # still work after the original unit is deleted.
                    "property_id": merged_property.id,
                }
                if reservation.status in cancel_statuses:
                    vals.update(
                        {
                            "status": "canceled",
                            "canceled_time": fields.Datetime.now(),
                            "canceled_reason": _(
                                "Canceled automatically: property merged into %s"
                            )
                            % merged_property.display_name,
                        }
                    )
                reservation.write(vals)
                if reservation.status == "canceled" or vals.get("status") == "canceled":
                    self._cancel_sales_for_merged_reservation(reservation)
            _logger.info(
                "Linked/canceled %s reservation(s) from %s to child %s (parent %s)",
                len(reservations),
                prop.display_name,
                child.display_name,
                merged_property.display_name,
            )

    def _cancel_sales_for_merged_reservation(self, reservation):
        """Cancel pending sales tied to a reservation canceled by merge."""
        if "property.sale" not in self.env:
            return
        sales = self.env["property.sale"].sudo().search(
            [("reservation_id", "=", reservation.id)]
        )
        for sale in sales:
            if sale.state != "cancel":
                try:
                    sale.write({"state": "cancel"})
                except Exception:
                    _logger.exception(
                        "Failed to cancel sale %s for merged reservation %s",
                        sale.id,
                        reservation.id,
                    )

    def _child_copy_vals(self, prop, merged_property):
        return {
            "parent_property_id": merged_property.id,
            "original_property_id": prop.id,
            "original_property_database_id": prop.id,
            "name": prop.name,
            "code": prop.code,
            "computed_reference": getattr(prop, "computed_reference", False),
            "state": prop.state,
            "salesperson_id": self._salesperson_for_property(prop),
            "site_id": prop.site.id,
            "block_id": prop.block.id,
            "floor_id": prop.floor_id.id,
            "site_property_type_id": prop.site_property_type_id.id,
            "property_type_id": prop.property_type_id.id,
            "property_kind": prop.property_type,
            "unit_number": getattr(prop, "unit_number", False),
            "gross_area": prop.gross_area,
            "net_area": prop.net_area,
            "bedroom": prop.bedroom,
            "bathroom": prop.bathroom,
            "price": prop.price,
            "unit_price": prop.unit_price,
            "rent_month": prop.rent_month,
            "payment_structure_id": prop.payment_structure_id.id,
            "site_payment_structure_id": prop.site_payment_structure_id.id,
            "commercial_location": getattr(prop, "commercial_location", False),
            "commercial_rate_range": getattr(getattr(prop, "commercial_rate_range_id", False), "display_name", False),
            "commercial_amount": getattr(prop, "commercial_amount", 0.0),
            "rate_per_m2": getattr(prop, "rate_per_m2", 0.0),
            "finishing": prop.finishing,
            "furnishing": prop.furnishing,
            "snapshot_json": self._property_snapshot_json(prop),
        }

    def _copy_property_relations(self, properties, merged_property):
        facility_ids = properties.mapped("facility_ids").ids
        tag_ids = properties.mapped("property_tags").ids
        vals = {}
        if facility_ids:
            vals["facility_ids"] = [(6, 0, facility_ids)]
        if tag_ids:
            vals["property_tags"] = [(6, 0, tag_ids)]
        if vals:
            merged_property.sudo().write(vals)

        for prop in properties:
            for image in prop.property_image_ids:
                self.env["property.image"].sudo().create(
                    {
                        "property_id": merged_property.id,
                        "name": "%s - %s" % (prop.name, image.name),
                        "description": image.description,
                        "image": image.image,
                    }
                )
            for measure in prop.area_measurement_ids:
                self.env["property.area.measure"].sudo().create(
                    {
                        "property_id": merged_property.id,
                        "name": "%s - %s" % (prop.name, measure.name),
                        "length": measure.length,
                        "width": measure.width,
                        "height": measure.height,
                    }
                )

    def _property_snapshot_json(self, prop):
        snapshot = {}
        for field_name, field in prop._fields.items():
            if field_name in ("message_ids", "message_follower_ids", "activity_ids"):
                continue
            try:
                value = prop[field_name]
                if field.type == "many2one":
                    snapshot[field_name] = {
                        "id": value.id,
                        "display_name": value.display_name,
                    } if value else False
                elif field.type in ("many2many", "one2many"):
                    snapshot[field_name] = [
                        {"id": rec.id, "display_name": rec.display_name}
                        for rec in value
                    ]
                else:
                    snapshot[field_name] = value
            except Exception as exc:
                snapshot[field_name] = "Snapshot failed: %s" % exc
        return json.dumps(snapshot, default=str, sort_keys=True, indent=2)

    def _replace_property_references(self, old_properties, new_property):
        old_ids = old_properties.ids
        # Reservations are handled separately: they keep the original display via
        # child.property (child_property_id), while property_id points at the parent.
        skipped_models = {
            "child.property",
            "child.property.merge.wizard",
            "property.reservation",
        }
        for model_name, model_class in self.env.registry.models.items():
            if model_name in skipped_models:
                continue
            Model = self.env[model_name].sudo().with_context(active_test=False)
            for field_name, field in model_class._fields.items():
                if field.type != "many2one" or field.comodel_name != "property.property":
                    continue
                if field.related or (field.compute and not field.inverse):
                    continue
                try:
                    records = Model.search([(field_name, "in", old_ids)])
                    if records:
                        records.write({field_name: new_property.id})
                except Exception:
                    _logger.exception(
                        "Failed to update %s.%s during property merge",
                        model_name,
                        field_name,
                    )

    def _remove_merged_source_properties(self, properties, source_names=None):
        """Delete the selected source properties after child copies and FK updates."""
        if not properties:
            return
        # Keep historical names/details on child.property; drop the live FK so unlink
        # of the source property cannot cascade or block on this relation.
        children = self.env["child.property"].sudo().search([
            ("original_property_id", "in", properties.ids),
        ])
        if children:
            children.write({"original_property_id": False})
        names = source_names or properties.mapped("display_name")
        _logger.info(
            "Removing merged source properties: %s",
            ", ".join(names),
        )
        properties.sudo().unlink()

    def _log_merge_result(self, source_names, new_property):
        child_count = self.env["child.property"].search_count([
            ("parent_property_id", "=", new_property.id),
        ])
        property_items = "".join(
            "<li>%s</li>" % name for name in source_names
        )
        message = Markup(
            "<p><strong>Property merge completed</strong></p>"
            "<ul>"
            "<li><strong>Parent:</strong> %(parent)s</li>"
            "<li><strong>Copied child records:</strong> %(child_count)s</li>"
            "<li><strong>Removed source properties:</strong><ul>%(properties)s</ul></li>"
            "</ul>"
        ) % {
            "parent": new_property.display_name,
            "child_count": child_count,
            "properties": Markup(property_items),
        }
        if hasattr(new_property, "message_post"):
            new_property.message_post(body=message)
        _logger.info(
            "Property merge completed. Parent=%s children=%s selected=%s",
            new_property.display_name,
            child_count,
            ", ".join(source_names),
        )

    def _format_property_selection(self, properties):
        lines = []
        for prop in properties:
            lines.append(
                "%s | Site: %s | Block: %s | Floor: %s | Type: %s"
                % (
                    prop.display_name,
                    prop.site.display_name if prop.site else "-",
                    prop.block.display_name if prop.block else "-",
                    prop.floor_id.display_name if prop.floor_id else "-",
                    prop.property_type or "-",
                )
            )
        return "\n".join(lines)

    def _normalized_many2one_values(self, records, field_name):
        values = set()
        for record in records:
            value = record[field_name]
            if value:
                values.add((value.display_name or value.name or "").strip().lower())
            else:
                values.add("")
        return values

    def _get_merged_property_unit(self, properties):
        return " & ".join(self._get_property_unit_part(prop) for prop in properties)

    def _get_property_unit_part(self, prop):
        value = getattr(prop, "unit_number", False) or prop.property_type_id.code or prop.name.rsplit("-", 1)[-1]
        value = str(value).strip()
        digits = "".join(char for char in value if char.isdigit())
        if digits:
            return str(int(digits)).zfill(2)
        return value

    def _build_preview_name(self, first, merged_unit):
        return "%s-%s-F%s-%s" % (
            first.site.name,
            first.block.name,
            first.floor_id.name,
            merged_unit,
        )

    def _build_merge_reference(self, first, merged_unit):
        if not first or not first.site or not merged_unit:
            return ""

        clean_site = re.sub(r"[^A-Za-z0-9]", "", (first.site.name or "").strip())
        site_code = clean_site[:3].upper() if clean_site else ""
        if not site_code:
            return ""

        owner_code = ""
        if hasattr(first.site, "company_id") and first.site.company_id:
            company = first.site.company_id
            if getattr(company, "abbreviation", False) and company.abbreviation.strip():
                owner_code = re.sub(r"[^A-Za-z0-9]", "", company.abbreviation.strip().upper())
            elif getattr(company, "name", False):
                owner_code = re.sub(r"[^A-Za-z0-9]", "", company.name.strip())[:3].upper()

        project_no = ""
        if hasattr(first.site, "project_number") and first.site.project_number:
            project_no = str(first.site.project_number).strip()

        block_no = ""
        if first.block and getattr(first.block, "name", False):
            block_str = str(first.block.name).strip()
            block_no = block_str.zfill(2) if block_str.isdigit() else block_str.upper()

        floor_no = ""
        if first.floor_id and first.floor_id.name is not None:
            floor_no = "F%s" % first.floor_id.name

        ref_parts = [site_code]
        if owner_code:
            ref_parts.append("-%s" % owner_code)
            if project_no:
                ref_parts.append(project_no)
        if block_no or floor_no:
            ref_parts.append("/%s" % "/".join(part for part in (block_no, floor_no) if part))
        ref_parts.append("-%s" % merged_unit)
        return "".join(ref_parts)


class ChildPropertyMergeConfirmWizard(models.TransientModel):
    _name = "child.property.merge.confirm.wizard"
    _description = "Confirm Merge Reservation Cancellation"

    merge_wizard_id = fields.Many2one(
        "child.property.merge.wizard",
        string="Merge Wizard",
        required=True,
        ondelete="cascade",
    )
    reservation_count = fields.Integer(compute="_compute_reservation_count")
    line_ids = fields.One2many(
        "child.property.merge.confirm.line",
        "wizard_id",
        string="Reservations to Cancel",
    )

    @api.depends("line_ids")
    def _compute_reservation_count(self):
        for rec in self:
            rec.reservation_count = len(rec.line_ids)

    def action_confirm_merge(self):
        self.ensure_one()
        if not self.merge_wizard_id:
            raise ValidationError(_("Merge wizard not found."))
        return self.merge_wizard_id.with_context(
            merge_reservations_confirmed=True
        ).action_merge_properties()

    def action_cancel(self):
        return {"type": "ir.actions.act_window_close"}


class ChildPropertyMergeConfirmLine(models.TransientModel):
    _name = "child.property.merge.confirm.line"
    _description = "Merge Reservation Cancellation Line"

    wizard_id = fields.Many2one(
        "child.property.merge.confirm.wizard",
        required=True,
        ondelete="cascade",
    )
    reservation_id = fields.Many2one("property.reservation", string="Reservation", readonly=True)
    property_id = fields.Many2one("property.property", string="Property", readonly=True)
    property_name = fields.Char(string="Property", readonly=True)
    status = fields.Char(string="Status", readonly=True)
    customer_name = fields.Char(string="Customer", readonly=True)
    salesperson_name = fields.Char(string="Salesperson", readonly=True)
    created_by_name = fields.Char(string="Created By", readonly=True)
