# -*- coding: utf-8 -*-

def pre_init_hook(cr):
    """
    Migrate wing.distribution.line from distribution_type_id to distribution_type_ids
    before the model is loaded. Must run before Odoo applies schema changes.
    """
    import logging
    _log = logging.getLogger(__name__)
    
    # Check if the old column exists
    cr.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'wing_distribution_line' AND column_name = 'distribution_type_id'
    """)
    has_old_column = cr.fetchone() is not None
    
    # Create m2m table if it doesn't exist
    cr.execute("""
        CREATE TABLE IF NOT EXISTS wing_distribution_line_type_rel (
            line_id INTEGER NOT NULL,
            type_id INTEGER NOT NULL,
            PRIMARY KEY (line_id, type_id)
        )
    """)
    
    if has_old_column:
        # Populate from old column
        cr.execute("""
            INSERT INTO wing_distribution_line_type_rel (line_id, type_id)
            SELECT id, distribution_type_id FROM wing_distribution_line
            WHERE distribution_type_id IS NOT NULL
            ON CONFLICT (line_id, type_id) DO NOTHING
        """)
        
        # Drop old constraint and column
        for stmt in [
            "ALTER TABLE wing_distribution_line DROP CONSTRAINT IF EXISTS wing_distribution_line_user_distribution_type_uniq",
            "ALTER TABLE wing_distribution_line DROP CONSTRAINT IF EXISTS user_distribution_type_uniq",
            "ALTER TABLE wing_distribution_line DROP COLUMN IF EXISTS distribution_type_id",
        ]:
            try:
                cr.execute(stmt)
            except Exception as e:
                _log.debug("Migration: %s failed: %s", stmt[:50], e)


def post_init_hook(env):
    """
    Post-install hook to fix any records that still have multiple types in one line.
    This runs after the module is fully loaded.
    """
    import logging
    _log = logging.getLogger(__name__)
    
    # Get the distribution line model
    DistributionLine = env['wing.distribution.line']
    
    # Find all lines with more than one distribution type
    lines_to_fix = DistributionLine.search([]).filtered(lambda l: len(l.distribution_type_ids) > 1)
    
    _log.info("Found %d lines with multiple distribution types to fix", len(lines_to_fix))
    
    fixed_count = 0
    for line in lines_to_fix:
        try:
            type_ids = line.distribution_type_ids.ids
            user_id = line.user_id.id
            
            _log.info("Fixing line %s for user %s with types: %s", 
                     line.id, user_id, type_ids)
            
            # Base values for new lines
            base_vals = {
                'user_id': user_id,
                'status': line.status or 'new',
                'active': line.active,
                'round_id': line.round_id.id if line.round_id else False,
            }
            
            # Create a new line for each type
            new_lines = []
            for type_id in type_ids:
                # Check if this type already exists for this user from another line
                existing = DistributionLine.search([
                    ('user_id', '=', user_id),
                    ('distribution_type_ids', 'in', [type_id]),
                    ('id', '!=', line.id),
                ], limit=1)
                
                if not existing:
                    line_vals = dict(base_vals)
                    line_vals['distribution_type_ids'] = [(6, 0, [type_id])]
                    new_line = DistributionLine.create(line_vals)
                    new_lines.append(new_line)
                    _log.info("  Created new line %s for type %s", new_line.id, type_id)
            
            # Archive the original line if we created new ones
            if new_lines:
                line.active = False
                fixed_count += 1
                _log.info("Archived original line %s and created %d new lines", 
                         line.id, len(new_lines))
            
            env.cr.commit()  # Commit after each record to avoid long transactions
            
        except Exception as e:
            _log.error("Error fixing line %s: %s", line.id, str(e))
            env.cr.rollback()
    
    _log.info("Post-init hook completed. Fixed %d lines with multiple types.", fixed_count)


def post_load_hook(env):
    """
    Run migrations and create ir.model.access for crm.reception.duplicate.wizard if the model exists.
    This avoids referencing the wizard in ir.model.access.csv, so module upgrade
    succeeds even when the wizard model is not yet loaded (e.g. deployment order).
    """
    # First run the post-init hook to fix any remaining multiple-type lines
    post_init_hook(env)
    
    # Then handle the wizard access
    if "crm.reception.duplicate.wizard" not in env:
        return
    Model = env["ir.model"].sudo()
    Access = env["ir.model.access"].sudo()
    model = Model.search([("model", "=", "crm.reception.duplicate.wizard")], limit=1)
    if not model:
        return
    group = env.ref("base.group_user", raise_if_not_found=False)
    if not group:
        return
    existing = Access.search(
        [
            ("model_id", "=", model.id),
            ("group_id", "=", group.id),
        ],
        limit=1,
    )
    if existing:
        return
    Access.create({
        "name": "crm.reception.duplicate.wizard",
        "model_id": model.id,
        "group_id": group.id,
        "perm_read": True,
        "perm_write": True,
        "perm_create": True,
        "perm_unlink": True,
    })