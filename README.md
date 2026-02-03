# Barcode Scanner - Stock

Full-featured barcode scanning for Stock Picking operations in Odoo 18.

---

# 條碼掃描 - 庫存模組

Odoo 18 庫存調撥作業全功能條碼掃描模組。

---

## Features / 功能特色

### English

- **Product Scanning**: Scan products to confirm receipt/delivery quantities
- **Location Scanning**: Scan location barcodes to set source/destination
- **Lot/Serial Support**: Scan GS1 barcodes with lot and serial information
- **Full-screen Scanner**: Dedicated scanning interface for warehouse operations
- **Progress Tracking**: Visual progress bar showing scanned vs expected quantities
- **USB Scanner Support**: Works with keyboard-emulating USB barcode scanners
- **Validate from Scanner**: Complete picking without leaving scanner view

### 繁體中文

- **產品掃描**：掃描產品以確認收貨/出貨數量
- **儲位掃描**：掃描儲位條碼以設定來源/目的地
- **批號/序號支援**：掃描包含批號與序號資訊的 GS1 條碼
- **全螢幕掃描器**：倉庫作業專用掃描介面
- **進度追蹤**：視覺化進度條顯示已掃描與預期數量對比
- **USB 掃描器支援**：支援鍵盤模擬的 USB 條碼掃描器
- **掃描器內驗證**：無需離開掃描畫面即可完成調撥

---

## Dependencies / 相依性

- `barcode_scanner_base`
- `stock`

---

## Installation / 安裝

### English

1. Install `barcode_scanner_base` first
2. Install this module from Apps menu
3. The scanner button will appear on Stock Picking forms

### 繁體中文

1. 先安裝 `barcode_scanner_base`
2. 從應用程式選單安裝此模組
3. 掃描器按鈕將出現在庫存調撥表單上

---

## Configuration / 設定

### Additional Settings / 額外設定

Go to **Settings > General Settings > Inventory**:

| Setting | Description | 說明 |
|---------|-------------|------|
| Allow New Products | Add products not in picking | 允許新增不在調撥單的產品 |

---

## Usage / 使用方式

### Basic Scanning Workflow / 基本掃描流程

**English:**

1. Open a Stock Picking (Delivery Order, Receipt, Internal Transfer)
2. Click **Open Scanner** button (opens full-screen mode)
3. **Scan Products**: Point camera at product barcodes
4. **Scan Locations** (optional): Scan source/destination location barcodes
5. **Scan Lots** (if required): For tracked products, scan lot/serial numbers
6. Monitor progress bar at top of screen
7. Click **Validate** when all items are scanned
8. Click **Close** to return to picking form

**繁體中文：**

1. 開啟庫存調撥單（出貨單、收貨單、內部調撥）
2. 點擊 **開啟掃描器** 按鈕（開啟全螢幕模式）
3. **掃描產品**：將相機對準產品條碼
4. **掃描儲位**（選擇性）：掃描來源/目的地儲位條碼
5. **掃描批號**（如需要）：針對追蹤產品，掃描批號/序號
6. 在畫面頂部監控進度條
7. 所有項目掃描完成後點擊 **驗證**
8. 點擊 **關閉** 返回調撥表單

### Scanning Modes / 掃描模式

| Mode | Description | 說明 |
|------|-------------|------|
| Product | Scan products to update quantities | 掃描產品以更新數量 |
| Location | Scan locations to set source/dest | 掃描儲位以設定來源/目的地 |

Toggle mode by clicking the mode button. / 點擊模式按鈕切換模式。

---

## Barcode Types / 條碼類型

### Product Barcodes / 產品條碼

Standard product barcodes (EAN-13, UPC-A, etc.) will:
- Find the product in the picking
- Increment quantity by 1
- Show success notification with qty progress

標準產品條碼（EAN-13、UPC-A 等）會：
- 在調撥單中找到產品
- 數量增加 1
- 顯示成功通知及數量進度

### Location Barcodes / 儲位條碼

Location barcodes will:
- Set as source (for outgoing) or destination (for incoming)
- Show confirmation message

儲位條碼會：
- 設定為來源（出庫）或目的地（入庫）
- 顯示確認訊息

### GS1-128 Barcodes / GS1-128 條碼

GS1-128 barcodes with lot/serial info will:
- Find product by GTIN
- Set lot/serial on move line
- Set expiry date if available
- For serials, quantity is always 1

包含批號/序號資訊的 GS1-128 條碼會：
- 以 GTIN 查找產品
- 在移動明細設定批號/序號
- 如有則設定有效期限
- 序號的數量恆為 1

---

## Notifications / 通知訊息

| Type | Message | 說明 |
|------|---------|------|
| Success | "Qty: X / Y" | 數量：X / Y |
| Success | "Location: [name]" | 儲位：[名稱] |
| Success | "Lot: [name]" | 批號：[名稱] |
| Warning | "Product Not Found" | 找不到產品 |
| Warning | "Product Not in Picking" | 產品不在調撥單中 |
| Warning | "Picking Done" | 調撥已完成 |
| Warning | "Picking Cancelled" | 調撥已取消 |

---

## API Reference / API 參考

### stock.picking

| Method | Description | 說明 |
|--------|-------------|------|
| `on_barcode_scanned(barcode)` | Handle barcode scan | 處理條碼掃描 |
| `process_barcode_scan(picking_id, barcode)` | Static method for JS | 供 JS 呼叫的靜態方法 |
| `action_open_barcode_scanner()` | Open full-screen scanner | 開啟全螢幕掃描器 |

### stock.move.line

| Method | Description | 說明 |
|--------|-------------|------|
| `update_from_barcode(picking_id, barcode)` | Update line from scan | 從掃描更新明細 |

---

## Workflow Diagram / 工作流程圖

```
┌──────────────────────────────────────────────────┐
│                 STOCK PICKING                     │
└──────────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────┐
│              OPEN SCANNER (Full-screen)           │
└──────────────────────────────────────────────────┘
                       │
         ┌─────────────┴─────────────┐
         ▼                           ▼
┌─────────────────┐         ┌─────────────────┐
│  Scan Location  │         │  Scan Product   │
│  (optional)     │         │                 │
└────────┬────────┘         └────────┬────────┘
         │                           │
         ▼                           ▼
┌─────────────────┐         ┌─────────────────┐
│ Location Set    │         │ Qty Incremented │
└─────────────────┘         └────────┬────────┘
                                     │
                            ┌────────┴────────┐
                            ▼                 │
                   ┌─────────────────┐        │
                   │ Scan Lot/Serial │        │
                   │ (if tracked)    │        │
                   └────────┬────────┘        │
                            │                 │
                            ▼                 │
                   ┌─────────────────┐        │
                   │ Lot Assigned    │────────┘
                   └────────┬────────┘  (repeat)
                            │
                            ▼
              ┌──────────────────────┐
              │ Progress: 100%       │
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │ Click VALIDATE       │
              └──────────────────────┘
```

---

## Troubleshooting / 疑難排解

### "Product Not in Picking" / 「產品不在調撥單中」

**English:** Enable "Allow New Products" in settings to add products not originally in the picking.

**繁體中文：** 在設定中啟用「允許新增產品」以新增原本不在調撥單中的產品。

### USB Scanner not working / USB 掃描器無法運作

**English:**
- Ensure the scanner is in keyboard emulation mode
- Click inside the scanner interface to focus
- Scanner should be configured to add Enter after scan

**繁體中文：**
- 確認掃描器處於鍵盤模擬模式
- 點擊掃描器介面以取得焦點
- 掃描器應設定為掃描後加入 Enter 鍵

---

## License / 授權

LGPL-3.0

---

**Author / 作者:** Woow Tech

**Version / 版本:** 18.0.1.0.0
