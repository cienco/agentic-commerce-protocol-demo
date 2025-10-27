
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from ..db import get_conn

router = APIRouter()

@router.get("/products")
async def list_products():
    conn = get_conn()
    rows = conn.execute("SELECT id as product_id, title, price, currency, image, available FROM products").fetchall()
    cols = [c[0] for c in conn.description]
    items = [dict(zip(cols, r)) for r in rows]
    return JSONResponse(items)
