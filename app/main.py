
import os
from fastapi import FastAPI
from .routes.products import router as products_router
from .routes.checkout import router as checkout_router
from .routes.webhooks import router as webhooks_router
from .db import init_db

app = FastAPI(title="ACP Python Demo (FastAPI + Stripe + MotherDuck)", version="0.2.0")

@app.on_event("startup")
def startup():
    init_db()

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

app.include_router(products_router, prefix="")
app.include_router(checkout_router, prefix="")
app.include_router(webhooks_router, prefix="")
