import requests

SOURCE_URL = "https://SURCEDOMAIN/wp-json/wp/v2/product_cat?per_page=100"
DEST_URL = "https://YOURDOMAINHERE/wp-json/wp/v2/product_cat"

auth = ("YOUR_WP_APPLICATION_USERNAME", "YOUR_WP_APPLICATION_PASSWORD")

source = requests.get(SOURCE_URL).json()

existing = requests.get(DEST_URL + "?per_page=100", auth=auth).json()

slug_to_id = {c["slug"]: c["id"] for c in existing}
id_map = {}

pending = {c["id"]: c for c in source}

progress = True

while pending and progress:
    progress = False
    to_remove = []

    for cid, cat in pending.items():

        parent = cat["parent"]

        if parent == 0:
            parent_id = 0

        else:
            if parent not in id_map:
                continue

            parent_id = id_map[parent]

        if cat["slug"] in slug_to_id:
            id_map[cid] = slug_to_id[cat["slug"]]
            to_remove.append(cid)
            continue

        payload = {
            "name": cat["name"],
            "slug": cat["slug"],
            "parent": parent_id
        }

        r = requests.post(DEST_URL, json=payload, auth=auth)

        if r.status_code in [200, 201]:
            new_id = r.json()["id"]
            id_map[cid] = new_id
            to_remove.append(cid)
            progress = True
            print("✅ Created:", cat["name"])
        else:
            print("❌ Failed:", cat["name"], r.text)

    for cid in to_remove:
        pending.pop(cid)

if pending:
    print("\n⚠️ Orphan categories found:")
    for c in pending.values():
        print("-", c["name"])