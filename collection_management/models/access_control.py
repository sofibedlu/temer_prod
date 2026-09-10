from odoo import _
from odoo.exceptions import AccessError

FEATURE_GROUP = {
    "payment_initiate": "collection_management.group_collection_payment_initiator",
    "due_date_edit": "collection_management.group_collection_due_date_editor",
    "penalty_manage": "collection_management.group_collection_penalty_manager",
    "milestone_update": "collection_management.group_collection_milestone_manager",
    "notify_send": "collection_management.group_collection_notification_sender",
    "early_settlement": "collection_management.group_collection_settlement_manager",
}


def require_feature(env, feature: str, message: str | None = None) -> None:
    xmlid = FEATURE_GROUP.get(feature)
    if not xmlid:
        raise AccessError(_("Unknown access feature: %s") % feature)

    if not env.user.has_group(xmlid):
        raise AccessError(message or _("You are not allowed to perform this operation."))