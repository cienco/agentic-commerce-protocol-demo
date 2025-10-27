
import os, json
import httpx

BASE = os.getenv("BASE_URL", "http://127.0.0.1:8000")

def main():
    products = httpx.get(f"{BASE}/products").json()
    print("[agent] products:", json.dumps(products, indent=2))

    item = {"product_id": products[0]["product_id"], "quantity": 1}
    payload = {
        "item": item,
        "buyer": {
            "email": "buyer@example.com",
            "name": "Mario Rossi",
            "address": {"line1":"Via Roma 1","city":"Milano","postal_code":"20100","country":"IT"}
        },
        "currency": "EUR",
        "shared_payment_token": "test_spt_visa"
    }

    print("[agent] create session...")
    sess = httpx.post(f"{BASE}/checkout/sessions", json=payload).json()
    print("[agent] session:", json.dumps(sess, indent=2))

    sid = sess["id"]
    print("[agent] confirm...")
    res = httpx.post(f"{BASE}/checkout/sessions/{sid}/confirm").json()
    print("[agent] confirm result:", json.dumps(res, indent=2))

if __name__ == "__main__":
    main()
