# -*- coding: utf-8 -*-
{
    'name': "Reservation Contract Team Flow",
    'version': '17.0.1.0.1',
    'summary': "Route reservations to a contract team before contract creation.",
    'description': """
        - Add a Contract Team configuration under Property Reservation settings.
        - Assign reservations to a Contract Team user when confirming sales.
        - Replace the 'Sold' button with a 'Confirm Sales' button that:
          * Picks an available contract team user.
          * Assigns the reservation to that user.
          * Marks the contract team line as served.
          * Creates/opens the related sale (contract) as before.
          * Notifies the assigned user on the reservation.
    """,
    'author': "Temer",
    'category': 'Property',
    'depends': [
        'ahadubit_property_reservation',
        'property_contract',
        'temer_structure',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/contact_team_views.xml',
        'views/property_reservation_views_inherit.xml',
        'wizard/confirm_sales_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
    'post_init_hook': 'post_init_hook',
}

