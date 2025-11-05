from typing import List, Optional
import os
from fastapi import APIRouter, HTTPException, Query
from ..db import get_conn
from ..models import Product
from pydantic import ValidationError
import logging
logger = logging.getLogger("acp.products")

router = APIRouter(tags=["products"])

def table_has(conn, table: str, col: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info('{table}')").fetchall()
    return any(r[1] == col for r in rows)

# piccolo helper per validare url lato SQL: lo facciamo direttamente in SELECT con regex

@router.get("/products", summary="List products (public)", response_model=List[Product])
async def list_products(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    category: Optional[str] = None,
    q: Optional[str] = None,
    max_price: Optional[float] = None,
    color: Optional[str] = None,
    size: Optional[str] = None,
):
    """
    Restituisce prodotti in formato ACP esteso con campi:
    id, title, description, link, brand, category, price, currency, image_url, size, color, return_policy, available.
    Applica sanifiche ACP (title<=150, description<=5000, currency uppercase, image_url valida).
    """
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

    # Sanifiche in SQL:
    # - substr(title,1,150) as title_safe  (ACP)
    # - substr(description,1,5000) as desc_safe (ACP)
    # - upper(COALESCE(currency,'EUR')) as currency_safe
    # - image_url_valid: solo se inizia con http/https, altrimenti NULL
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

    # ... dentro list_products, dopo rows = conn.execute(...).fetchall()
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
            # logga id e messaggio: utile per ripulire i pochi record rognosi
            logger.warning("Product validation skipped id=%s error=%s", r[0], e)

    # opzionale: se vuoi sapere quanti sono stati saltati, puoi anche aggiungere un header
    from fastapi.responses import JSONResponse
    resp = JSONResponse([i.model_dump() for i in items])
    resp.headers["X-Items-Skipped"] = str(skipped)
    return resp


@router.get("/products/{product_id}", summary="Get product detail", response_model=Product)
async def get_product(product_id: str):
    conn = get_conn()
    base = os.getenv("PUBLIC_BASE_URL", "https://acp-merchant.onrender.com")

    row = conn.execute(f"""
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
        WHERE id = ?
        LIMIT 1
    """, [product_id]).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Product not found")

    return Product(
        id=str(row[0]),
        title=str(row[1]) if row[1] is not None else "",
        description=str(row[2]) if row[2] is not None else "",
        link=str(row[3]),
        brand=row[4] or None,
        category=row[5] or None,
        price=float(row[6]) if row[6] is not None else 0.0,
        currency=str(row[7]) if row[7] else "EUR",
        image_url=row[8] or None,
        size=(str(row[9]) if row[9] not in (None, '') else None),
        color=(row[10] or None),
        return_policy=(row[11] or None),
        available=bool(row[12]) if row[12] is not None else True,
    )
