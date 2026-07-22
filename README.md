# 🚀 WooCommerce Multi-Source Dropshipping Sync

A lightweight, automated Python engine for synchronizing multiple WooCommerce stores into a single destination store.

This project automates the entire dropshipping workflow: it fetches products from one or multiple source WooCommerce stores, builds parent-child category trees, calculates custom dynamic pricing, manages exact stock levels, and safely creates/updates products in your destination store — all with zero manual intervention.

---

## ✨ Features & What's New in v2.0

* 🌐 **Multi-Source Support** — Sync products from multiple supplier sites simultaneously without conflicts.
* ⚡ **Continuous Automation (Daemon & Cron)** — Run in the background every X hours or integrate with Linux Cron Jobs.
* 🛡️ **Product Isolation (SKU Prefixing)** — Automatically prefix SKUs (e.g., `shz-product-123`) to protect native store products.
* 📉 **Percentage Discount & Price Multipliers** — Preserve original discount ratios while applying custom margins.
* 📦 **Exact Inventory Sync & Out-of-Stock Tracking** — Sync real stock counts and mark missing source products as `outofstock`.
* 🗂️ **Dynamic Category Tree Preservation** — Rebuild full parent → child category hierarchies automatically.
* 🧠 **Smart Hash Caching** — Use SHA-256 hashing to skip unchanged products and reduce server load.
* 🗑️ **One-Click Cleanup Utility** — Batch delete products, categories, and caches with `cleanup.py`.
* 🔐 **Security First** — Keep credentials in `.env` and supplier configs in `sources.json`.

---

## 📂 Project Structure

```text
.
├── sync.py             # Main synchronization engine (Daemon / Single-run)
├── cleanup.py          # Fast batch deletion utility for reset/testing
├── sources.json        # Configuration file for all source WooCommerce stores
├── .env                # Secret keys, API credentials, and runtime settings
├── requirements.txt    # Python dependencies
├── sync_log.txt        # Automatic activity and error logs
└── hashes.json         # Smart cache tracking file (auto-generated)
```

---

## ⚙️ Workflow Architecture

```text
  ┌───────────────────────┐      ┌───────────────────────┐
  │  Source Store A (shz) │      │  Source Store B (exm) │
  └───────────┬───────────┘      └───────────┬───────────┘
              │                              │
              └──────────────┬───────────────┘
                             ▼
                     ┌───────────────┐
                     │    sync.py    │ ◄─── sources.json & .env
                     └───────┬───────┘
                             │
            ┌────────────────┴────────────────┐
            ▼                                 ▼
┌──────────────────────┐          ┌──────────────────────┐
│  Category Hierarchy  │          │ Price & Stock Engine │
│    Parent -> Child   │          │ Multipliers & Status │
└───────────┬───────────┘          └───────────┬───────────┘
            │                                 │
            └────────────────┬────────────────┘
                             ▼
            ┌─────────────────────────────────┐
            │ Destination WooCommerce Store   │
            │  (Updates & Creates Products)   │
            └─────────────────────────────────┘
```

---

## 📦 Installation

### Clone the repository

```bash
git clone https://github.com/yourusername/woocommerce-dropshipping-sync.git
cd woocommerce-dropshipping-sync
```

### Install dependencies

```bash
pip install -r requirements.txt
```

---

## 🔧 Configuration

### 1. Destination Credentials (`.env`)

Create a `.env` file in the project root:

```env
# Destination Website Credentials
DEST_BASE_URL=https://destination-domain.com/wp-json/wc/v3
DEST_CK=ck_your_consumer_key
DEST_CS=cs_your_consumer_secret

# Sync Interval Settings (in hours)
SYNC_INTERVAL_HOURS=4

# Set to True if using Linux Cron Job,
# or False for continuous background execution
RUN_ONCE=False
```

### 2. Multi-Source Suppliers (`sources.json`)

Create a `sources.json` file:

```json
[
  {
    "name": "Supplier One",
    "url": "https://supplier-one.com/wp-json/wc/store/v1/products",
    "source_id": "shz",
    "price_multiplier": 0.98
  },
  {
    "name": "Supplier Two",
    "url": "https://supplier-two.com/wp-json/wc/store/v1/products",
    "source_id": "sup2",
    "price_multiplier": 1.05
  }
]
```

---

## 🚀 Usage

### Run the Synchronizer

```bash
python sync.py
```

* `RUN_ONCE=False` → Runs continuously every `SYNC_INTERVAL_HOURS` hours.
* `RUN_ONCE=True` → Runs once and exits (ideal for Cron Jobs).

### Reset / Wipe Store Data (Optional)

```bash
python cleanup.py
```

Uses WooCommerce Batch REST API endpoints and asks for confirmation before deleting data.

---

## 📋 Logs

All activities are stored in `sync_log.txt` with timestamps:

```text
[2026-07-22 14:00:00] [INFO] ===== STARTING SYNC CYCLE =====
[2026-07-22 14:00:02] [INFO] --- Processing Source: Supplier One (ID: shz) ---
[2026-07-22 14:00:10] [CREATE] [shz] Creating product: shz-mascara-volume
[2026-07-22 14:00:15] [UPDATE] [shz] Updating product: shz-lipstick-red | ID: 1042
[2026-07-22 14:00:18] [OUTOFSTOCK] [shz] Marking Out of Stock: shz-old-item | ID: 980
[2026-07-22 14:00:20] [INFO] Source [Supplier One] Summary -> Created: 1, Updated: 1, Skipped: 340, Out-of-Stock: 1, Failed: 0
[2026-07-22 14:00:20] [INFO] ===== SYNC CYCLE COMPLETED =====
```

---

## 🧠 How It Works

The engine performs the following steps automatically:

<List gap={1}><List.Item>Load all supplier configurations from `sources.json`.</List.Item><List.Item>Fetch products from each source WooCommerce API.</List.Item><List.Item>Generate unique prefixed SKUs for isolation.</List.Item><List.Item>Rebuild category trees in the destination store.</List.Item><List.Item>Calculate final prices using multipliers while preserving discount percentages.</List.Item><List.Item>Compare product hashes against `hashes.json`.</List.Item><List.Item>Create new products, update changed products, and skip unchanged ones.</List.Item><List.Item>Mark deleted source products as `outofstock`.</List.Item><List.Item>Write detailed logs and persist the updated cache.</List.Item></List>

---

## 🔒 Security Notes

* Never commit `.env` to Git.
* Add both `.env` and `hashes.json` to `.gitignore`.
* Use WooCommerce API keys with the minimum required permissions.
* Keep supplier endpoints private if they expose inventory data.

Example `.gitignore`:

```gitignore
.env
hashes.json
sync_log.txt
__pycache__/
*.pyc
```

---

## 🆕 Changelog

### Version 2.0.0 — Major Architecture Update

* **Single-Script / Single-Process Architecture** — Removed intermediate files (`products.json`) and synchronized directly from source to destination.
* **Unlimited Multi-Source Support** — Added `sources.json` with per-source `source_id` and `price_multiplier`.
* **Daemon Mode & Cron Compatibility** — Added continuous background execution and one-shot Cron mode.
* **Smart Pricing Engine** — Applied multipliers to both `regular_price` and `sale_price` while preserving discount ratios.
* **Safe Inventory Management** — Added exact stock extraction and automatic `outofstock` handling for deleted source products.
* **Configuration-Based Security** — Moved all sensitive credentials to `.env`.
* **Fast Cleanup Utility** — Added `cleanup.py` with WooCommerce Batch Delete support for rapid testing resets.

---

## 🛠️ Requirements

* Python 3.10+
* WooCommerce REST API enabled
* Write access to the destination WooCommerce store

Main dependencies:

* `requests`
* `python-dotenv`
* `woocommerce`
* `urllib3`

---

## 📄 License

This project is released under the **MIT License**.

You are free to use, modify, and distribute this software for personal or commercial projects, provided that the original license notice is retained.

---

## ⭐ Support the Project

If this project helped you automate your WooCommerce dropshipping workflow:

* ⭐ Star the repository
* 🍴 Fork it for your own custom integrations
* 🐛 Open an issue for bugs or feature requests
* 🚀 Share improvements with the community

Built with **Python + WooCommerce REST API** for high-speed, low-maintenance dropshipping automation.
