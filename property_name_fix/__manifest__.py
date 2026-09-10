# -*- coding: utf-8 -*-
{
    'name': 'Property Name Fix - Block at End',
    'version': '17.0.1.0.0',
    'category': 'Property',
    'summary': 'Fix property name generation: use house number, block at the end',
    'description': """
        Fixes the property name format to use house number (unit_number) and
        place block number at the END.
        Format: {Site}-F{Floor}-{HouseNumber}-{Block}
        Example: PAN-AJWA1 SHOP-F4-003-01
    """,
    'author': 'Temer',
    'depends': [
        'ahadubit_property_base',
        'bulk_property_registration',
        'property_type_details',
    ],
    'data': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
