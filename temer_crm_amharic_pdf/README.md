# Temer CRM – Amharic PDF Reports

This module fixes **Amharic** (and other Ethiopic script) text in the **Lead Activity Report** PDF. Without it, such text can appear as `???` or blank when printing.

## Installation

1. Install the module **Temer CRM – Amharic PDF Reports** (`temer_crm_amharic_pdf`) as usual (it depends on `temer_crm`).
2. Restart Odoo. No font files or extra setup are required.

## How it works

Same approach as the **Contract** module (`contract_sections`): the report template imports **Noto Sans Ethiopic** from Google Fonts (`@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Ethiopic:...')`) and applies it to the report body. The PDF engine loads the font from Google when generating the report, so it works **locally and on the server** as long as the server can reach `fonts.googleapis.com`.

No local font file or controller is used.
