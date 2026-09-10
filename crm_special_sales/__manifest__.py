{
    "name": "Special Sales CRM",
    "version": "17.0.1.0.8",
    "category": "Sales",
    "summary": "Special Sales like Temer CRM: type (Company/Freelance/Employee), save in temer.lead",
    "description": """
        Special Sales under TEMER CRM. Same as Temer CRM: saves directly in temer.lead (no draft/sent).
        Type first: Company, Freelance, or Employee.
        - Employee: select customer from Contacts (res.partner).
        - Company / Freelance: enter customer name manually.
    """,
    "author": "Temer Properties",
    "depends": ["base", "mail", "temer_crm", "hr"],
    "data": [
        "security/crm_special_sales_groups.xml",
        "security/ir.model.access.csv",
        "data/temer_lead_type_data.xml",
        "data/crm_employee_ref_cron.xml",
        "views/crm_special_sales_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "crm_special_sales/static/src/views/fields/search_or_type_autocomplete.js",
            "crm_special_sales/static/src/views/fields/search_or_type_autocomplete.xml",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
    "post_init_hook": "post_init_hook",
}
