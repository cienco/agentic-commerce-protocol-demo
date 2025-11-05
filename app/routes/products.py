from typing import List, Optional
import os
from fastapi import APIRouter, HTTPException, Query
from ..db import get_conn
from ..models import Product
from pydantic import ValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi import Request
import logging
logger = logging.getLogger("acp.products")

router = APIRouter(tags=["products"])

def table_has(conn, table: str, col: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info('{table}')").fetchall()
    return any(r[1] == col for r in rows)

# Helper per validare URL lato SQL
@router.get("/products", summary="List products (public)", response_model=List[Product])
async def list_products(
    request: Request,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    category: Optional[str] = None,
    q: Optional[str] = None,
    max_price: Optional[float] = None,
    color: Optional[str] = None,
    size: Optional[str] = None,
):
    logger.info("QUERY_PARAMS %s", dict(request.query_params))   
    conn = get_conn()

    # Verifica schema base
    required = ["id", "title", "description", "price", "currency"]
    for c in required:
        if not table_has(conn, "products", c):
            raise HTTPException(status_code=500, detail=f"products table missing required column '{c}'")

    base = os.getenv("PUBLIC_BASE_URL", "https://acp-merchant.onrender.com")

    where, params = [], []
    if category:
        where.append("LOWER(category) = LOWER(?)")
        params.append(category)
    if q:
        like = f"%{q}%"
        where.append("(title ILIKE ? OR brand ILIKE ? OR category ILIKE ? OR description ILIKE ?)")
        params += [like, like, like, like]
    if max_price is not None:
        where.append("price <= ?")
        params.append(max_price)
    if color:
        where.append("LOWER(color) = LOWER(?)")
        params.append(color)
    if size:
        where.append("replace(size, ',', '.') = replace(?, ',', '.')")
        params.append(size)

    where_sql = (" WHERE " + " AND ".join(where)) if where else ""

    query = f"""
        SELECT
            id,
            substr(title, 1, 150) AS title_safe,
            substr(description, 1, 5000) AS desc_safe,
            ('{base}' || '/product/' || id) AS link,
            brand,
            category,
            price,
            upper(COALESCE(currency, 'EUR')) AS currency_safe,
            CASE
              WHEN image_url IS NOT NULL
                   AND regexp_matches(image_url, '^(http|https)://') THEN image_url
              ELSE NULL
            END AS image_url_safe,
            size,
            color,
            return_policy,
            available
        FROM products
        {where_sql}
        LIMIT ? OFFSET ?
    """
    params += [int(limit), int(offset)]
    rows = conn.execute(query, params).fetchall()

    items: List[Product] = []
    skipped = 0

    for r in rows:
        try:
            items.append(Product(
                id=str(r[0]),
                title=str(r[1]) if r[1] is not None else "",
                description=str(r[2]) if r[2] is not None else "",
                link=str(r[3]),
                brand=r[4] or None,
                category=r[5] or None,
                price=float(r[6]) if r[6] is not None else 0.0,
                currency=str(r[7]) if r[7] else "EUR",
                image_url=r[8] or None,
                size=(str(r[9]) if r[9] not in (None, '') else None),
                color=(r[10] or None),
                return_policy=(r[11] or None),
                available=bool(r[12]) if r[12] is not None else True,
            ))
        except ValidationError as e:
            skipped += 1
            logger.warning("Product validation skipped id=%s error=%s", r[0], e)

    payload = jsonable_encoder(items)  # Converti gli URL in stringhe
    resp = JSONResponse(content=payload, headers={"X-Items-Skipped": str(skipped)})
    return resp
