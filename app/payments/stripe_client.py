
import os
import stripe

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")

DEMO_SPT_TO_PM = {
    "test_spt_visa": "pm_card_visa",
    "test_spt_3ds2": "pm_card_authenticationRequired",
}

def resolve_payment_method_from_spt(shared_payment_token: str | None) -> str | None:
    if not shared_payment_token:
        return None
    return DEMO_SPT_TO_PM.get(shared_payment_token)

def create_payment_intent(amount_minor: int, currency: str, buyer_email: str, shared_payment_token: str | None, metadata: dict | None = None):
    pm = resolve_payment_method_from_spt(shared_payment_token)

    kwargs = dict(
        amount=amount_minor,
        currency=currency,
        receipt_email=buyer_email,
        capture_method="automatic",
        metadata=metadata or {},
        confirm=False,
    )
    if pm:
        kwargs["payment_method"] = pm

    pi = stripe.PaymentIntent.create(**kwargs)
    return pi

def confirm_payment_intent(payment_intent_id: str):
    pi = stripe.PaymentIntent.confirm(payment_intent_id)
    return pi
