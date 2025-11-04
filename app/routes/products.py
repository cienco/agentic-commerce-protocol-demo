# app/routes/products.py
from typing import List
from fastapi import APIRouter, HTTPException, Query
from ..db import get_conn

router = APIRouter(tags=["products"])

def table_columns(conn, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info('{table}')").fetchall()
    return {r[1] for r in rows}

@router.get("/products", summary="List products (public)")
async def list_products(
    limit: int | None = Query(None, ge=1),
    offset: int = Query(0, ge=0),
    category: str | None = None,
    q: str | None = None,
    max_price: float | None = None,
):
    """
    Restituisce prodotti in formato ACP canonico:
    id, title, brand, category, price, currency, description, image_url, available
    """
    conn = get_conn()
    cols = table_columns(conn, "products")

    id_sel = "id" if "id" in cols else ("product_id" if "product_id" in cols else None)
    if not id_sel:
        raise HTTPException(status_code=500, detail="products table missing 'id'/'product_id' column")
    if "title" not in cols:
        raise HTTPException(status_code=500, detail="products table missing 'title' column")

    brand_sel = "brand" if "brand" in cols else "'' AS brand"
    category_sel = "category" if "category" in cols else "'' AS category"
    price_sel = "price" if "price" in cols else "0.0 AS price"
    currency_sel = "currency" if "currency" in cols else "'EUR' AS currency"
    description_sel = "description" if "description" in cols else "'' AS description"
    image_sel = "image_url" if "image_url" in cols else ("image AS image_url" if "image" in cols else "'' AS image_url")
    available_sel = "available" if "available" in cols else "TRUE AS available"

    where, params = [], []
    if category:
        where.append("LOWER(category) = LOWER(?)")
        params.append(category)
    if q:
        like = f"%{q}%"
        where.append("(title ILIKE ? OR brand ILIKE ? OR category ILIKE ? OR description ILIKE ?)")
        params += [like, like, like, like]
    if max_price is not None and "price" in cols:
        where.append("price <= ?")
        params.append(max_price)

    where_sql = (" WHERE " + " AND ".join(where)) if where else ""
    
    limit_sql = ""
    if limit is not None:
        limit_sql = " LIMIT ?"
        params.append(int(limit))
    
    offset_sql = " OFFSET ?" if offset > 0 else ""
    if offset > 0:
        params.append(int(offset))
    
    query = f"""
        SELECT
            {id_sel} AS id,
            title,
            {brand_sel},
            {category_sel},
            {price_sel},
            {currency_sel},
            {description_sel},
            {image_sel},
            {available_sel}
        FROM products
        {where_sql}
        {limit_sql}{offset_sql}
    """

    rows = conn.execute(query, params).fetchall()
    items = []
    for r in rows:
        items.append({
            "id": r[0],
            "title": r[1],
            "brand": r[2],
            "category": r[3],
            "price": float(r[4]) if r[4] is not None else 0.0,
            "currency": r[5],
            "description": r[6],
            "image_url": r[7],
            "available": bool(r[8]) if r[8] is not None else True,
        })
    return items
