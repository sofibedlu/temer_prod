# -*- coding: utf-8 -*-

from . import models

def pre_init_hook(cr):
    from .hooks import pre_init_hook
    return pre_init_hook(cr)

def post_init_hook(cr, registry):
    from odoo import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})
    from .hooks import post_init_hook
    return post_init_hook(env)

def post_load_hook():
    from odoo import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})
    from .hooks import post_load_hook
    return post_load_hook(env)