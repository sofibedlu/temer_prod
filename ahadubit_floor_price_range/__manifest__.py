# -*- coding: utf-8 -*-
{
    'name': "Floor Price Range",
    'version': '17.0.1.0.0',
    'summary': "Configure price per m2 by site and floor range; set Property Price(m2) from selected floor",
    'description': """
        - Registration site: Price per m2 can be saved as 0.
        - Configuration > Floor price range: define site, floor from/to, and price.
        - Property registration: Price(m2) is set from the matching floor range when a floor is selected; Sales Price calculates as before.
    """,
    'author': "Ahadubit Technologies",
    'website': "https://ahadubit.com/",
    'category': 'Property',
    'depends': [
        'ahadubit_property_base',
        'contract_sections',  # load after so floor price (e.g. 5,000) wins over site price_per_m2
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/property_site_views.xml',
        'views/floor_price_range_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
