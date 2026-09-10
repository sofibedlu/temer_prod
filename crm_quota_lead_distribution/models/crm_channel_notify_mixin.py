# -*- coding: utf-8 -*-
import logging

from odoo import _, models

from .lead_afromessage_sms import send_sms_afromessage

_logger = logging.getLogger(__name__)


class CrmChannelNotifyMixin(models.AbstractModel):
    _name = "crm.channel.notify.mixin"
    _description = "CRM channel: SMS via Login only"

    def _wing_get_user_sms_target_and_email(self, user):
        return self.env["crm.lead.distribution"]._contact_from_login_only(user)

    def _wing_user_has_phone(self, user):
        return bool(
            self.env["crm.lead.distribution"]._contact_from_login_only(user)[0]
        )

    def _wing_user_has_supervisor(self, user):
        if not user:
            return False
        if hasattr(user, "active") and not user.active:
            return False
        if not self._wing_user_has_phone(user):
            return False
        sup = self._wing_get_supervisor_for_salesperson(user)
        if not sup:
            return False
        sup_user = None
        if getattr(sup, "_name", None) == "res.users":
            sup_user = sup
        elif getattr(sup, "name", None) and getattr(sup.name, "_name", None) == "res.users":
            sup_user = sup.name
        elif getattr(sup, "user_id", None) and getattr(sup.user_id, "_name", None) == "res.users":
            sup_user = sup.user_id
        return self._wing_user_has_phone(sup_user) if sup_user else True

    def _send_sms(self, mobile_number, message):
        return send_sms_afromessage(mobile_number, message, env=self.env)

    def _send_notification(self, mobile_number, email_address, message, recipient_name=""):
        dist = self.env["crm.lead.distribution"]
        number = (mobile_number or "").strip()
        if number:
            normalized = dist._normalize_sms_number(number)
            if normalized:
                return self._send_sms(normalized, message)
        _logger.info(
            "Lead distribution: skip SMS — no valid Login phone for %s",
            recipient_name or "recipient",
        )
        return False, ""

    def _wing_duplicate_message_for_salesperson(self, salesperson):
        return _("Customer is already registered.")

    def _get_customer_phone_from_record(self, override=None):
        phone = None
        if override and str(override).strip():
            phone = str(override).strip()
        if getattr(self, "phone_no", None) and str(self.phone_no).strip():
            phone = str(self.phone_no).strip()
        elif getattr(self, "new_phone", None) and str(self.new_phone).strip():
            if not phone:
                phone = str(self.new_phone).strip()
        if not phone and getattr(self, "full_phone", None) and self.full_phone:
            phone = (self.full_phone[0].name or "").strip()
        if phone and hasattr(self, "_normalize_phone"):
            phone = self._normalize_phone(phone) or phone
        phone = (phone or "").strip()
        try:
            country = getattr(self, "country_id", None)
            if country and getattr(country, "phone_code", None) and phone:
                local = phone.replace(" ", "").replace("-", "").replace("+", "")
                code = str(country.phone_code)
                if local.startswith(code):
                    local = local[len(code):]
                if local.startswith("0"):
                    local = local[1:]
                if local:
                    return "+%s%s" % (code, local)
        except Exception:
            pass
        return phone

    def _send_sales_team_sms(
        self,
        salesperson,
        supervisor,
        customer_name,
        customer_phone,
        source,
        is_existing=False,
        lead=None,
    ):
        self.ensure_one()
        if not salesperson:
            return False, _("No salesperson to notify.")
        sales_mobile, _sales_email = self._wing_get_user_sms_target_and_email(salesperson)
        if not sales_mobile:
            if is_existing:
                return False, _(
                    "Customer already registered but the assigned salesperson "
                    "does not have a valid Login phone."
                )
            return False, _("Salesperson has no valid Login phone.")
        sales_name = salesperson.name or "Sales Person"
        src = (source or "").strip() or "Walk In"
        phone_display = (customer_phone or "").strip() or ""
        cust_name = (customer_name or "").strip() or phone_display or "Customer"

        def _resolve_supervisor_user(sup):
            if not sup:
                return None
            if getattr(sup, "_name", None) == "res.users":
                return sup
            if getattr(sup, "name", None) and getattr(sup.name, "_name", None) == "res.users":
                return sup.name
            if getattr(sup, "user_id", None) and getattr(sup.user_id, "_name", None) == "res.users":
                return sup.user_id
            return None

        supervisor_user = _resolve_supervisor_user(supervisor)
        same_user = bool(
            supervisor_user and salesperson and supervisor_user.id == salesperson.id
        )

        if is_existing:
            sales_msg = _(
                "Hi %(sales)s, Customer: %(cust)s (%(phone)s) came via %(source)s. Please follow up."
            ) % {
                "sales": sales_name,
                "cust": cust_name,
                "phone": phone_display,
                "source": src,
            }
            supervisor_msg = None
            sup_mobile = None
            if not same_user and supervisor_user:
                sup_mobile, _sup_email = self._wing_get_user_sms_target_and_email(
                    supervisor_user
                )
                if sup_mobile:
                    supervisor_msg = _(
                        "Hi %(super)s, salesperson under your supervision %(sales)s's customer contacted us via %(source)s. Please follow up."
                    ) % {
                        "super": supervisor_user.name or "Supervisor",
                        "sales": sales_name,
                        "source": src,
                    }
        else:
            sales_msg = _(
                "Hi %(sales)s, New lead from %(source)s: Customer %(cust)s (%(phone)s). Please follow up."
            ) % {
                "sales": sales_name,
                "source": src,
                "cust": cust_name,
                "phone": phone_display,
            }
            supervisor_msg = None
            sup_mobile = None
            if not same_user and supervisor_user:
                sup_mobile, _sup_email = self._wing_get_user_sms_target_and_email(
                    supervisor_user
                )
                if sup_mobile:
                    supervisor_msg = _(
                        "Hi %(super)s, salesperson under your supervision %(sales)s got a new lead from %(source)s. Please follow up."
                    ) % {
                        "super": supervisor_user.name or "Supervisor",
                        "sales": sales_name,
                        "source": src,
                    }

        ok, err = self._send_notification(
            sales_mobile, None, sales_msg, salesperson.name or "salesperson"
        )
        if not ok:
            return False, err or _("Failed to send notification to salesperson.")
        if supervisor_msg and sup_mobile:
            ok2, err2 = self._send_notification(
                sup_mobile, None, supervisor_msg, supervisor_user.name or "supervisor"
            )
            if not ok2:
                return True, _(
                    "Notification sent to salesperson, but failed to send to supervisor (%(reason)s)."
                ) % {"reason": (err2 or _("unknown reason"))}
        return True, None

    def _send_sales_team_sms_from_record(
        self,
        source,
        is_existing=False,
        lead=None,
        customer_phone_override=None,
        salesperson_override=None,
        supervisor_override=None,
    ):
        self.ensure_one()
        if is_existing:
            salesperson = salesperson_override or (
                getattr(self, "existing_salesperson_id", None)
                and self.existing_salesperson_id
            )
            if not salesperson:
                return False, _("No existing salesperson found for this phone number.")
            supervisor = supervisor_override or (
                getattr(self, "existing_supervisor_id", None)
                and self.existing_supervisor_id
            )
        else:
            salesperson = salesperson_override or (
                getattr(self, "nominated_salesperson_id", None)
                and self.nominated_salesperson_id
            )
            if not salesperson:
                return False, _("No salesperson to notify.")
            supervisor = supervisor_override or (
                getattr(self, "nominated_supervisor_id", None)
                and self.nominated_supervisor_id
            )
        if not supervisor and salesperson and hasattr(self, "_get_supervisor_for_salesperson"):
            supervisor = self._get_supervisor_for_salesperson(salesperson)
        customer_name = (getattr(self, "customer_name", None) or "").strip() or "Customer"
        customer_phone = self._get_customer_phone_from_record(customer_phone_override)
        return self._send_sales_team_sms(
            salesperson=salesperson,
            supervisor=supervisor,
            customer_name=customer_name,
            customer_phone=customer_phone,
            source=source,
            is_existing=is_existing,
            lead=lead,
        )
