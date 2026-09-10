# -*- coding: utf-8 -*-


def post_init_hook(env):
    """Run once on install: fix existing expire dates on Sunday/holiday."""
    env['property.reservation']._fix_all_sunday_holiday()
