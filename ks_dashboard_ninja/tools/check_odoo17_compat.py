#!/usr/bin/env python3
"""Simple scanner to find potentially incompatible patterns for Odoo 17 migration.
Run from module root: `python3 tools/check_odoo17_compat.py`
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PATTERNS = {
    'DEFAULT_SERVER_DATETIME_FORMAT': r'DEFAULT_SERVER_DATETIME_FORMAT',
    'odoo.tools.misc import': r'from odoo.tools.misc import',
    'safe_eval import': r'from odoo.tools.safe_eval import',
    'web.Dialog usage': r"require\('web.Dialog'\)|require\(""" + "'web.Dialog'\)" ,
}

def main():
    print(f"Scanning module: {ROOT}\n")
    py_files = list(ROOT.rglob('*.py'))
    findings = []
    for p in py_files:
        text = p.read_text(encoding='utf-8')
        for name, pat in PATTERNS.items():
            if re.search(pat, text):
                findings.append((p.relative_to(ROOT), name))

    if not findings:
        print('No obvious matches found for the simple patterns.')
        return 0

    print('Potential matches:')
    for f, name in findings:
        print(f'- {f}: {name}')

    return 0

if __name__ == '__main__':
    raise SystemExit(main())
