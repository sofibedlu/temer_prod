from . import models
from . import controllers

def post_init_hook(env):
    """Post-init hook to assign manager group to managers"""
    try:
        import logging
        _logger = logging.getLogger(__name__)
        _logger.info("=" * 80)
        _logger.info("=== SALES PLAN MODULE: Running post_init_hook ===")
        
        ResUsers = env['res.users']
        ResUsers._assign_manager_group()
        
        # Also run debug check for all managers
        _logger.info("=== Running debug check for all managers ===")
        ResUsers.debug_all_managers_menu_access()
        
        _logger.info("=== SALES PLAN MODULE: post_init_hook completed ===")
        _logger.info("=" * 80)
    except Exception as e:
        import logging
        _logger = logging.getLogger(__name__)
        _logger.error(f"Error in post_init_hook: {e}", exc_info=True)