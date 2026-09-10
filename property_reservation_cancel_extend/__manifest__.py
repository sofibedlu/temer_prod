{
    "name": "Property Reservation Cancel Extend",
    "summary": "Cancels all reservations for a property and makes the property available.",
    "version": "17.0.1.0.0",
    "category": "Property  Management",
    "author": "Eyu Devo",
    "website": "https://yourcompany.com",
    "depends": ['ahadubit_property_reservation','advanced_property_management','temer_structure','ahadubit_property_base','contract_sections'],
    "data": [
        'security/reservation_cancel_access_group.xml',
        "views/property_reservation_cancel_view.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
