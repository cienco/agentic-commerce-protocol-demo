
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Literal, List

ISO_CURRENCY = Literal["EUR","USD","GBP"]

class Address(BaseModel):
    line1: Optional[str] = None
    line2: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = Field(default=None, min_length=2, max_length=2)
    region: Optional[str] = None

class Buyer(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    address: Optional[Address] = None

class LineItem(BaseModel):
    product_id: str
    quantity: int = Field(default=1, ge=1, le=100)

class CartTotals(BaseModel):
    subtotal_minor: int
    discount_minor: int
    tax_minor: int
    shipping_minor: int
    grand_total_minor: int
    currency: ISO_CURRENCY = "EUR"

class Cart(BaseModel):
    items: List[LineItem]
    totals: CartTotals

class CreateSessionRequest(BaseModel):
    items: List[LineItem]
    buyer: Buyer
    currency: ISO_CURRENCY = "EUR"
    shared_payment_token: Optional[str] = None
    idempotency_key: Optional[str] = None  # <-- alias compatibile GPT Actions

class UpdateSessionRequest(BaseModel):
    items: Optional[List[LineItem]] = None
    buyer: Optional[Buyer] = None
    currency: Optional[ISO_CURRENCY] = None
    promo_code: Optional[str] = None

class Session(BaseModel):
    id: str
    status: Literal["requires_confirmation", "requires_action", "succeeded", "failed"]
    cart: Cart
    payment_intent_id: Optional[str] = None

class CompleteResponse(Session):
    pass
