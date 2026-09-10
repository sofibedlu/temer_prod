# -*- coding: utf-8 -*-
{
    'name': "Bulk Property Registration",
    'version': '17.0.1.0.0',
    'summary': "Bulk register multiple properties by site, floor range, and unit count",
    'description': """
        - Menu under Property: Bulk Registration.
        - Select site (read-only summary: project number, company, payment structure, address, price).
        - For mixed sites: select type (Residential/Commercial); for Commercial: inside/outside required.
        - Floor selection: Range (from-to) or Multiple (multi-select).
        - House number range (e.g. 01-4 = 4 units per floor); units numbered 01,02... per floor, then next floor continues.
        - Property type details (bedroom, bathroom, gross/net area, finishing) from site property type.
        - Generate creates preview lines; tab Properties shows all; Save as Draft / Save as Available creates individual property records.
    """,
    'author': "Ahadubit Technologies",
    'website': "https://ahadubit.com/",
    'category': 'Property',
    'depends': [
        'ahadubit_property_base',
        'advanced_property_unit_naming',
    ],
    'data': [
        'data/ir_sequence_data.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/property_bulk_registration_views.xml',
        'wizard/bulk_generate_message_wizard_views.xml',
        'wizard/bulk_edit_line_wizard_views.xml',
        'views/property_property_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
