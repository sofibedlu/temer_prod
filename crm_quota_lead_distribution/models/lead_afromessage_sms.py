# -*- coding: utf-8 -*-
"""AfroMessage SMS gateway (no wing_distribution_configuration dependency)."""

import logging

import requests

_logger = logging.getLogger(__name__)

AFROMESSAGE_TOKEN_DEFAULT = (
    "eyJhbGciOiJIUzI1NiJ9.eyJpZGVudGlmaWVyIjoiQ2JsdHB6dHRFNkNaR1BjZ2VHWjRidThDUzMyOXczNWMiLCJleHAiOjE5Mjk4NzE1NjYsImlhdCI6MTc3MjEwNTE2NiwianRpIjoiNDZiZjhiYWMtNjhiOS00NmMzLWFjZTctMGZkNDMyNTM5YjMxIn0.3XK4_j0brTi7DkzE37YNVponFjzXyJo5w0a7TAr-7_Y"
)
AFROMESSAGE_FROM_DEFAULT = "e80ad9d8-adf3-463f-80f4-7c4b39f7f164"
AFROMESSAGE_SENDER_DEFAULT = "Temer RE"


def _get_afromessage_config(env):
    param = env["ir.config_parameter"].sudo()
    token = param.get_param("wing.afromessage.token") or AFROMESSAGE_TOKEN_DEFAULT
    from_val = param.get_param("wing.afromessage.from")
    if from_val in (None, False):
        from_val = AFROMESSAGE_FROM_DEFAULT
    sender = param.get_param("wing.afromessage.sender") or AFROMESSAGE_SENDER_DEFAULT
    return token, (from_val or "").strip(), (sender or "").strip()


def send_sms_afromessage(mobile_number, message, env=None):
    """Send SMS via AfroMessage API. Returns (success, message)."""
    if not env:
        return False, "No environment for SMS."
    try:
        token, from_val, sender = _get_afromessage_config(env)
        mobile_number = (
            str(mobile_number).replace(" ", "").replace("-", "").replace("+", "")
        )
        base_url = "https://api.afromessage.com/api/send"
        headers = {"Authorization": "Bearer " + token}
        params = {"to": mobile_number, "message": message, "callback": ""}
        if from_val:
            params["from"] = from_val
        if sender:
            params["sender"] = sender
        result = requests.get(base_url, params=params, headers=headers, timeout=15)
        if result.status_code in (200, 201):
            try:
                json_response = result.json()
            except Exception:
                return True, "SMS sent successfully"
            if isinstance(json_response, dict):
                ack = json_response.get("acknowledge") or json_response.get("acknowledgement")
                if ack in (True, "true", "success", "Success"):
                    return True, "SMS sent successfully"
                if json_response.get("error"):
                    return False, str(json_response.get("error"))
            return True, "SMS sent successfully"
        return False, "SMS API returned status %s" % result.status_code
    except Exception as exc:
        _logger.exception("Lead distribution SMS failed: %s", exc)
        return False, str(exc)
