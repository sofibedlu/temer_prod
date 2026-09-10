{
    "name": "My Team Ban — Distribution Config",
    "version": "17.0.1.0.0",
    "summary": "Deactivate Distribution Configuration rows when a user is banned from My Team",
    "description": """
        When a Wing Manager or Sales Manager bans a team member in My Team,
        all active crm.wing.member (Distribution Configuration) rows for that
        user are set to inactive — same effect as archiving lines in the
        old Wing Distribution module.
    """,
    "category": "Sales",
    "author": "Temer Properties",
    "website": "https://www.temerproperties.com",
    "license": "LGPL-3",
    "depends": [
        "my_team",
        "crm_quota_lead_distribution",
    ],
    "data": [],
    "installable": True,
    "application": False,
    "auto_install": False,
}
