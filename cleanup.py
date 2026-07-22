import os
import time
import requests
from dotenv import load_dotenv

# ---------------- LOAD ENVIRONMENT VARIABLES ----------------
load_dotenv()

DEST_BASE_URL = os.getenv("DEST_BASE_URL")
DEST_CK = os.getenv("DEST_CK")
DEST_CS = os.getenv("DEST_CS")

if not all([DEST_BASE_URL, DEST_CK, DEST_CS]):
    print("[ERROR] Missing destination credentials in .env file!")
    exit(1)

DEST_AUTH = (DEST_CK, DEST_CS)
HASH_FILE = "hashes.json"


# ---------------- HTTP REQUEST HELPER ----------------
def request(method, url, **kwargs):
    """Executes HTTP request with retry logic for network resilience."""
    for attempt in range(3):
        try:
            r = requests.request(method, url, timeout=30, **kwargs)
            if r.status_code in [200, 201]:
                return r
            print(f"[ERROR] HTTP {r.status_code} on {url} -> {r.text[:200]}")
        except Exception as e:
            print(f"[ERROR] Request Exception on {url}: {e}")
        time.sleep(1 + attempt)
    return None


# ---------------- BATCH DELETE PRODUCTS ----------------
def delete_all_products():
    """Fetches and force-deletes all products in batches of 50."""
    print("\n--- Starting Products Cleanup ---")
    deleted_total = 0

    while True:
        # Fetch current batch of product IDs
        r = request("GET", f"{DEST_BASE_URL}/products", auth=DEST_AUTH, params={"per_page": 50, "_fields": "id"})
        if not r:
            break

        products = r.json()
        if not products:
            print("No more products found.")
            break

        product_ids = [p["id"] for p in products]

        # Execute Batch Delete Request
        payload = {"delete": product_ids}
        del_response = request("POST", f"{DEST_BASE_URL}/products/batch", auth=DEST_AUTH, json=payload)

        if del_response:
            deleted_count = len(product_ids)
            deleted_total += deleted_count
            print(f"[SUCCESS] Permanently deleted batch of {deleted_count} products. Total: {deleted_total}")
        else:
            print("[ERROR] Failed to delete current batch of products.")
            break

        time.sleep(0.5)

    print(f"Products cleanup finished. Total deleted: {deleted_total}")


# ---------------- BATCH DELETE CATEGORIES ----------------
def delete_all_categories():
    """Fetches and force-deletes all categories in batches of 50."""
    print("\n--- Starting Categories Cleanup ---")
    deleted_total = 0

    while True:
        # Fetch current batch of category IDs (excluding Uncategorized default category)
        r = request("GET", f"{DEST_BASE_URL}/products/categories", auth=DEST_AUTH, params={"per_page": 50, "_fields": "id,slug"})
        if not r:
            break

        categories = r.json()
        # Exclude 'uncategorized' as WooCommerce core prevents deleting it
        cat_ids = [c["id"] for c in categories if c.get("slug") != "uncategorized"]

        if not cat_ids:
            print("No more custom categories found.")
            break

        # Execute Batch Delete Request
        payload = {"delete": cat_ids}
        del_response = request("POST", f"{DEST_BASE_URL}/products/categories/batch", auth=DEST_AUTH, json=payload)

        if del_response:
            deleted_count = len(cat_ids)
            deleted_total += deleted_count
            print(f"[SUCCESS] Permanently deleted batch of {deleted_count} categories. Total: {deleted_total}")
        else:
            print("[ERROR] Failed to delete current batch of categories.")
            break

        time.sleep(0.5)

    print(f"Categories cleanup finished. Total deleted: {deleted_total}")


# ---------------- RESET HASH CACHE ----------------
def reset_hash_file():
    """Removes the hash tracking file so the sync script can re-create products cleanly."""
    if os.path.exists(HASH_FILE):
        os.remove(HASH_FILE)
        print(f"\n[INFO] Cache file '{HASH_FILE}' removed successfully.")


# ---------------- MAIN EXECUTION ----------------
if __name__ == "__main__":
    print("==================================================")
    print(" WARNING: THIS WILL PERMANENTLY DELETE ALL PRODUCTS")
    print(" AND CATEGORIES FROM THE DESTINATION SITE!")
    print("==================================================")
    
    confirm = input("Are you sure you want to proceed? (type 'YES' to confirm): ")
    if confirm.strip() == "YES":
        delete_all_products()
        delete_all_categories()
        reset_hash_file()
        print("\nCleanup completed successfully!")
    else:
        print("\nOperation cancelled by user.")