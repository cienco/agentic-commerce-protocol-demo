
import uuid
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from ..models import CreateSessionRequest, Session, ConfirmSessionResponse
from ..payments.stripe_client import create_payment_intent, confirm_payment_intent
from ..db import get_conn

router = APIRouter()

def fetch_price_cents(conn, product_id: str) -> int:
    row = conn.execute("SELECT price, currency FROM products WHERE id = ?", [product_id]).fetchone()
    if not row:
        raise HTTPException(status_code=400, detail="Unknown product_id")
    price = float(row[0])
    cents = int(round(price * 100))
    return cents

@router.post("/checkout/sessions", response_model=Session)
async def create_session(req: CreateSessionRequest):
    conn = get_conn()

    amount_minor = fetch_price_cents(conn, req.item.product_id) * req.item.quantity
    pi = create_payment_intent(
        amount_minor=amount_minor,
        currency=req.currency.lower(),
        buyer_email=req.buyer.email,
        shared_payment_token=req.shared_payment_token,
        metadata={
            "product_id": req.item.product_id,
            "qty": str(req.item.quantity),
            "buyer_email": req.buyer.email
        },
    )

    sid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO checkout_sessions (id, status, payment_intent_id, buyer_email, currency, product_id, quantity) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [sid, "requires_confirmation", pi["id"], req.buyer.email, req.currency, req.item.product_id, req.item.quantity]
    )

    return Session(id=sid, status="requires_confirmation", payment_intent_id=pi["id"])

@router.post("/checkout/sessions/{session_id}/confirm", response_model=ConfirmSessionResponse)
async def confirm_session(session_id: str):
    conn = get_conn()
    row = conn.execute("SELECT payment_intent_id, buyer_email, currency, product_id, quantity FROM checkout_sessions WHERE id = ?", [session_id]).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")

    pi_id, buyer_email, currency, product_id, qty = row
    res = confirm_payment_intent(pi_id)
    status = "succeeded" if res.get("status") == "succeeded" else "failed"

    # If success, persist as order
    if status == "succeeded":
        amount_minor = fetch_price_cents(conn, product_id) * int(qty)
        conn.execute(
            "INSERT INTO orders (id, payment_intent_id, buyer_email, amount_minor, currency, product_id, quantity) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [str(uuid.uuid4()), pi_id, buyer_email, amount_minor, currency, product_id, qty]
        )

    conn.execute("UPDATE checkout_sessions SET status = ? WHERE id = ?", [status, session_id])
    return ConfirmSessionResponse(id=session_id, status=status, payment_intent_id=pi_id)
