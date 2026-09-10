{
    "name": "Collection ↔ Construction Progress Integration",
    "version": "17.0.1.0.0",
    "author": "Sofonias B/TemerProperties",
    "summary": "Adds workflow on construction progress and sets due dates for progress-based installments.",
    "depends": [
        "base",
        "mail",
        "temer_payment_modify",
        "collection_management",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/progress_views.xml",
        "views/collection_installment_views.xml",
        "views/shift_config_views.xml",
        "views/progress_readonly_menu.xml",
    ],
    'assets': {
        'web.assets_backend':[
            'collection_progress_integration/static/src/js/smooth_slider.js',
            'collection_progress_integration/static/src/xml/smooth_slider.xml',
        ],
    },
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}