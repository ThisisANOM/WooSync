import os
import time
import requests
import urllib3
from dotenv import load_dotenv


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
    """Executes HTTP request with retry logic and SSL verification bypass."""
    kwargs.setdefault("verify", False)
    
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


# ---------------- DELETE PRODUCT IMAGES FROM HOST ----------------
def delete_product_images(image_ids):
    """Permanently deletes images from Media Library and Host storage."""
    if not image_ids:
        return 0

    deleted_images_count = 0
    # Construct WordPress REST API endpoint for media
    wp_base_url = DEST_BASE_URL.rsplit("/wc/", 1)[0] + "/wp/v2/media"

    for img_id in image_ids:
        # force=true permanently deletes file from host storage
        del_url = f"{wp_base_url}/{img_id}?force=true"
        r = request("DELETE", del_url, auth=DEST_AUTH)
        if r:
            deleted_images_count += 1

    return deleted_images_count


# ---------------- BATCH DELETE PRODUCTS & IMAGES ----------------
def delete_all_products():
    """Fetches products, deletes associated images from host, and force-deletes products in batches."""
    print("\n--- Starting Products & Images Cleanup ---")
    deleted_total = 0
    deleted_images_total = 0

    while True:
        # Fetch products along with image information
        r = request("GET", f"{DEST_BASE_URL}/products", auth=DEST_AUTH, params={"per_page": 50, "_fields": "id,images"})
        if not r:
            break

        products = r.json()
        if not products:
            print("No more products found.")
            break

        product_ids = []
        image_ids_to_delete = set()

        for p in products:
            product_ids.append(p["id"])
            for img in p.get("images", []):
                if img.get("id"):
                    image_ids_to_delete.add(img["id"])

        # 1. Delete associated images from Host Storage & Media Library
        if image_ids_to_delete:
            img_count = delete_product_images(image_ids_to_delete)
            deleted_images_total += img_count
            print(f"[INFO] Permanently deleted {img_count} images from host for this batch.")

        # 2. Execute Batch Delete Request for Products
        payload = {"delete": product_ids}
        del_response = request("POST", f"{DEST_BASE_URL}/products/batch", auth=DEST_AUTH, json=payload)

        if del_response:
            deleted_count = len(product_ids)
            deleted_total += deleted_count
            print(f"[SUCCESS] Permanently deleted batch of {deleted_count} products. Total Products: {deleted_total}")
        else:
            print("[ERROR] Failed to delete current batch of products.")
            break

        time.sleep(0.5)

    print(f"Products cleanup finished. Total Products Deleted: {deleted_total} | Total Images Deleted: {deleted_images_total}")


# ---------------- BATCH DELETE CATEGORIES ----------------
def delete_all_categories():
    """Fetches and force-deletes all custom categories in batches of 50."""
    print("\n--- Starting Categories Cleanup ---")
    deleted_total = 0

    while True:
        r = request("GET", f"{DEST_BASE_URL}/products/categories", auth=DEST_AUTH, params={"per_page": 50, "_fields": "id,slug"})
        if not r:
            break

        categories = r.json()
        # Exclude 'uncategorized' default category
        cat_ids = [c["id"] for c in categories if c.get("slug") != "uncategorized"]

        if not cat_ids:
            print("No more custom categories found.")
            break

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
    print(" WARNING: THIS WILL PERMANENTLY DELETE ALL PRODUCTS,")
    print(" THEIR IMAGES FROM HOST, AND CATEGORIES!")
    print("==================================================")
    
    confirm = input("Are you sure you want to proceed? (type 'YES' to confirm): ")
    if confirm.strip() == "YES":
        delete_all_products()
        delete_all_categories()
        reset_hash_file()
        print("\nCleanup completed successfully!")
    else:
        print("\nOperation cancelled by user.")
