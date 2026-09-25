Migration checklist — ks_dashboard_ninja -> Odoo 17
===============================================

This file contains the first steps and notes for migrating the ks_dashboard_ninja module from Odoo 15 to Odoo 17.

1) Manifest
   - Bumped `version` to indicate Odoo 17 target.
   - Verify `assets` entries are correct for Odoo 17.

2) Development environment
   - Start an Odoo 17 instance and include this module in `addons_path`.
   - Update apps list and attempt installation to get runtime errors.

3) Python compatibility
   - Run `pylint`/`flake8` (optional) and start Odoo to capture import/runtime deprecations.
   - Pay attention to usages of deprecated APIs (odoo.tools.misc, safe_eval locations, etc.).

4) JS compatibility (minimal approach)
   - Keep existing `odoo.define` modules; update `require()` paths if any import paths changed in Odoo 17.
   - Ensure asset names in manifest match bundles expected by Odoo 17 (`web.assets_backend`, `web.assets_qweb`).

5) XML/QWeb
   - Load views and QWeb templates; fix any attribute changes or removed attrs.

6) Testing & verification
   - Create a DB, install the module, open Dashboard, add/edit/delete items, render charts, and monitor server and browser console for errors.

Quick local test commands

```bash
# from module root
cp -r ks_dashboard_ninja /path/to/odoo17/addons/
# restart Odoo 17 service, then update apps list and install the module via UI or:
odoo -c /etc/odoo/odoo.conf -d your_test_db --update=ks_dashboard_ninja --stop-after-init
```

Notes
- This repository will be migrated incrementally. Next: run a code scan for obvious deprecated API usage and list concrete changes.
