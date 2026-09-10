{
    'name': 'Collection Payment Order Validation',
    'version': '17.0.1.0.0',
    'category': 'Collection',
    'summary': 'Validates payment order - allows payment if previous has pending payments',
    'description': """
        Collection Payment Order Validation
        ===================================
        
        This module ensures that installments are paid in order.
        
        Key Features:
        - Validates that previous installments are paid before allowing payment
        - If previous installment has pending payments, validation PASSES (allows next payment)
        - Only blocks payment if previous installment has NO payments at all
        
        This ensures that pending payments don't block subsequent payments.
    """,
    'author': 'Temer Properties',
    'depends': [
        'collection_management',
    ],
    'data': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

