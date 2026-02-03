# -*- coding: utf-8 -*-
{
    'name': 'Barcode Scanner - Inventory',
    'version': '18.0.1.0.1',
    'category': 'Inventory/Barcode',
    'summary': 'Barcode and QR code scanning for Stock Picking operations',
    'description': """
Barcode Scanner for Inventory Operations
========================================

This module extends Stock Pickings with barcode/QR scanning functionality:

* Scan products to add/update stock move lines
* Location barcode scanning (scan source/destination locations)
* Lot/serial barcode scanning with GS1-128 support
* Quantity increment on duplicate scans
* "Add new product in picking" toggle option
* Overage delivery handling
* Validate picking by scanning all products

Supports GS1-128 barcodes for:
- Product identification (GTIN)
- Lot/Batch numbers (AI 10)
- Serial numbers (AI 21)
- Expiry dates (AI 17)

Requires the Barcode Scanner Base module.
    """,
    'author': 'Woow Tech',
    'website': 'https://github.com/woowtech',
    'license': 'LGPL-3',
    'depends': [
        'barcode_scanner_base',
        'stock',
    ],
    'data': [
        'views/stock_picking_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'barcode_scanner_stock/static/src/components/**/*',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
