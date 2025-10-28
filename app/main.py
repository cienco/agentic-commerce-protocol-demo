
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes.products import router as products_router
from .routes.checkout import router as checkout_router
from .routes.webhooks import router as webhooks_router
from .db import init_db

app = FastAPI(
    title="ACP-style Merchant API",
    version="0.3.0",
    description="ACP-like checkout API for GPT Actions demos. Public OpenAPI at /openapi.json",
)

# CORS (allow all origins for demo; tighten in prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    init_db()

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

# public products (no auth)
app.include_router(products_router, prefix="")
# commerce routes (with API key dependency inside)
app.include_router(checkout_router, prefix="")
app.include_router(webhooks_router, prefix="")
