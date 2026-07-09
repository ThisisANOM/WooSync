# 🚀 WooCommerce Dropshipping Sync

A lightweight Python toolkit for synchronizing WooCommerce stores.

This project automates the entire dropshipping workflow by exporting products from a source WooCommerce store, migrating product categories, and importing/updating products into a destination store.

Perfect for building dropshipping websites that mirror another WooCommerce store while keeping products synchronized.

---

## ✨ Features

- 📦 Export products from WooCommerce Store API
- 🗂 Export & import product categories
- 🔄 Automatically create missing categories
- 📁 Preserve category hierarchy (Parent/Child)
- 🚀 Create new products automatically
- 🔄 Update existing products by SKU
- 🖼 Import product images
- 💲 Modify prices during export
- 📜 Detailed synchronization logs
- ⚡ Automatic retry on failed requests
- 🛒 Works with WooCommerce REST API
- 🐍 Pure Python implementation

---

## 📂 Project Structure

```
.
├── export.py          # Export products from source store
├── categories.py      # Sync product categories
├── import.py          # Import & update products
├── requirements.txt
└── products.json      # Generated product database
```

---

## ⚙️ Workflow

```text
Source Store
      │
      ▼
 export.py
      │
      ▼
 products.json
      │
      ├──────────────► categories.py
      │                    │
      │                    ▼
      │          Destination Categories
      │
      ▼
 import.py
      │
      ▼
Destination WooCommerce Store
```

---

## 📦 Installation

Clone the repository

```bash
git clone https://github.com/yourusername/woocommerce-dropshipping-sync.git

cd woocommerce-dropshipping-sync
```

Install dependencies

```bash
pip install -r requirements.txt
```

---

## 🔧 Configuration

Replace the placeholders inside the scripts with your own information.

Source Store

```python
BASE_URL = "https://source-domain.com/wp-json/wc/store/v1/products"
```

Destination Store

```python
BASE_WP = "https://destination-domain.com/wp-json/wc/v3"
```

WooCommerce Authentication

```python
CK = "YOUR_APPLICATION_USERNAME"
CS = "YOUR_APPLICATION_PASSWORD"
```

---

## 🚀 Usage

### 1. Export Products

```bash
python export.py
```

Generates

```
products.json
```

---

### 2. Sync Categories

```bash
python categories.py
```

Creates missing categories while preserving parent-child relationships.

---

### 3. Import Products

```bash
python import.py
```

The importer will automatically:

- Create new products
- Update existing products
- Create missing categories
- Upload images
- Keep products synchronized

---

## 🔄 Synchronization Logic

Products are identified using their **SKU**.

If a product already exists:

```
Update Product
```

Otherwise:

```
Create Product
```

This prevents duplicate products and allows continuous synchronization.

---

## 💰 Price Customization

Prices can easily be modified during export.

Example:

```python
discounted_price = int(base_price * 0.98)
```

You can replace this with your own pricing strategy such as:

- Fixed markup
- Percentage profit
- Currency conversion
- Dynamic pricing

---

## 📋 Logs

The importer generates a log file:

```
sync_log.txt
```

Example

```
[INFO] Loaded 350 products
[CREATE] iphone-15
[UPDATE] samsung-s24
[ERROR] Request timeout
===== SUMMARY =====
Created: 120
Updated: 230
Failed: 2
```

---

## 🛠 Requirements

- Python 3.10+
- WooCommerce
- WordPress REST API
- WooCommerce REST API

Libraries

- requests
- pandas
- openpyxl

---

## 📌 Future Improvements

- [ ] Multi-threaded import
- [ ] Product variations
- [ ] Attribute synchronization
- [ ] Stock synchronization
- [ ] Scheduled synchronization
- [ ] CLI arguments
- [ ] Docker support
- [ ] Progress bar
- [ ] Image deduplication
- [ ] Incremental sync

---

## 🤝 Contributing

Contributions are welcome.

Feel free to open an Issue or submit a Pull Request.

---

## 📄 License

This project is released under the MIT License.

---

⭐ If you find this project useful, consider giving it a star on GitHub!
