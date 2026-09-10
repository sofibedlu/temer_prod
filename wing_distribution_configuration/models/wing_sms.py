# -*- coding: utf-8 -*-
"""Shared SMS helper for wing_distribution_configuration – AfroMessage API."""

import logging
import requests

_logger = logging.getLogger(__name__)

# Token and Identifier ID: wing uses its own token; from=identifier from crm_custom_menu
AFROMESSAGE_TOKEN_DEFAULT = (
    "eyJhbGciOiJIUzI1NiJ9.eyJpZGVudGlmaWVyIjoiQ2JsdHB6dHRFNkNaR1BjZ2VHWjRidThDUzMyOXczNWMiLCJleHAiOjE5Mjk4NzE1NjYsImlhdCI6MTc3MjEwNTE2NiwianRpIjoiNDZiZjhiYWMtNjhiOS00NmMzLWFjZTctMGZkNDMyNTM5YjMxIn0.3XK4_j0brTi7DkzE37YNVponFjzXyJo5w0a7TAr-7_Y"
)
AFROMESSAGE_FROM_DEFAULT = "e80ad9d8-adf3-463f-80f4-7c4b39f7f164"  # Identifier ID from crm_custom_menu
AFROMESSAGE_SENDER_DEFAULT = "Temer RE"  # Approved sender (same as crm_custom_menu)


def _get_afromessage_config(env):
    """Read config from ir.config_parameter; fallback to defaults."""
    Param = env["ir.config_parameter"].sudo()
    token = Param.get_param("wing.afromessage.token") or AFROMESSAGE_TOKEN_DEFAULT
    from_val = Param.get_param("wing.afromessage.from")
    if from_val in (None, False):
        from_val = AFROMESSAGE_FROM_DEFAULT
    sender = Param.get_param("wing.afromessage.sender") or AFROMESSAGE_SENDER_DEFAULT
    return token, (from_val or "").strip(), (sender or "").strip()


def send_test_sms_to_0970414609(env=None):
    """Send a test SMS to 0970414609. Returns (success, message). env required for config."""
    if env is None:
        import odoo
        env = odoo.api.Environment(odoo.registry(odoo.tools.config["db_name"]), odoo.SUPERUSER_ID, {})
    return send_sms_afromessage(mobile_number="0970414609", message="Test SMS from Temer Properties - Wing Distribution", env=env)


def send_sms_afromessage(mobile_number, message, env=None):
    """Send SMS via AfroMessage API. Returns (success: bool, message: str). env optional for config override."""
    try:
        if env:
            token, from_val, sender = _get_afromessage_config(env)
        else:
            import odoo
            e = odoo.api.Environment(odoo.registry(odoo.tools.config["db_name"]), odoo.SUPERUSER_ID, {})
            token, from_val, sender = _get_afromessage_config(e)
        mobile_number = mobile_number.replace(" ", "").replace("-", "").replace("+", "")
        base_url = "https://api.afromessage.com/api/send"
        headers = {"Authorization": "Bearer " + token}
        params = {"to": mobile_number, "message": message, "callback": ""}
        if from_val:
            params["from"] = from_val
        if sender:
            params["sender"] = sender
        result = requests.get(base_url, params=params, headers=headers, timeout=15)
        # AfroMessage can return 200 with different success payloads. Be tolerant here,
        # but always log the full response for troubleshooting.
        content_text = ""
        try:
            content_text = result.text
        except Exception:
            content_text = str(getattr(result, "content", b""))

        if result.status_code in (200, 201):
            try:
                json_response = result.json()
            except Exception:
                _logger.warning(
                    "Wing Distribution SMS: non-JSON response (status=%s) to=%s sender=%s body=%s",
                    result.status_code,
                    mobile_number,
                    sender,
                    content_text[:500],
                )
                # If API returns 200/201 but not JSON, treat as success (older gateway behavior).
                return True, "SMS sent successfully"

            _logger.info(
                "Wing Distribution SMS response (status=%s) to=%s sender=%s json=%s",
                result.status_code,
                mobile_number,
                sender,
                json_response,
            )

            # Explicit error in JSON → treat as failure
            ack = json_response.get("acknowledge") or json_response.get("ack") or json_response.get("status")
            if isinstance(ack, str):
                ack_norm = ack.strip().lower()
                if ack_norm in ("error", "fail", "failed", "rejected", "invalid"):
                    return False, f"AfroMessage API error: {json_response}"
                if ack_norm in ("success", "ok", "accepted", "queued", "sent"):
                    return True, "SMS sent successfully"
            if json_response.get("error") or json_response.get("success") is False:
                return False, f"AfroMessage API error: {json_response}"
            # Success indicators
            if json_response.get("id") or json_response.get("message_id") or json_response.get("messageId"):
                return True, "SMS sent successfully"

            return False, f"AfroMessage API error: {json_response}"

        _logger.warning(
            "Wing Distribution SMS HTTP error (status=%s) to=%s sender=%s body=%s",
            result.status_code,
            mobile_number,
            sender,
            content_text[:500],
        )
        return False, f"HTTP error: {result.status_code}, Message: {content_text}"
    except Exception as e:
        _logger.exception("Wing Distribution SMS failed for %s: %s", mobile_number, e)
        return False, str(e)
