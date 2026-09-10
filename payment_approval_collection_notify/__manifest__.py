{
    "name": "Payment Approval - Notify Initiator",
    "version": "17.0.1.0.0",
    "summary": "Notify collection initiator on approval/denial and post status on collection order.",
    "author": "Sofonias B/Temer Properties",
    "license": "LGPL-3",
    "depends": [
        "mail",
        "collection_management",
        "payment_approval_new",
    ],
    "data": [
        "views/payment_approval_record_views.xml",
    ],
    "installable": True,
    "application": False,
}