# -*- coding: utf-8 -*-
# Duplicate-phone check: ONLY Temer Lead (temer.lead) + Old CRM (crm.lead). No crm_custom_menu.

from odoo import _, models


class WingDuplicatePhoneMixin(models.AbstractModel):
    _name = "wing.duplicate.phone.mixin"
    _description = "Wing: duplicate check from temer.lead and old crm.lead only"

    def _wing_norm_phone(self, val):
        """Normalize to 9+ digit local phone (no +251/251/0)."""
        if not val or not str(val).strip():
            return None
        p = str(val).strip()
        p = p.replace(" ", "").replace("-", "").replace("+", "")
        if p.startswith("251"):
            p = p[3:]
        if p.startswith("0"):
            p = p[1:]
        return p if p and len(p) >= 9 else None

    def _dup_msg_for_salesperson(self, salesperson, fallback_msg=None):
        if not salesperson:
            return _("Customer is already registered (Unassigned).")
        if not self._wing_user_has_phone(salesperson):
            return _(
                "Customer already registered by %s but the assigned salesperson does not have a phone number in the system."
            ) % (salesperson.name or _("Unknown"))
        return fallback_msg or _("Customer is already registered by %s.") % (salesperson.name or _("Unknown"))

    def _wing_find_existing_temer_and_old_crm_only(self, full_phone_number):
        """
        Check ONLY temer.lead and old crm.lead. No crm_custom_menu.
        Returns (salesperson, supervisor, message) or (None, None, False) if not found.
        """
        phone9 = self._wing_norm_phone(full_phone_number)
        if not phone9:
            return None, None, False
        phone_251 = f"+251{phone9}" if not str(full_phone_number or "").strip().startswith("+") else full_phone_number

        # 1) Temer Lead (authoritative existing customer)
        TemerLead = self.env.get("temer.lead")
        if TemerLead:
            # First, check temer.phone directly (authoritative)
            # Tail matching for robustness (last 9 digits)
            tail = phone9[-9:] if phone9 and len(phone9) >= 9 else None
            domain_phone = ["|", "|", ("phone", "=", phone9), ("phone", "=", phone_251)]
            if tail:
                domain_phone = ["|"] + domain_phone + [("phone", "ilike", tail)]
            
            existing_phone = self.env["temer.phone"].sudo().search(domain_phone, limit=1)
            lead = existing_phone.lead_id if existing_phone else None
            
            if not lead:
                # Fallback to phone_no on temer.lead
                domain_lead = ["|", ("phone_no", "=", phone9), ("phone_no", "=", phone_251)]
                if tail:
                    domain_lead = ["|"] + domain_lead + [("phone_no", "ilike", tail)]
                lead = TemerLead.sudo().search(domain_lead, order="create_date desc", limit=1)
            
            if lead:
                user = getattr(lead, "user_id", None)
                msg = self._dup_msg_for_salesperson(user, _("Customer is already registered."))
                sup = None
                if user and hasattr(self, "_get_supervisor_for_salesperson"):
                    sup = self._get_supervisor_for_salesperson(user)
                return user, sup, msg

        # 2) Old CRM (crm.lead)
        salesperson, supervisor = self._wing_old_crm_existing_salesperson_info(phone_251)
        if salesperson:
            msg = self._dup_msg_for_salesperson(
                salesperson,
                _("In Old CRM (Leads) registered by: %s.") % (salesperson.name or _("Unknown")),
            )
            return salesperson, supervisor, msg
        elif self.env.get("crm.lead") and self._wing_old_crm_has_phone(phone_251):
            # Found in CRM but no user
            return None, None, _("Customer found in Old CRM (Leads) but has no assigned salesperson.")

        # 3) Other crm_custom_menu models (cross-check)
        for model_name, label in [
            ("crm.reception", _("Reception CRM")),
            ("crm.website", _("Website CRM")),
            ("crm.callcenter", _("Call Center CRM")),
        ]:
            if self.env.get(model_name):
                Model = self.env[model_name].sudo()
                domain = [
                    "|",
                    ("full_phone.name", "=", phone9),
                    ("full_phone.name", "=", phone_251),
                ]
                # Avoid matching current record if it has an id
                if self.ids and self._name == model_name:
                    domain.append(("id", "not in", self.ids))
                
                # Check for record one-by-one or by phone table
                rec = Model.search(domain, order="create_date desc", limit=1)
                
                # Broadest fallback: check phone tables for these models
                if not rec:
                    phone_model = model_name + ".phone"
                    if self.env.get(phone_model):
                        phone_rec = self.env[phone_model].sudo().search([("name", "in", [phone9, phone_251])], limit=1)
                        if phone_rec:
                            # Try to find the record that owns this phone
                            ref_field = model_name.split(".")[-1] + "_record_id" # e.g. website_record_id, callcenter_record_id
                            if hasattr(phone_rec, ref_field) and getattr(phone_rec, ref_field):
                                rec = getattr(phone_rec, ref_field)
                            elif hasattr(phone_rec, "reception_record_id") and phone_rec.reception_record_id:
                                rec = phone_rec.reception_record_id

                if rec:
                    sp = getattr(rec, "assigned_salesperson_id", None) or getattr(rec, "nominated_salesperson_id", None)
                    msg = self._dup_msg_for_salesperson(
                        sp, _("In %s registered by: %s.") % (label, sp.name if sp else _("Unknown"))
                    )
                    sup = None
                    if sp and hasattr(self, "_get_supervisor_for_salesperson"):
                        sup = self._get_supervisor_for_salesperson(sp)
                    return sp, sup, msg

        return None, None, False

    def _get_duplicate_phone_message(self, full_phone_number, exclude_ids=None):
        """
        Used by crm_custom_menu create/write. 
        Returns (salesperson, supervisor, message) or (None, None, False) if not found.
        """
        _sp, _sup, message = self._wing_find_existing_temer_and_old_crm_only(full_phone_number)
        return message

    def _get_existing_salesperson_info(self, full_phone_number):
        """
        Used by crm_custom_menu create/write.
        Returns (salesperson, supervisor, existing_temer_lead_id) or (None, None, False).
        """
        sp, sup, _msg = self._wing_find_existing_temer_and_old_crm_only(full_phone_number)
        
        # We also need to explicitly find the temer lead if it exists
        temer_lead_id = False
        TemerLead = self.env.get("temer.lead")
        if TemerLead:
            phone9 = self._wing_norm_phone(full_phone_number)
            phone_251 = f"+251{phone9}" if not str(full_phone_number or "").strip().startswith("+") else full_phone_number
            tail = phone9[-9:] if phone9 and len(phone9) >= 9 else None
            domain_phone = ["|", "|", ("phone", "=", phone9), ("phone", "=", phone_251)]
            if tail:
                domain_phone = ["|"] + domain_phone + [("phone", "ilike", tail)]
            existing_phone = self.env["temer.phone"].sudo().search(domain_phone, limit=1)
            if existing_phone and existing_phone.lead_id:
                temer_lead_id = existing_phone.lead_id.id
            if not temer_lead_id:
                domain_lead = ["|", ("phone_no", "=", phone9), ("phone_no", "=", phone_251)]
                if tail:
                    domain_lead = ["|"] + domain_lead + [("phone_no", "ilike", tail)]
                lead = TemerLead.sudo().search(domain_lead, order="create_date desc", limit=1)
                if lead:
                    temer_lead_id = lead.id

        if sp or temer_lead_id:
            return sp, sup, temer_lead_id
        return None, None, False

    def _wing_backfill_duplicate_owner_from_phone(self, full_phone_number):
        """
        Set duplicate fields from temer.lead + old crm.lead + cross-model checks.
        Returns True if a duplicate was found (even if unassigned).
        """
        self.ensure_one()
        salesperson, supervisor, msg = self._wing_find_existing_temer_and_old_crm_only(full_phone_number)
        
        # If no message, then no duplicate was found at all
        if not msg:
            return False

        vals = {}
        if salesperson and "existing_salesperson_id" in self._fields:
            vals["existing_salesperson_id"] = salesperson.id
        if supervisor and "existing_supervisor_id" in self._fields:
            if getattr(supervisor, "_name", None) in ["property.sales.supervisor", "res.users"]:
                vals["existing_supervisor_id"] = supervisor.id
            elif getattr(supervisor, "name", None) and getattr(supervisor.name, "_name", None) == "res.users":
                vals["existing_supervisor_id"] = supervisor.name.id
        
        if "phone_number_message" in self._fields:
            vals["phone_number_message"] = msg
        if "wing_duplicate_popup_pending" in self._fields:
            vals["wing_duplicate_popup_pending"] = True

        # Set existing_temer_lead_id explicitly using search (most reliable)
        if "existing_temer_lead_id" in self._fields:
            _sp, _sup, t_id = self._get_existing_salesperson_info(full_phone_number)
            if t_id:
                vals["existing_temer_lead_id"] = t_id

        if vals:
            self.sudo().write(vals)
            return True
        return False

    def _wing_old_crm_has_phone(self, phone):
        if not self.env.get("crm.lead"):
            return False
        return bool(self.env["crm.lead"].sudo().search_count(["|", ("phone", "=", phone), ("mobile", "=", phone)]))

    def _wing_old_crm_duplicate_message(self, full_phone_number, exclude_ids=None):
        """If phone found in crm.lead, return message line. Else return None."""
        exclude_ids = exclude_ids or []
        if not self.env.get("crm.lead"):
            return None
        CrmLead = self.env["crm.lead"].sudo()
        domain = [
            "|",
            ("phone", "=", full_phone_number),
            ("mobile", "=", full_phone_number),
        ]
        if exclude_ids:
            domain.append(("id", "not in", exclude_ids))
        if "active" in CrmLead._fields:
            domain.append(("active", "=", True))
        old_lead = CrmLead.search(domain, order="create_date desc", limit=1)
        if old_lead and getattr(old_lead, "user_id", None) and old_lead.user_id:
            return _("In Old CRM (Leads) registered by: %s.") % (old_lead.user_id.name or _("Unknown"))
        return None

    def _wing_old_crm_existing_salesperson_info(self, full_phone_number):
        """If phone found in crm.lead, return (salesperson, supervisor). Else (None, None)."""
        if not self.env.get("crm.lead"):
            return None, None
        CrmLead = self.env["crm.lead"].sudo()
        domain = [
            "|",
            ("phone", "=", full_phone_number),
            ("mobile", "=", full_phone_number),
        ]
        if "active" in CrmLead._fields:
            domain.append(("active", "=", True))
        old_lead = CrmLead.search(domain, order="create_date desc", limit=1)
        if old_lead and getattr(old_lead, "user_id", None) and old_lead.user_id:
            salesperson = old_lead.user_id
            supervisor = self._get_supervisor_for_salesperson(salesperson)
            return salesperson, supervisor
        return None, None

    def _wing_user_has_phone(self, user):
        """Return True if user has a phone, mobile, or any contact value (including phone stored in email/login field)."""
        if not user:
            return False
        partner = getattr(user, "partner_id", None)
        if partner:
            if partner.phone or partner.mobile:
                return True
            if getattr(partner, "email", None) and str(partner.email).strip():
                return True
        # user.login is the "Email Address" field on the Odoo user form
        for val in (getattr(user, "email", None), getattr(user, "login", None)):
            if val and str(val).strip():
                return True
        return False
