import requests
import json
import time
import re
from datetime import datetime

BASE_WP = "https://YOURDOMAINHERE/wp-json/wc/v3"
PRODUCTS_URL = f"{BASE_WP}/products"
CATEGORIES_URL = f"{BASE_WP}/products/categories"

CK = "YOUR_WP_APPLICATION_USERNAME"
CS = "YOUR_WP_APPLICATION_PASSWORD"

AUTH = (CK, CS)

LOG_FILE = "sync_log.txt"

def log(level, msg):
    line = f"[{datetime.now()}] [{level}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def request(method, url, **kwargs):
    for i in range(3):
        try:
            r = requests.request(method, url, timeout=30, **kwargs)

            if r.status_code in [200, 201]:
                return r

            log("ERROR", f"{r.status_code} → {r.text}")

        except Exception as e:
            log("ERROR", str(e))

        time.sleep(1 + i)

    return None


def clean_sku(raw):
    if not raw:
        raw = "product"

    sku = raw.lower()
    sku = re.sub(r"[^a-z0-9\-]", "-", sku)
    sku = re.sub(r"-+", "-", sku).strip("-")

    return sku or "product"


def get_all_categories():
    r = request("GET", CATEGORIES_URL, auth=AUTH, params={"per_page": 100})
    if not r:
        return {}

    data = r.json()
    return {
        (c["name"].strip().lower(), c.get("slug")): c["id"]
        for c in data
    }


def find_category(name, cache):

    key = (name.strip().lower(), None)

    for (n, _), cid in cache.items():
        if n == name.strip().lower():
            return cid

    r = request(
        "GET",
        CATEGORIES_URL,
        auth=AUTH,
        params={"search": name}
    )

    if r:
        for c in r.json():
            if c["name"].strip().lower() == name.strip().lower():
                cache[(c["name"].strip().lower(), None)] = c["id"]
                return c["id"]

    r = request(
        "POST",
        CATEGORIES_URL,
        json={"name": name},
        auth=AUTH
    )

    if r:
        cid = r.json()["id"]
        cache[(name.strip().lower(), None)] = cid
        return cid

    return None


def fetch_existing():
    cache = {}
    page = 1

    while True:
        r = request(
            "GET",
            PRODUCTS_URL,
            auth=AUTH,
            params={"per_page": 100, "page": page}
        )

        if not r:
            break

        data = r.json()
        if not data:
            break

        for p in data:
            if p.get("sku"):
                cache[p["sku"]] = p

        log("INFO", f"Fetched page {page}")
        page += 1

    return cache


def map_images(images):
    if not images:
        return []

    return [{"src": img["src"]} for img in images if img.get("src")]


def build_product(p, sku, cat_cache):

    categories = []

    for c in p.get("categories", []):
        cid = find_category(c["name"], cat_cache)
        if cid:
            categories.append({"id": cid})

    prices = p.get("prices", {})

    return {
        "name": p.get("name"),
        "sku": sku,

        "regular_price": str(prices.get("price") or "0"),
        "sale_price": str(prices.get("sale_price") or ""),

        "description": p.get("description") or "",
        "short_description": p.get("short_description") or "",

        "images": map_images(p.get("images")),

        "categories": categories
    }


with open("products.json", "r", encoding="utf-8") as f:
    products = json.load(f)

log("INFO", f"Loaded {len(products)} products")

cat_cache = get_all_categories()
existing = fetch_existing()

created = updated = failed = 0

for p in products:

    raw_sku = p.get("sku") or str(p.get("id"))
    sku = clean_sku(raw_sku)

    payload = build_product(p, sku, cat_cache)

    old = existing.get(sku)

    # CREATE
    if not old:
        log("CREATE", sku)

        r = request("POST", PRODUCTS_URL, json=payload, auth=AUTH)

        if r:
            created += 1
        else:
            failed += 1

        continue

    log("UPDATE", f"{sku} | ID:{old['id']}")

    r = request(
        "PUT",
        f"{PRODUCTS_URL}/{old['id']}",
        json=payload,
        auth=AUTH
    )

    if r:
        updated += 1
    else:
        failed += 1

    time.sleep(0.2)


log("INFO", "===== SUMMARY =====")
log("INFO", f"Created: {created}")
log("INFO", f"Updated: {updated}")
log("INFO", f"Failed: {failed}")
log("INFO", "DONE ✔")