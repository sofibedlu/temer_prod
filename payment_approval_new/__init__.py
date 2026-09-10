# -*- coding: utf-8 -*-

from . import models
from . import wizard


def post_init_recompute_pending_installments(env):
    """Recompute state for all installments that have draft payment approvals"""
    try:
        import logging
        _logger = logging.getLogger(__name__)
        _logger.info("Starting post_init_recompute_pending_installments...")
        
        CollectionInstallment = env['collection.installment']
        if hasattr(CollectionInstallment, '_fix_all_pending_installments'):
            result = CollectionInstallment._fix_all_pending_installments()
            _logger.info(f"post_init_recompute_pending_installments completed. Result: {result}")
        else:
            _logger.warning("_fix_all_pending_installments method not found on CollectionInstallment")
    except Exception as e:
        import logging
        _logger = logging.getLogger(__name__)
        _logger.error(f"Error in post_init_recompute_pending_installments: {e}", exc_info=True)


def post_migrate_patch_pay_button(env):
    import re
    import logging
    _logger = logging.getLogger(__name__)

    views_to_patch = [
        'collection_management.view_collection_installment_form',
        'collection_management.view_collection_order_form',
    ]

    for xml_id in views_to_patch:
        try:
            view = env.ref(xml_id, raise_if_not_found=False)
            if not view:
                _logger.warning(f"View {xml_id} not found, skipping.")
                continue

            arch = view.arch
            old_val = "state == 'paid'"
            new_val = "state == 'paid' or state == 'pending'"

            if new_val in arch:
                _logger.info(f"{xml_id} already patched.")
                continue

            patched = re.sub(
                r'(<button\b[^>]*\bname=["\']action_open_payment_wizard["\'][^>]*\binvisible=["\'])' + re.escape(old_val) + r'(["\'])',
                lambda m: m.group(1) + new_val + m.group(2),
                arch,
            )
            if patched == arch:
                patched = re.sub(
                    r'(<button\b[^>]*\binvisible=["\'])' + re.escape(old_val) + r'(["\'][^>]*\bname=["\']action_open_payment_wizard["\'])',
                    lambda m: m.group(1) + new_val + m.group(2),
                    arch,
                )

            if patched != arch:
                view.sudo().write({'arch': patched})
                _logger.info(f"Patched Pay button in {xml_id}")
            else:
                _logger.warning(f"No match found for Pay button patch in {xml_id}")
        except Exception as e:
            _logger.error(f"Error patching {xml_id}: {e}", exc_info=True)
