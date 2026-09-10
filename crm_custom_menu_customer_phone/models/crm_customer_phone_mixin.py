# -*- coding: utf-8 -*-
"""Country-aware phone helpers (uses res.country.phone_code, not hardcoded +251)."""


def customer_phone_line_model(record):
    return {
        "crm.reception": "crm.reception.phone",
        "crm.website": "crm.website.phone",
        "crm.callcenter": "crm.callcenter.phone",
    }.get(record._name)


def get_country_phone_code_from_vals(record, vals):
    country_id = vals.get("country_id") or record.env.context.get("default_country_id")
    if not country_id and len(record) == 1 and getattr(record, "country_id", None):
        country_id = record.country_id.id
    try:
        if isinstance(country_id, int) and country_id:
            country = record.env["res.country"].browse(country_id)
            code = str(getattr(country, "phone_code", "") or "").strip()
            return code or "251"
    except Exception:
        pass
    return "251"


def normalize_phone_from_vals(record, vals):
    raw = (vals.get("new_phone") or vals.get("phone_no") or "").strip()
    if not raw:
        return None
    if raw.startswith("+"):
        digits = "".join(ch for ch in raw if ch.isdigit())
        return f"+{digits}" if digits else None
    code = get_country_phone_code_from_vals(record, vals)
    digits = "".join(ch for ch in raw if ch.isdigit())
    if not digits:
        return None
    if digits.startswith(code):
        digits = digits[len(code) :]
    if digits.startswith("0"):
        digits = digits[1:]
    if not digits:
        return None
    return f"+{code}{digits}"


def get_new_phone_entry(record, vals):
    full_number = normalize_phone_from_vals(record, vals)
    if not full_number:
        return None
    phone_model = customer_phone_line_model(record)
    if not phone_model or phone_model not in record.env:
        return None
    Phone = record.env[phone_model].sudo()
    country_id = vals.get("country_id")
    if not country_id and len(record) == 1 and getattr(record, "country_id", None):
        country_id = record.country_id.id
    phone = Phone.search([("name", "=", full_number)], limit=1)
    if not phone:
        create_vals = {"name": full_number}
        if country_id and "country_id" in Phone._fields:
            create_vals["country_id"] = country_id
        phone = Phone.create(create_vals)
    elif country_id and hasattr(phone, "country_id") and not phone.country_id:
        phone.country_id = country_id
    return phone


def sync_phone_lines_country(records):
    for rec in records:
        if not rec.full_phone or not getattr(rec, "country_id", None):
            continue
        for phone in rec.full_phone:
            if hasattr(phone, "country_id") and not phone.country_id:
                phone.country_id = rec.country_id.id


def merge_full_phone_entry(record, phone_entry, saved_ids=None):
    if not phone_entry:
        return
    existing = list(saved_ids or record.full_phone.ids)
    if phone_entry.id not in existing:
        existing.append(phone_entry.id)
    record.with_context(no_clear_new_phone=True).write({"full_phone": [(6, 0, existing)]})


def phone_lookup_variants(record, vals_or_phone):
    """E.164 and legacy variants so +971 and +251 match the same customer."""
    if isinstance(vals_or_phone, dict):
        primary = normalize_phone_from_vals(record, vals_or_phone)
        country_id = vals_or_phone.get("country_id")
    else:
        primary = (vals_or_phone or "").strip() or None
        country_id = None
        if not country_id and len(record) == 1 and getattr(record, "country_id", None):
            country_id = record.country_id.id
    variants = []
    seen = set()

    def _add(val):
        v = (val or "").strip()
        if v and v not in seen:
            seen.add(v)
            variants.append(v)

    _add(primary)
    raw = ""
    if isinstance(vals_or_phone, dict):
        raw = (vals_or_phone.get("new_phone") or vals_or_phone.get("phone_no") or "").strip()
    elif vals_or_phone:
        raw = str(vals_or_phone).strip()
    digits = "".join(ch for ch in raw if ch.isdigit())
    if digits.startswith("0"):
        digits = digits[1:]
    if primary:
        digits = "".join(ch for ch in primary if ch.isdigit())
    if digits:
        _add(digits)
        _add(f"+{digits}")
        _add(f"+251{digits}")
        code = get_country_phone_code_from_vals(
            record, {"country_id": country_id} if country_id else {}
        )
        if code and code != "251":
            _add(f"+{code}{digits}")
        tail = digits[-9:] if len(digits) >= 9 else None
        if tail and tail != digits:
            _add(tail)
            _add(f"+251{tail}")
            if code and code != "251":
                _add(f"+{code}{tail}")
    return variants


def national_digits_from_raw(record, raw_phone):
    if not raw_phone:
        return ""
    vals = {"new_phone": raw_phone}
    if len(record) == 1 and record.country_id:
        vals["country_id"] = record.country_id.id
    full = normalize_phone_from_vals(record, vals)
    if full:
        code = (
            str(record.country_id.phone_code or "")
            if len(record) == 1 and record.country_id
            else ""
        )
        digits = "".join(ch for ch in full if ch.isdigit())
        if code and digits.startswith(code):
            return digits[len(code) :]
        return digits
    return "".join(ch for ch in raw_phone if ch.isdigit()).lstrip("0")


def _phone_digit_tail(phone_value):
    digits = "".join(ch for ch in (phone_value or "") if ch.isdigit())
    return digits[-9:] if len(digits) >= 9 else digits


def apply_correct_customer_phone(record, phone_entry):
    """
    Keep the country-correct number only.
    Removes mistaken +251... rows left by base crm_custom_menu (same last 9 digits).
    """
    if not phone_entry:
        return
    is_ethiopia = (
        getattr(record, "country_id", None)
        and (record.country_id.code or "").upper() == "ET"
    )
    correct_tail = _phone_digit_tail(phone_entry.name)
    keep_ids = []

    for line in record.full_phone:
        if line.id == phone_entry.id:
            keep_ids.append(line.id)
            continue
        if not is_ethiopia and line.name.startswith("+251") and correct_tail:
            line_tail = _phone_digit_tail(line.name)
            if line_tail == correct_tail:
                line.unlink()
                continue
        if line.id not in keep_ids:
            keep_ids.append(line.id)

    if phone_entry.id not in keep_ids:
        keep_ids.append(phone_entry.id)

    record.with_context(no_clear_new_phone=True).write(
        {"full_phone": [(6, 0, keep_ids)]}
    )


def replace_wrong_country_phone_lines(record, phone_entry):
    apply_correct_customer_phone(record, phone_entry)
