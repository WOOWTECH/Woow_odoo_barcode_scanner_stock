# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class StockPicking(models.Model):
    _name = 'stock.picking'
    _inherit = ['stock.picking', 'barcodes.barcode_events_mixin']

    # Scanner mode for this picking
    scanner_mode = fields.Selection(
        selection=[
            ('product', 'Scan Products'),
            ('location', 'Scan Location'),
        ],
        string='Scanner Mode',
        default='product',
        help="Current scanning mode: product or location"
    )
    scanner_location_id = fields.Many2one(
        comodel_name='stock.location',
        string='Scanned Location',
        help="Last scanned location (for source or destination)"
    )

    def on_barcode_scanned(self, barcode):
        """Handle barcode scan on stock picking.

        This method handles:
        - Product barcodes (add/update move lines)
        - Location barcodes (set source/destination location)
        - Lot/serial barcodes (with GS1-128 support)

        Args:
            barcode: The scanned barcode string

        Returns:
            dict: Action or notification to display
        """
        self.ensure_one()

        # Check picking state
        if self.state == 'done':
            return {
                'warning': {
                    'title': _('Picking Done'),
                    'message': _('Cannot modify a completed picking.'),
                }
            }

        if self.state == 'cancel':
            return {
                'warning': {
                    'title': _('Picking Cancelled'),
                    'message': _('Cannot modify a cancelled picking.'),
                }
            }

        # Parse barcode - check if it's a GS1 barcode first
        gs1_parser = self.env['barcode.gs1.parser']
        gs1_data = gs1_parser.parse(barcode)

        # Check if this is a location barcode
        location = self._find_location_by_barcode(barcode)
        if location:
            return self._handle_location_scan(location)

        # Check if this is a lot/serial scan (from GS1 or direct)
        if gs1_data.get('lot') or gs1_data.get('serial'):
            return self._handle_lot_serial_scan(barcode, gs1_data)

        # Standard product scan
        return self._handle_product_scan(barcode, gs1_data)

    def _find_location_by_barcode(self, barcode):
        """Find a stock location by its barcode.

        Args:
            barcode: The barcode string

        Returns:
            stock.location recordset or False
        """
        return self.env['stock.location'].search([
            ('barcode', '=', barcode),
            '|',
            ('company_id', '=', False),
            ('company_id', '=', self.company_id.id),
        ], limit=1)

    def _handle_location_scan(self, location):
        """Handle a scanned location barcode.

        Args:
            location: stock.location record

        Returns:
            dict: Notification
        """
        self.scanner_location_id = location.id

        # Determine if this is source or destination based on picking type
        location_type = 'Source' if self.picking_type_id.code == 'outgoing' else 'Destination'

        return {
            'success': {
                'title': _('Location Scanned'),
                'message': _('%s location set to: %s') % (location_type, location.display_name),
            }
        }

    def _handle_product_scan(self, barcode, gs1_data=None):
        """Handle a scanned product barcode.

        Args:
            barcode: The barcode string
            gs1_data: Parsed GS1 data dict (optional)

        Returns:
            dict: Notification
        """
        # Find product by barcode (use GTIN from GS1 if available)
        search_barcode = gs1_data.get('gtin') or barcode if gs1_data else barcode
        product_info = self.env['product.product'].find_by_barcode_with_info(
            search_barcode,
            self.company_id.id
        )

        if not product_info.get('product'):
            # Check if we should allow adding new products
            allow_new = self.env['ir.config_parameter'].sudo().get_param(
                'barcode_scanner_stock.allow_new_products', 'False'
            ) == 'True'

            if not allow_new:
                return {
                    'warning': {
                        'title': _('Product Not Found'),
                        'message': _('No product found for barcode: %s. Enable "Add new products" to allow adding products not in the picking.') % barcode,
                    }
                }
            else:
                return {
                    'warning': {
                        'title': _('Product Not Found'),
                        'message': product_info.get('error', _('No product found for barcode: %s') % barcode),
                    }
                }

        # product_info['product'] is a dict from _serialize_for_js(), get the actual recordset
        product_data = product_info['product']
        product = self.env['product.product'].browse(product_data['id'])

        # Find or create move line
        move_line = self._find_or_create_move_line(product, gs1_data)

        if isinstance(move_line, dict):
            # This is an error/warning response
            return move_line

        # Increment quantity
        auto_increment = self.env['ir.config_parameter'].sudo().get_param(
            'barcode_scanner.auto_increment', 'True'
        ) == 'True'

        if auto_increment:
            move_line.quantity += 1
        else:
            move_line.quantity = 1

        return self._get_scan_success_notification(product, move_line, gs1_data)

    def _find_or_create_move_line(self, product, gs1_data=None):
        """Find an existing move line for the product or create one.

        Args:
            product: product.product record
            gs1_data: Parsed GS1 data dict (optional)

        Returns:
            stock.move.line record or dict (error response)
        """
        self.ensure_one()

        # First, look for an existing move for this product
        move = self.move_ids.filtered(
            lambda m: m.product_id.id == product.id and m.state not in ('done', 'cancel')
        )

        if not move:
            # Check if we're allowed to add new products
            allow_new = self.env['ir.config_parameter'].sudo().get_param(
                'barcode_scanner_stock.allow_new_products', 'False'
            ) == 'True'

            if not allow_new:
                return {
                    'warning': {
                        'title': _('Product Not in Picking'),
                        'message': _('Product "%s" is not expected in this picking. Enable "Add new products" to allow adding it.') % product.display_name,
                    }
                }

            # Create a new move
            move = self.env['stock.move'].create({
                'name': product.display_name,
                'product_id': product.id,
                'product_uom_qty': 1,
                'product_uom': product.uom_id.id,
                'picking_id': self.id,
                'location_id': self.location_id.id,
                'location_dest_id': self.location_dest_id.id,
            })

        move = move[0] if len(move) > 1 else move

        # Look for existing move line (consider lot/serial if GS1 data present)
        lot_id = False
        if gs1_data and (gs1_data.get('lot') or gs1_data.get('serial')):
            lot_name = gs1_data.get('serial') or gs1_data.get('lot')
            lot = self.env['stock.lot'].search([
                ('name', '=', lot_name),
                ('product_id', '=', product.id),
                '|',
                ('company_id', '=', False),
                ('company_id', '=', self.company_id.id),
            ], limit=1)

            if lot:
                lot_id = lot.id

            # Look for move line with this lot
            move_line = move.move_line_ids.filtered(
                lambda ml: ml.lot_id.id == lot_id if lot_id else not ml.lot_id
            )
        else:
            # Look for move line without lot
            move_line = move.move_line_ids.filtered(lambda ml: not ml.lot_id)

        if move_line:
            return move_line[0]

        # Create new move line
        # Note: picking_id is computed from move_id.picking_id, so we don't set it explicitly
        line_vals = {
            'move_id': move.id,
            'product_id': product.id,
            'product_uom_id': product.uom_id.id,
            'location_id': self.scanner_location_id.id or move.location_id.id,
            'location_dest_id': move.location_dest_id.id,
            'quantity': 0,  # Will be incremented
        }

        if lot_id:
            line_vals['lot_id'] = lot_id

        return self.env['stock.move.line'].create(line_vals)

    def _handle_lot_serial_scan(self, barcode, gs1_data):
        """Handle a scanned lot or serial number.

        Args:
            barcode: The original barcode string
            gs1_data: Parsed GS1 data dict

        Returns:
            dict: Notification
        """
        lot_name = gs1_data.get('serial') or gs1_data.get('lot')
        is_serial = bool(gs1_data.get('serial'))

        # If we have GTIN, find the product
        if gs1_data.get('gtin'):
            return self._handle_product_scan(barcode, gs1_data)

        # Otherwise, try to find an existing lot with this name
        lot = self.env['stock.lot'].search([
            ('name', '=', lot_name),
            '|',
            ('company_id', '=', False),
            ('company_id', '=', self.company_id.id),
        ], limit=1)

        if lot:
            # We found an existing lot, use its product
            gs1_data['_lot_record'] = lot
            product_info = {'product': lot.product_id.id}
            product = lot.product_id
            move_line = self._find_or_create_move_line(product, gs1_data)

            if isinstance(move_line, dict):
                return move_line

            # Set the lot on the move line
            move_line.lot_id = lot.id

            if is_serial:
                move_line.quantity = 1  # Serial numbers always qty=1
            else:
                move_line.quantity += 1

            return {
                'success': {
                    'title': _('Lot/Serial Scanned'),
                    'message': _('%s: %s | Product: %s') % (
                        _('Serial') if is_serial else _('Lot'),
                        lot_name,
                        product.display_name
                    ),
                }
            }
        else:
            return {
                'warning': {
                    'title': _('Lot/Serial Not Found'),
                    'message': _('No existing lot/serial found with name: %s. Scan the product barcode first.') % lot_name,
                }
            }

    def _get_scan_success_notification(self, product, move_line, gs1_data=None):
        """Generate success notification for scanned product.

        Args:
            product: product.product record
            move_line: stock.move.line record
            gs1_data: Parsed GS1 data dict (optional)

        Returns:
            dict: Notification data
        """
        message_parts = []

        # Quantity info
        message_parts.append(_('Qty: %s / %s') % (
            move_line.quantity,
            move_line.move_id.product_uom_qty
        ))

        # Location info
        if self.scanner_location_id:
            message_parts.append(_('Location: %s') % self.scanner_location_id.name)

        # Lot/serial info
        if move_line.lot_id:
            message_parts.append(_('Lot: %s') % move_line.lot_id.name)

        # GS1 extra info
        if gs1_data:
            if gs1_data.get('expiry'):
                message_parts.append(_('Expiry: %s') % gs1_data['expiry'].strftime('%Y-%m-%d'))

        return {
            'success': {
                'title': product.display_name,
                'message': ' | '.join(message_parts),
            }
        }

    def action_open_barcode_scanner(self):
        """Open the barcode scanner dialog.

        This action is triggered from the button in the form view.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'barcode_scanner_stock.scan_action',
            'target': 'fullscreen',
            'context': {
                'active_model': 'stock.picking',
                'active_id': self.id,
            },
        }

    @api.model
    def process_barcode_scan(self, picking_id, barcode):
        """Process a barcode scan for a picking.

        This method can be called directly from JavaScript.

        Args:
            picking_id: int, the picking ID
            barcode: str, the scanned barcode

        Returns:
            dict: Result with notification data or error
        """
        picking = self.browse(picking_id)
        if not picking.exists():
            return {'error': _('Picking not found')}

        return picking.on_barcode_scanned(barcode)


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    @api.model
    def update_from_barcode(self, picking_id, barcode):
        """Update a move line from a barcode scan.

        Args:
            picking_id: int, the picking ID
            barcode: str, the scanned barcode

        Returns:
            dict: Result with line data or error
        """
        picking = self.env['stock.picking'].browse(picking_id)
        if not picking.exists():
            return {'error': _('Picking not found')}

        return picking.on_barcode_scanned(barcode)
