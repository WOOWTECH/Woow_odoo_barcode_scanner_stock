# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    barcode_stock_allow_new_products = fields.Boolean(
        string='Allow Adding New Products',
        default=False,
        config_parameter='barcode_scanner_stock.allow_new_products',
        help="Allow adding products to pickings that are not in the expected moves"
    )

    barcode_stock_allow_overage = fields.Boolean(
        string='Allow Overage Delivery',
        default=False,
        config_parameter='barcode_scanner_stock.allow_overage',
        help="Allow scanning more quantity than expected in the picking"
    )

    barcode_stock_auto_validate = fields.Boolean(
        string='Auto-Validate When Complete',
        default=False,
        config_parameter='barcode_scanner_stock.auto_validate',
        help="Automatically validate the picking when all products are scanned"
    )

    barcode_stock_require_location = fields.Boolean(
        string='Require Location Scan',
        default=False,
        config_parameter='barcode_scanner_stock.require_location',
        help="Require scanning a location before scanning products"
    )
