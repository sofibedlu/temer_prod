# -*- coding: utf-8 -*-

from . import models

def post_init_hook(env):
    """
    This hook is executed after the module is installed or updated.
    It alters the 'property_type_id' column in 'property_property' table
    to make it nullable, as it's no longer required by this module.
    """
    env.cr.execute("""
        ALTER TABLE property_property
        ALTER COLUMN property_type_id DROP NOT NULL;
    """)

