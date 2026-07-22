import os
import re
import json
import time
import hashlib
from datetime import datetime
from urllib.parse import unquote
import requests
from dotenv import load_dotenv

# ---------------- LOAD ENVIRONMENT VARIABLES ----------------
load_dotenv()

DEST_BASE_URL = os.getenv("DEST_BASE_URL")
DEST_CK = os.getenv("DEST_CK")
DEST_CS = os.getenv("DEST_CS")
SYNC_INTERVAL_HOURS = float(os.getenv("SYNC_INTERVAL_HOURS", "4"))
RUN_ONCE = os.getenv("RUN_ONCE", "False").lower() in ["true", "1", "yes"]

DEST_AUTH = (DEST_CK, DEST_CS)
LOG_FILE = "sync_log.txt"
HASH_FILE = "hashes.json"
SOURCES_FILE = "sources.json"


# ---------------- LOGGING UTILITY ----------------
def log(level, msg):
    """Logs messages to console and log file with timestamp."""
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{level}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ---------------- HTTP REQUEST HELPER ----------------
def request(method, url, **kwargs):
    """Executes HTTP request with retry logic for network resilience."""
    for attempt in range(3):
        try:
            r = requests.request(method, url, timeout=30, **kwargs)
            if r.status_code in [200, 201]:
                return r
            log("ERROR", f"HTTP {r.status_code} on {url} -> {r.text[:200]}")
        except Exception as e:
            log("ERROR", f"Request Exception on {url}: {e}")
        time.sleep(1 + attempt)
    return None


# ---------------- HASH MANAGEMENT ----------------
def load_hashes():
    """Loads previously stored payload hashes."""
    try:
        with open(HASH_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_hashes(hashes):
    """Saves updated payload hashes to file."""
    with open(HASH_FILE, "w", encoding="utf-8") as f:
        json.dump(hashes, f, ensure_ascii=False, indent=2)


def make_hash(payload):
    """Generates SHA256 hash for payload (excluding images to avoid duplicate updates)."""
    data = payload.copy()
    data.pop("images", None)
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


# ---------------- CATEGORY MANAGEMENT ----------------
def get_dest_categories():
    """Fetches all existing product categories from the destination site."""
    r = request("GET", f"{DEST_BASE_URL}/products/categories", auth=DEST_AUTH, params={"per_page": 100})
    if not r:
        return {}
    
    cats = r.json()
    # Mapping structure: (category_name_lower, parent_id) -> category_id
    cat_map = {}
    for c in cats:
        cat_map[(c["name"].strip().lower(), c["parent"])] = c["id"]
    return cat_map


def get_or_create_dest_category_chain(cat_path_names, dest_cat_map):
    """
    Recursively finds or creates category hierarchy (Parent -> Child).
    Example input: ['Eye Makeup', 'Mascara']
    """
    parent_id = 0
    for name in cat_path_names:
        clean_name = name.strip()
        key = (clean_name.lower(), parent_id)
        
        if key in dest_cat_map:
            parent_id = dest_cat_map[key]
        else:
            payload = {"name": clean_name, "parent": parent_id}
            r = request("POST", f"{DEST_BASE_URL}/products/categories", json=payload, auth=DEST_AUTH)
            if r:
                new_cat = r.json()
                cid = new_cat["id"]
                dest_cat_map[key] = cid
                parent_id = cid
                log("INFO", f"Created Category: '{clean_name}' (ID: {cid}, Parent: {payload['parent']})")
            else:
                log("ERROR", f"Failed to create category '{clean_name}'")
                return None
    return parent_id


# ---------------- SOURCE DATA PARSING ----------------
def extract_stock_quantity(p):
    """Extracts stock quantity from source product payload."""
    add_to_cart = p.get("add_to_cart", {})
    if "maximum" in add_to_cart and add_to_cart["maximum"] is not None:
        return int(add_to_cart["maximum"])
    
    stock_text = p.get("stock_availability", {}).get("text", "")
    match = re.search(r'(\d+)', stock_text)
    if match:
        return int(match.group(1))
    
    return 1 if p.get("is_in_stock") else 0


def parse_category_path(link_url):
    """Extracts category path hierarchy from source category URL."""
    if not link_url:
        return []
    match = re.search(r'/product-category/(.+?)/?$', link_url)
    if not match:
        return []
    path_str = match.group(1).strip('/')
    slugs = path_str.split('/')
    
    names = []
    for s in slugs:
        decoded = unquote(s).replace('-', ' ')
        names.append(decoded.title())
    return names


def fetch_source_products(source_config):
    """Fetches and normalizes all products from a single source site."""
    url = source_config["url"]
    source_id = source_config["source_id"].strip().lower()
    price_multiplier = float(source_config.get("price_multiplier", 1.0))
    
    page = 1
    source_products = []
    log("INFO", f"Fetching products from Source: {source_config['name']} ({url})")

    while True:
        params = {"page": page, "per_page": 100}
        r = request("GET", url, params=params, headers={"User-Agent": "Mozilla/5.0"})
        if not r:
            break
        data = r.json()
        if not data:
            break

        for p in data:
            raw_sku = p.get("sku") or str(p.get("id"))
            clean_raw_sku = re.sub(r"[^a-z0-9\-]", "-", raw_sku.lower()).strip("-")
            final_sku = f"{source_id}-{clean_raw_sku}"

            # Calculate prices using multiplier
            prices = p.get("prices", {})
            try:
                reg_price = int(prices.get("regular_price") or prices.get("price") or 0)
            except ValueError:
                reg_price = 0

            try:
                sale_price = int(prices.get("sale_price") or 0)
            except ValueError:
                sale_price = 0

            new_regular_price = int(reg_price * price_multiplier) if reg_price > 0 else 0
            new_sale_price = int(sale_price * price_multiplier) if sale_price > 0 else 0

            stock_qty = extract_stock_quantity(p)
            is_in_stock = p.get("is_in_stock", False) and (stock_qty > 0)

            # Extract Category Chains
            cat_paths = []
            for c in p.get("categories", []):
                path = parse_category_path(c.get("link", ""))
                if path:
                    cat_paths.append(path)
                elif c.get("name"):
                    cat_paths.append([c["name"]])

            parsed_product = {
                "name": p.get("name", ""),
                "sku": final_sku,
                "regular_price": str(new_regular_price) if new_regular_price > 0 else "",
                "sale_price": str(new_sale_price) if (0 < new_sale_price < new_regular_price) else "",
                "description": p.get("description", ""),
                "short_description": p.get("short_description", ""),
                "manage_stock": True,
                "stock_quantity": stock_qty,
                "stock_status": "instock" if is_in_stock else "outofstock",
                "images": [{"src": img["src"]} for img in p.get("images", []) if img.get("src")],
                "cat_paths": cat_paths
            }
            source_products.append(parsed_product)

        page += 1
        time.sleep(0.2)

    log("INFO", f"Total products fetched from {source_config['name']}: {len(source_products)}")
    return source_products


# ---------------- DESTINATION DATA FETCHING ----------------
def fetch_dest_existing():
    """Fetches all existing products from the destination WooCommerce site."""
    existing = {}
    page = 1
    log("INFO", "Fetching existing products from Destination site...")

    while True:
        r = request("GET", f"{DEST_BASE_URL}/products", auth=DEST_AUTH, params={"per_page": 100, "page": page})
        if not r:
            break
        data = r.json()
        if not data:
            break

        for p in data:
            sku = p.get("sku", "")
            if sku:
                existing[sku] = p

        page += 1

    log("INFO", f"Total products existing on Destination: {len(existing)}")
    return existing


# ---------------- CORE SYNC ENGINE ----------------
def sync_sources():
    """Main processing logic for all source sites."""
    log("INFO", "===== STARTING SYNC CYCLE =====")

    # Load configuration & hashes
    if not os.path.exists(SOURCES_FILE):
        log("ERROR", f"Config file '{SOURCES_FILE}' not found! Aborting sync.")
        return

    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        sources = json.load(f)

    hashes = load_hashes()
    dest_cat_map = get_dest_categories()
    dest_existing = fetch_dest_existing()

    # Process each source independently
    for source in sources:
        source_name = source.get("name", "Unknown Source")
        source_id = source.get("source_id", "").strip().lower()
        
        if not source_id:
            log("ERROR", f"Missing 'source_id' for {source_name}. Skipping...")
            continue

        log("INFO", f"--- Processing Source: {source_name} (ID: {source_id}) ---")
        source_products = fetch_source_products(source)
        
        created = updated = skipped = failed = outofstock_count = 0
        current_source_skus = set()

        # 1. Create or Update Products
        for p in source_products:
            sku = p["sku"]
            current_source_skus.add(sku)

            # Map categories
            cat_ids = []
            for path in p["cat_paths"]:
                cid = get_or_create_dest_category_chain(path, dest_cat_map)
                if cid:
                    cat_ids.append({"id": cid})

            payload = {
                "name": p["name"],
                "sku": sku,
                "regular_price": p["regular_price"],
                "sale_price": p["sale_price"],
                "description": p["description"],
                "short_description": p["short_description"],
                "manage_stock": True,
                "stock_quantity": p["stock_quantity"],
                "stock_status": p["stock_status"],
                "categories": cat_ids,
                "images": p["images"]
            }

            new_hash = make_hash(payload)
            old_hash = hashes.get(sku)
            old_prod = dest_existing.get(sku)

            # Skip unchanged products
            if old_prod and old_hash == new_hash:
                skipped += 1
                continue

            # Create new product
            if not old_prod:
                log("CREATE", f"[{source_id}] Creating product: {sku}")
                r = request("POST", f"{DEST_BASE_URL}/products", json=payload, auth=DEST_AUTH)
                if r:
                    created += 1
                    hashes[sku] = new_hash
                else:
                    failed += 1
                time.sleep(0.2)
                continue

            # Update existing product
            log("UPDATE", f"[{source_id}] Updating product: {sku} | ID: {old_prod['id']}")
            r = request("PUT", f"{DEST_BASE_URL}/products/{old_prod['id']}", json=payload, auth=DEST_AUTH)
            if r:
                updated += 1
                hashes[sku] = new_hash
            else:
                failed += 1
            time.sleep(0.2)

        # 2. Mark missing products from THIS source as Out of Stock
        prefix = f"{source_id}-"
        for sku, old_prod in dest_existing.items():
            if sku.startswith(prefix) and sku not in current_source_skus:
                if old_prod.get("stock_status") == "outofstock" and old_prod.get("stock_quantity") == 0:
                    continue

                log("OUTOFSTOCK", f"[{source_id}] Marking Out of Stock: {sku} | ID: {old_prod['id']}")
                r = request(
                    "PUT",
                    f"{DEST_BASE_URL}/products/{old_prod['id']}",
                    auth=DEST_AUTH,
                    json={"stock_status": "outofstock", "stock_quantity": 0}
                )
                if r:
                    outofstock_count += 1
                else:
                    failed += 1
                time.sleep(0.2)

        log("INFO", f"Source [{source_name}] Summary -> Created: {created}, Updated: {updated}, Skipped: {skipped}, Out-of-Stock: {outofstock_count}, Failed: {failed}")

    # Save hash cache
    save_hashes(hashes)
    log("INFO", "===== SYNC CYCLE COMPLETED =====")


# ---------------- ENTRY POINT / SCHEDULER ----------------
if __name__ == "__main__":
    if RUN_ONCE:
        log("INFO", "Running in single-execution mode.")
        sync_sources()
    else:
        log("INFO", f"Running in daemon mode. Sync interval: every {SYNC_INTERVAL_HOURS} hours.")
        while True:
            try:
                sync_sources()
            except Exception as e:
                log("CRITICAL", f"Unexpected error in main loop: {e}")
            
            sleep_seconds = int(SYNC_INTERVAL_HOURS * 3600)
            log("INFO", f"Sleeping for {SYNC_INTERVAL_HOURS} hours ({sleep_seconds} seconds)...")
            time.sleep(sleep_seconds)