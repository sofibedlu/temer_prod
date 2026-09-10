# -*- coding: utf-8 -*-
{
    'name': "Property Finishing Rate & Commercial Amount",
    'version': '17.0.1.0.0',
    'summary': "Rate/m² for fully finished properties + commercial amount for reservation advance",
    'author': "Custom",
    'category': 'Sales',
    'depends': [
        'ahadubit_property_base',
        'ahadubit_property_reservation',
        'temer_property_price_edit',
    ],
    'data': [
        'views/property_views.xml',
        'views/reservation_views.xml',
    ],
    'license': 'OPL-1',
    'installable': True,
    'application': False,
    'auto_install': False,
}
