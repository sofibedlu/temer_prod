from odoo.exceptions import UserError

def prevent_uninstall_hook(env):
    # force a rollback of the uninstallation
    raise UserError("Uninstallation of this module is restricted.")