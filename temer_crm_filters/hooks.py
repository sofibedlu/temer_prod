# -*- coding: utf-8 -*-

def post_init_hook(env):
    """Point My Leads and All Leads actions to our search view (extended search + filters)."""
    action_my = env.ref('temer_crm.action_temer_lead_my', raise_if_not_found=False)
    action_all = env.ref('temer_crm.action_temer_lead_all', raise_if_not_found=False)
    search_my = env.ref('temer_crm_filters.view_temer_lead_search_filters', raise_if_not_found=False)
    search_all = env.ref('temer_crm_filters.view_temer_lead_search_all_filters', raise_if_not_found=False)
    if action_my and search_my:
        action_my.search_view_id = search_my
    if action_all and search_all:
        action_all.search_view_id = search_all
