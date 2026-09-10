import re
from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PropertySale(models.Model):
    _inherit = "property.sale"

    # Template & Creation
    def _template_model(self):
        return self.env[self._fields["template_id"].comodel_name]

    def _find_template_for_site(self, site):
        if not site:
            return False

        Template = self._template_model()
        return Template.search([
            ("site_id", "=", site.id),
            ("active", "=", True),
        ], limit=1)

    @api.onchange("property_id")
    def _onchange_property_id_set_template(self):
        for sale in self:
            site = sale.property_id.site if sale.property_id else False
            if site and (not sale.template_id or getattr(sale.template_id, "site_id", False) != site):
                tmpl = sale._find_template_for_site(site)
                if tmpl:
                    sale.template_id = tmpl

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("template_id") and vals.get("property_id"):
                prop = self.env["property.property"].browse(vals["property_id"])
                tmpl = self._find_template_for_site(prop.site)
                if tmpl:
                    vals["template_id"] = tmpl.id
        return super().create(vals_list)

    # Contract Number Generation Helpers
    def _get_yy_from_contract(self, contract_application):
        s = (getattr(contract_application, "contract_date_char", "") or "").strip()
        if len(s) >= 4:
            return s[-2:]

        contract_date = contract_application.contract_date or fields.Date.today()
        try:
            from ethiopian_date import EthiopianDateConverter
            eth_year = EthiopianDateConverter.to_ethiopian(
                contract_date.year, 
                contract_date.month, 
                contract_date.day
            ).year
        except Exception:
            if contract_date.month < 9 or (contract_date.month == 9 and contract_date.day < 11):
                eth_year = contract_date.year - 8
            else:
                eth_year = contract_date.year - 7

        return str(eth_year)[-2:]

    def _get_sequence_for_sale(self, sale, template):
        if not template:
            return False

        if getattr(template, 'use_property_type_sequences', False) and sale.property_id:
            prop_type = sale.property_id.property_type
            if prop_type == 'residential' and getattr(template, 'residential_sequence_id', False):
                return template.residential_sequence_id
            elif prop_type == 'commercial' and getattr(template, 'commercial_sequence_id', False):
                return template.commercial_sequence_id
            elif prop_type == 'office' and getattr(template, 'office_sequence_id', False):
                return template.office_sequence_id

        if "developer_id" in template._fields:
            print("DEBUG: Checking developer sequence")
            dev = template.developer_id
            print("DEBUG: Developer is %s" % dev.name if dev else "None")
            if dev and "sequence" in dev._fields and dev.sequence:
                return dev.sequence

        for fname in ("sequence_id", "sequence"):
            if fname in template._fields and getattr(template, fname):
                return getattr(template, fname)

        return False

    def _next_seq_number_padded_and_increment(self, sequence):

        sequence.invalidate_recordset(['number_next', 'number_next_actual'])
        next_no = sequence.number_next_actual
        padding = int(sequence.padding or 0)
        seq_no = str(next_no).zfill(padding) if padding else str(next_no)
        sequence.next_by_id() 
        
        return seq_no

    def _extract_seq_int_from_existing_contract_name(self, name):

        if not name:
            return None
        parts = [p for p in str(name).split("/") if p]
        if len(parts) < 2:
            return None

        seq_part = parts[-2]
        if str(seq_part).isdigit():
            try:
                return int(seq_part)
            except Exception:
                return None
        return None

    def _format_seq_no(self, sequence, seq_int):
        padding = int(sequence.padding or 0)
        return str(seq_int).zfill(padding) if padding else str(seq_int)

    #####
    def _clean_contract_code(self, value, size=None):
        cleaned = re.sub(r"[^A-Za-z0-9]", "", (value or "").upper())
        return cleaned[:size] if size else cleaned

    def _get_company_site_mapping_line(self, site):
        if not site:
            return False
        return self.env["site.company.mapping.line"].sudo().search(
            [("site_id", "=", site.id)],
            limit=1,
        )

    def _get_company_code(self, company):
        if not company:
            raise ValidationError(_("A company is required to generate the contract number."))

        abbreviation = (company.abbreviation or "").strip()

        if abbreviation:
            code = self._clean_contract_code(abbreviation)
            if not code:
                raise ValidationError(_(
                    "Company abbreviation for '%s' is invalid."
                ) % company.display_name)
            return code

        name = (company.name or "").strip()
        code = self._clean_contract_code(name, size=3)
        if len(code) < 3:
            raise ValidationError(_(
                "Company code could not be generated.\n"
                "Please make sure the company name has at least 3 letters."
            ))
        return code

    def _get_site_code(self, mapping_line):
        code = self._clean_contract_code(mapping_line.site_abbreviation)
        if not code:
            raise ValidationError(_(
                "Site abbreviation is missing for site '%s'."
            ) % mapping_line.site_id.display_name)
        return code
    
    def _get_location_code(self, mapping_line):
        if not mapping_line.location_id:
            raise ValidationError(_("Location is required on the mapping for site '%s'.") % mapping_line.site_id.display_name)
        
        code = self._clean_contract_code(mapping_line.location_id.abbreviation)
        if not code:
            raise ValidationError(_("Location abbreviation is missing for location '%s'.") % mapping_line.location_id.display_name)
        return code

    def _get_property_type_code(self, property_id):
        code = self._clean_contract_code(property_id.property_type, size=1)
        if not code:
            raise ValidationError(_(
                "Property type is required to generate the contract number for '%s'."
            ) % property_id.display_name)
        return code

    def _get_contract_prefix(self, sale):
        mapping_line = self._get_company_site_mapping_line(sale.property_id.site)
        if not mapping_line:
            raise ValidationError(_(
                "No Company Site Mapping was found for site '%s'.\n"
                "Please configure it before confirming the sale."
            ) % sale.property_id.site.display_name)

        company_code = self._get_company_code(mapping_line.company_id)
        location_code = self._get_location_code(mapping_line)
        site_code = self._get_site_code(mapping_line)
        type_code = self._get_property_type_code(sale.property_id)

        project_number = sale.property_id.site.project_number
        if project_number and str(project_number).strip():
            site_code = f"{site_code}{str(project_number)}".strip()

        return f"{company_code}/{location_code}-{site_code}/{type_code}"

    def _build_contract_name(self, prefix, seq_no_str, yy):
        return f"{prefix}/{seq_no_str}/{yy}" if prefix else f"{seq_no_str}/{yy}"
    
    # removed method
    def _max_used_seq_int_for_prefix_year(self, prefix, yy):
        """Find max used sequence integer from contract.application names."""
        ContractApp = self.env["contract.application"].sudo()

        if prefix:
            like_pat = f"{prefix}/%/{yy}"
        else:
            like_pat = f"%/{yy}"

        rows = ContractApp.search_read([("name", "like", like_pat)], ["name"])
        max_used = None
        for r in rows:
            seq_int = self._extract_seq_int_from_existing_contract_name(r.get("name"))
            if seq_int is None:
                continue
            max_used = seq_int if max_used is None else max(max_used, seq_int)
        return max_used

    #removed method
    def _sync_sequence_next_number(self, sequence, contract_application):
        prefix = self._get_contract_prefix(contract_application.property_sale_id)
        yy = self._get_yy_from_contract(contract_application)

        sequence.invalidate_recordset(["number_next", "number_next_actual"])
        try:
            next_no = int(sequence.number_next_actual or 0)
        except Exception:
            next_no = 0

        max_used = self._max_used_seq_int_for_prefix_year(prefix, yy)
        if max_used is not None and max_used >= next_no:
            sequence.sudo().write({"number_next": max_used + 1})

    #removed method
    def _generate_unique_contract_name(self, contract_application, sequence):
        prefix = self._get_contract_prefix(contract_application.property_sale_id)
        yy = self._get_yy_from_contract(contract_application)
        ContractApp = self.env["contract.application"].sudo()

        # self._sync_sequence_next_number(sequence, contract_application)
        
        seq_no_str = self._next_seq_number_padded_and_increment(sequence)

        candidate = self._build_contract_name(prefix, seq_no_str, yy)

        dup = ContractApp.search(
            [("name", "=", candidate), ("id", "!=", contract_application.id)],
            limit=1,
        )
        
        if dup:
            raise ValidationError(_(
                "The generated Contract Number '%s' is already in use.\n"
                "Please manually adjust the sequence '%s' to a higher value before confirming."
            ) % (candidate, sequence.name))

        return candidate

    def _precheck_contract_generation_setup(self):
        for sale in self:
            if not sale.property_id:
                raise ValidationError(_("A property is required before confirming the sale."))

            if not sale.property_id.site:
                raise ValidationError(_("A site is required on the property before confirming the sale."))

            mapping_line = sale._get_company_site_mapping_line(sale.property_id.site)
            if not mapping_line:
                raise ValidationError(_(
                    "No Company Site Mapping was found for site '%s'.\n"
                    "Please configure it before confirming the sale."
                ) % sale.property_id.site.display_name)

            template = sale._find_template_for_site(sale.property_id.site)
            if not template:
                raise ValidationError(_(
                    "No active Contract Template was found for site '%s'."
                ) % sale.property_id.site.display_name)

            if sale.template_id != template:
                sale.template_id = template

            sequence = sale._get_sequence_for_sale(sale, template)
            if not sequence:
                raise ValidationError(_(
                    "Contract Template '%s' is missing a sequence configuration. "
                    "Make sure a Developer with a sequence is assigned or 'Use Property Type Sequences' is properly configured."
                ) % template.display_name)

            # force all prefix parts to validate before confirmation
            sale._get_contract_prefix(sale)

    def _generate_valid_candidate_name(self, sale, contract_application, sequence):
        prefix = self._get_contract_prefix(sale)
        yy = self._get_yy_from_contract(contract_application)

        next_no = sequence.number_next_actual
        padding = int(sequence.padding or 0)
        seq_no_str = str(next_no).zfill(padding) if padding else str(next_no)

        candidate = self._build_contract_name(prefix, seq_no_str, yy)

        domain = [("name", "=", candidate)]
        if hasattr(contract_application, 'id') and isinstance(contract_application.id, int):
            domain.append(("id", "!=", contract_application.id))

        dup = self.env["contract.application"].sudo().search(domain, limit=1)
        
        if dup:
            raise ValidationError(_(
                "The generated Contract Number '%s' is already in use.\n"
                "Please manually adjust the sequence '%s' to a higher value before confirming."
            ) % (candidate, sequence.name))

        return candidate


    def action_confirm(self):

        sales_to_generate = self.filtered(lambda s: not getattr(s, 'skip_contract_generation', False))

        if sales_to_generate:
            sales_to_generate._precheck_contract_generation_setup()

        ContractApp = self.env["contract.application"].sudo()
        candidates = {}

        for sale in sales_to_generate:
            contract_application = ContractApp.search(
                [("property_sale_id", "=", sale.id)], limit=1
            )
            if not contract_application:
                contract_application = ContractApp.new({"property_sale_id": sale.id})

            seq = sale._get_sequence_for_sale(sale, sale.template_id)
            if seq:
                candidates[sale.id] = self._generate_valid_candidate_name(sale, contract_application, seq)

        res = super(PropertySale, self.with_context(skip_contract_unique_check=True)).action_confirm()

        for sale in sales_to_generate:
            if sale.id in candidates:
                contract_application = ContractApp.search(
                    [("property_sale_id", "=", sale.id)], limit=1
                )
                if contract_application:
                    contract_application.write({'name': candidates[sale.id]})

        return res