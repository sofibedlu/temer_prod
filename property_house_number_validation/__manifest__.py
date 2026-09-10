{
    'name': 'Property House Number Validation',
    'version': '1.0',
    'category': 'Real Estate',
    'summary': 'Validate unique house numbers within same floor',
    'description': """
        Validates that house numbers are unique within the same floor.
        Uses existing house number field.
    """,
    'author': 'Your Company',
    'depends': [
        'advanced_property_management',
        'advanced_property_unit_naming',
        'ahadubit_property_base_custom',
    ],
    'data': [
        # No views needed - just using existing fields
    ],
    'installable': True,
    'application': False,
}