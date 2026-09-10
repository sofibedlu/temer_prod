# -*- coding: utf-8 -*-


def post_init_hook(env):
    """Default Head Office on existing distribution members."""
    head = env.ref(
        "crm_distribution_location.distribution_location_head_office",
        raise_if_not_found=False,
    )
    if not head:
        return
    Member = env["crm.wing.member"].sudo()
    members = Member.search([("location_id", "=", False)])
    if members:
        members.write({"location_id": head.id})
    env["crm.reception"]._clear_legacy_reception_locations()
