
import os
import stripe
from fastapi import APIRouter, Request, HTTPException

router = APIRouter(tags=["webhooks"])
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")

@router.post("/webhooks/stripe", summary="Stripe webhook (test/demo)")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    try:
        event = stripe.Webhook.construct_event(payload=payload, sig_header=sig_header, secret=webhook_secret)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Webhook error: {e}")

    print(f"[WEBHOOK] {event.get('type')}")
    return {"received": True}
