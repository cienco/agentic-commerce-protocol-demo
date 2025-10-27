
import os
import stripe
from fastapi import APIRouter, Request, HTTPException

router = APIRouter()
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")

@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    try:
        event = stripe.Webhook.construct_event(payload=payload, sig_header=sig_header, secret=webhook_secret)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Webhook error: {e}")

    etype = event.get("type")
    if etype == "payment_intent.succeeded":
        pi = event["data"]["object"]
        print(f"[WEBHOOK] PaymentIntent succeeded: {pi['id']}")
    elif etype == "payment_intent.payment_failed":
        pi = event["data"]["object"]
        print(f"[WEBHOOK] PaymentIntent failed: {pi['id']}")
    else:
        print(f"[WEBHOOK] Unhandled: {etype}")

    return {"received": True}
