{
    'name': 'Temer HR Employee Extension',
    'version': '17.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Extend Employee with Title, Identification, and Assets',
    'description': """
        This module extends hr.employee with:
        - Title field above name
        - Identification notebook page (TIN, Pension, Fayda)
        - Bank Account details (Char fields)
        - Company Assets tracking
    """,
    'author': 'Girma M.',
    'depends': ['hr', 'hr_contract', 'hr_skills', 'sh_all_in_one_hrms'],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_employee_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
