/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart, onMounted } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

/**
 * Stock Picking Barcode Scanner Action
 *
 * Full-screen client action for scanning barcodes during picking operations.
 * Supports product, location, and lot/serial scanning.
 */
export class StockBarcodeScannerAction extends Component {
    static template = "barcode_scanner_stock.ScannerAction";
    static props = {
        action: { type: Object, optional: true },
        actionId: { type: Number, optional: true },
        "*": true,
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.barcodeScanner = useService("barcodeScanner");
        this.actionService = useService("action");

        this.state = useState({
            pickingId: null,
            pickingName: "",
            pickingType: "",
            partnerName: "",
            state: "",
            isLoading: true,
            moveLines: [],
            scannedCount: 0,
            totalCount: 0,
            lastScanned: null,
            scanMode: "product", // product, location
        });

        onWillStart(async () => {
            await this.loadPickingInfo();
        });

        onMounted(() => {
            // Set up keyboard barcode listener
            this.setupBarcodeListener();
        });
    }

    async loadPickingInfo() {
        const context = this.props.action?.context || {};
        this.state.pickingId = context.active_id;

        if (this.state.pickingId) {
            const pickings = await this.orm.read(
                "stock.picking",
                [this.state.pickingId],
                ["name", "state", "partner_id", "picking_type_id", "move_line_ids"]
            );

            if (pickings.length > 0) {
                const picking = pickings[0];
                this.state.pickingName = picking.name;
                this.state.state = picking.state;
                this.state.partnerName = picking.partner_id ? picking.partner_id[1] : "";
                this.state.pickingType = picking.picking_type_id ? picking.picking_type_id[1] : "";

                // Load move lines
                await this.loadMoveLines();
            }
        }
        this.state.isLoading = false;
    }

    async loadMoveLines() {
        if (!this.state.pickingId) return;

        const moveLines = await this.orm.searchRead(
            "stock.move.line",
            [["picking_id", "=", this.state.pickingId]],
            ["product_id", "quantity", "product_uom_id", "lot_id", "location_id", "location_dest_id", "move_id"],
            { order: "id" }
        );

        // Get move quantities for comparison
        const moves = await this.orm.searchRead(
            "stock.move",
            [["picking_id", "=", this.state.pickingId]],
            ["product_id", "product_uom_qty", "quantity"],
            { order: "id" }
        );

        // Create a map of product to expected qty
        const productQtyMap = {};
        for (const move of moves) {
            const productId = move.product_id[0];
            if (!productQtyMap[productId]) {
                productQtyMap[productId] = { expected: 0, done: 0 };
            }
            productQtyMap[productId].expected += move.product_uom_qty;
            productQtyMap[productId].done += move.quantity || 0;
        }

        this.state.moveLines = moveLines.map(line => ({
            id: line.id,
            productId: line.product_id[0],
            productName: line.product_id[1],
            quantity: line.quantity,
            uom: line.product_uom_id ? line.product_uom_id[1] : "",
            lot: line.lot_id ? line.lot_id[1] : "",
            locationFrom: line.location_id ? line.location_id[1] : "",
            locationTo: line.location_dest_id ? line.location_dest_id[1] : "",
        }));

        // Calculate totals
        this.state.totalCount = Object.values(productQtyMap).reduce((sum, p) => sum + p.expected, 0);
        this.state.scannedCount = Object.values(productQtyMap).reduce((sum, p) => sum + p.done, 0);
    }

    setupBarcodeListener() {
        // Listen for keyboard barcode input (USB scanner)
        let barcodeBuffer = "";
        let barcodeTimeout;

        this.barcodeHandler = (event) => {
            // Only capture if not in an input field
            if (event.target.tagName === "INPUT" || event.target.tagName === "TEXTAREA") {
                return;
            }

            clearTimeout(barcodeTimeout);

            if (event.key === "Enter" && barcodeBuffer.length > 0) {
                this.handleBarcodeScan(barcodeBuffer);
                barcodeBuffer = "";
            } else if (event.key.length === 1) {
                barcodeBuffer += event.key;
                // Reset buffer after 100ms of no input
                barcodeTimeout = setTimeout(() => {
                    barcodeBuffer = "";
                }, 100);
            }
        };

        document.addEventListener("keydown", this.barcodeHandler);
    }

    willUnmount() {
        if (this.barcodeHandler) {
            document.removeEventListener("keydown", this.barcodeHandler);
        }
    }

    /**
     * Open the camera barcode scanner dialog
     */
    async openCameraScanner() {
        this.barcodeScanner.openScanner({
            onScan: (result) => {
                this.handleBarcodeScan(result.barcode);
            },
            title: _t("Scan Product or Location"),
        });
    }

    /**
     * Handle a scanned barcode
     */
    async handleBarcodeScan(barcode) {
        if (!this.state.pickingId || !barcode) return;

        this.state.lastScanned = barcode;

        try {
            const result = await this.orm.call(
                "stock.picking",
                "process_barcode_scan",
                [this.state.pickingId, barcode]
            );

            if (result.success) {
                this.barcodeScanner.showSuccess(result.success.message);
                // Reload move lines to show updated quantities
                await this.loadMoveLines();
            } else if (result.warning) {
                this.barcodeScanner.showWarning(result.warning.message);
            } else if (result.error) {
                this.barcodeScanner.showError(result.error);
            }
        } catch (error) {
            console.error("Error processing barcode:", error);
            this.barcodeScanner.showError(_t("Error processing barcode"));
        }
    }

    /**
     * Toggle scan mode between product and location
     */
    toggleScanMode() {
        this.state.scanMode = this.state.scanMode === "product" ? "location" : "product";
        this.notification.add(
            _t("Scan mode: %s", this.state.scanMode === "product" ? "Products" : "Locations"),
            { type: "info" }
        );
    }

    /**
     * Validate the picking
     */
    async validatePicking() {
        try {
            await this.orm.call("stock.picking", "button_validate", [[this.state.pickingId]]);
            this.notification.add(_t("Picking validated successfully"), { type: "success" });
            this.close();
        } catch (error) {
            console.error("Error validating picking:", error);
            this.notification.add(_t("Error validating picking: %s", error.message), {
                type: "danger",
            });
        }
    }

    /**
     * Get progress percentage
     */
    get progressPercent() {
        if (this.state.totalCount === 0) return 0;
        return Math.round((this.state.scannedCount / this.state.totalCount) * 100);
    }

    /**
     * Check if picking can be validated
     */
    get canValidate() {
        // Can validate if picking is not done/cancelled and has scanned items
        const validStates = ["assigned", "confirmed", "waiting"];
        const result = validStates.includes(this.state.state) && this.state.scannedCount > 0;
        console.log("[canValidate] state:", this.state.state, "scannedCount:", this.state.scannedCount, "result:", result);
        return result;
    }

    /**
     * Close the scanner and return to the picking
     */
    close() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "stock.picking",
            res_id: this.state.pickingId,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

StockBarcodeScannerAction.template = "barcode_scanner_stock.ScannerAction";

// Register the client action
registry.category("actions").add("barcode_scanner_stock.scan_action", StockBarcodeScannerAction);
