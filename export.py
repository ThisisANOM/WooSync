import requests
import json
import time

BASE_URL = "https://SOURCEDOMAIN/wp-json/wc/store/v1/products"

products = []
page = 1

while True:
    params = {
        "page": page,
        "per_page": 100,
        "orderby": "popularity",
        "order": "desc",
        "stock_status": "instock"
    }

    print(f"Fetching page {page}...")

    r = requests.get(
        BASE_URL,
        params=params,
        timeout=30,
        headers={
            "User-Agent": "Mozilla/5.0"
        }
    )

    if r.status_code != 200:
        print(f"Error: {r.status_code}")
        break

    data = r.json()

    if not data:
        print("No more products.")
        break

    for p in data:

        prices = p.get("prices", {})

        try:
            base_price = int(prices.get("sale_price") or 0)
        except:
            base_price = 0

        discounted_price = int(base_price * 0.98)

        if "prices" in p:
            p["prices"]["sale_price"] = str(discounted_price)

        products.append(p)

    print(f"Received {len(data)} products")

    page += 1
    time.sleep(0.5)

print(f"Total products: {len(products)}")

with open("products.json", "w", encoding="utf-8") as f:
    json.dump(products, f, ensure_ascii=False, indent=2)

print("Saved to products.json")