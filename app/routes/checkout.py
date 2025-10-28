
import uuid, json
from fastapi import APIRouter, HTTPException, Header, Depends
from ..models import CreateSessionRequest, UpdateSessionRequest, Session, CompleteResponse, Cart, CartTotals, LineItem
from ..payments.stripe_client import create_payment_intent, confirm_payment_intent
from ..db import get_conn, get_idempotent_response, save_idempotent_response
from ..security import verify_api_key

router = APIRouter(tags=["checkout"], dependencies=[Depends(verify_api_key)])

def price_cents_for_product(conn, product_id: str) -> int:
    row = conn.execute("SELECT price FROM products WHERE id = ?", [product_id]).fetchone()
    if not row:
        raise HTTPException(status_code=400, detail=f"Unknown product_id: {product_id}")
    return int(round(float(row[0]) * 100))

def compute_totals(conn, items: list[LineItem], currency: str, promo_code: str | None) -> CartTotals:
    subtotal = 0
    for it in items:
        subtotal += price_cents_for_product(conn, it.product_id) * it.quantity

    discount = 0
    if promo_code and promo_code.upper() == "WELCOME10":
        discount = int(subtotal * 0.10)

    taxable_base = max(0, subtotal - discount)
    tax = int(round(taxable_base * 0.22))  # demo IVA 22%
    shipping = 500 if currency.upper() == "EUR" and (subtotal/100.0) < 50.0 else 0
    grand = max(0, taxable_base + tax + shipping)

    return CartTotals(
        subtotal_minor=subtotal,
        discount_minor=discount,
        tax_minor=tax,
        shipping_minor=shipping,
        grand_total_minor=grand,
        currency=currency.upper()
    )

def serialize_session(id: str, status: str, cart: Cart, payment_intent_id: str | None):
    return Session(id=id, status=status, cart=cart, payment_intent_id=payment_intent_id)

@router.post("/checkout/sessions", response_model=Session, summary="Create checkout session")
async def create_session(req: CreateSessionRequest, x_idempotency_key: str | None = Header(default=None)):
    conn = get_conn()
    cached = get_idempotent_response(x_idempotency_key, "create")
    if cached:
        return Session.model_validate_json(cached)

    totals = compute_totals(conn, [LineItem(**i.model_dump()) for i in req.items], req.currency, None)
    cart = Cart(items=req.items, totals=totals)

    pi = create_payment_intent(
        amount_minor=totals.grand_total_minor,
        currency=req.currency.lower(),
        buyer_email=req.buyer.email,
        shared_payment_token=req.shared_payment_token,
        metadata={"purpose":"acp_demo","items":json.dumps([i.model_dump() for i in req.items])},
    )

    sid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO checkout_sessions (id, status, payment_intent_id, buyer_email, currency, items_json, promo_code, totals_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [sid, "requires_confirmation", pi["id"], req.buyer.email, req.currency, json.dumps([i.model_dump() for i in req.items]), None, cart.totals.model_dump_json()]
    )

    session_obj = serialize_session(sid, "requires_confirmation", cart, pi["id"])
    if x_idempotency_key:
        save_idempotent_response(x_idempotency_key, "create", session_obj.model_dump_json())

    return session_obj

@router.post("/checkout/sessions/{session_id}", response_model=Session, summary="Update checkout session")
async def update_session(session_id: str, req: UpdateSessionRequest):
    conn = get_conn()
    row = conn.execute("SELECT payment_intent_id, currency, items_json, promo_code FROM checkout_sessions WHERE id = ?", [session_id]).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")

    pi_id, currency, items_json, promo_code = row
    items = [LineItem(**i) for i in json.loads(items_json)]

    if req.items is not None:
        items = req.items
    if req.currency is not None:
        currency = req.currency
    if req.promo_code is not None:
        promo_code = req.promo_code

    totals = compute_totals(conn, [LineItem(**i.model_dump()) for i in items], currency, promo_code)
    cart = Cart(items=items, totals=totals)

    conn.execute(
        "UPDATE checkout_sessions SET currency = ?, items_json = ?, promo_code = ?, totals_json = ?, updated_at = now() WHERE id = ?",
        [currency, json.dumps([i.model_dump() for i in items]), promo_code, cart.totals.model_dump_json(), session_id]
    )

    return serialize_session(session_id, "requires_confirmation", cart, pi_id)

@router.post("/checkout/sessions/{session_id}/complete", response_model=CompleteResponse, summary="Complete checkout session (confirm payment)")
async def complete_session(session_id: str, x_idempotency_key: str | None = Header(default=None)):
    conn = get_conn()
    cached = get_idempotent_response(x_idempotency_key, "complete")
    if cached:
        return CompleteResponse.model_validate_json(cached)

    row = conn.execute("SELECT status, payment_intent_id, buyer_email, currency, items_json, totals_json FROM checkout_sessions WHERE id = ?", [session_id]).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")

    status, pi_id, buyer_email, currency, items_json, totals_json = row
    items = [LineItem(**i) for i in json.loads(items_json)]
    totals = CartTotals.model_validate_json(totals_json)
    cart = Cart(items=items, totals=totals)

    res = confirm_payment_intent(pi_id)
    new_status = "succeeded" if res.get("status") == "succeeded" else "failed"

    if new_status == "succeeded":
        conn.execute(
            "INSERT INTO orders (id, payment_intent_id, buyer_email, amount_minor, currency, items_json) VALUES (?, ?, ?, ?, ?, ?)",
            [str(uuid.uuid4()), pi_id, buyer_email, totals.grand_total_minor, currency, json.dumps([i.model_dump() for i in items])]
        )

    conn.execute("UPDATE checkout_sessions SET status = ?, updated_at = now() WHERE id = ?", [new_status, session_id])

    resp = CompleteResponse(id=session_id, status=new_status, cart=cart, payment_intent_id=pi_id)
    if x_idempotency_key:
        save_idempotent_response(x_idempotency_key, "complete", resp.model_dump_json())

    return resp
