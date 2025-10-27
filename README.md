
# ACP Python Demo — FastAPI + Stripe + MotherDuck, deployable on Render

This demo extends the ACP-style checkout skeleton with:
- **Pydantic** payloads approximating ACP Checkout objects
- **MotherDuck (DuckDB in the cloud)** for persistence (sessions, orders, products)
- **Render.com** deployment files

> ⚠️ Not an official ACP implementation. Adjust payloads to match the latest spec.

## Local Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Set your Stripe TEST keys and MotherDuck token in .env
uvicorn app.main:app --reload
# In another terminal
python scripts/simulate_agent.py
```

Swagger UI: http://127.0.0.1:8000/docs

### Env vars (.env)
```
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
MOTHERDUCK_TOKEN=mdt_...
MOTHERDUCK_DATABASE=acp_demo   # optional, defaults to 'acp_demo'
APP_DEBUG=true
```

### MotherDuck Notes
- We use `duckdb` Python client. When `MOTHERDUCK_TOKEN` is set, we connect to `md:{MOTHERDUCK_DATABASE}`.
- If token is omitted, we fall back to a **local** DuckDB file `./local.duckdb`.
- On first boot we auto-create tables and seed products from `app/data/product_feed.json`.

### Render deploy (one-click via render.yaml)
1. Push this repo to GitHub.
2. In Render, **New +** → **Blueprint** → pick your repo.
3. Add env vars in the Render service:
   - `STRIPE_SECRET_KEY` (test key)
   - `STRIPE_WEBHOOK_SECRET` (optional if not using webhooks on Render)
   - `MOTHERDUCK_TOKEN` (if you want cloud DB)
   - `MOTHERDUCK_DATABASE` (optional, default `acp_demo`)
4. Render will run `uvicorn` with `$PORT` automatically from `render.yaml`.

## Endpoints
- `GET /healthz`
- `GET /products`
- `POST /checkout/sessions` → create session + PaymentIntent (requires_confirmation)
- `POST /checkout/sessions/{session_id}/confirm` → confirm payment
- `POST /webhooks/stripe`

## Pydantic payloads (approx. ACP)
**CreateSessionRequest**:
```json
{
  "item": {"product_id":"sku_1","quantity":1},
  "buyer": {
    "email":"buyer@example.com",
    "name":"Mario Rossi",
    "address": {
      "line1":"Via Roma 1","city":"Milano","postal_code":"20100","country":"IT"
    }
  },
  "currency":"EUR",
  "shared_payment_token":"test_spt_visa"
}
```
