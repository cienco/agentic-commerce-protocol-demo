
from pydantic import BaseModel, Field, EmailStr, HttpUrl
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
    quantity: int = 1
    unit_amount: float                      # es. 119.99
    currency: str = "EUR"
    title: str = Field(..., max_length=150) # ACP: max 150
    image_url: Optional[HttpUrl] = None     # validato come URL http/https
    # opzionali per varianti:
    color: Optional[str] = None             # es. "black"
    size: Optional[str] = None              # es. "44" o "44.5"
    # opzionale se vuoi
    description: Optional[str] = Field(default=None, max_length=5000)

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


class Product(BaseModel):
    id: str = Field(..., max_length=100)
    title: str = Field(..., max_length=150)
    description: str = Field(..., max_length=5000)
    link: HttpUrl                          # sintetizzato dal server
    brand: Optional[str] = None
    category: Optional[str] = None
    price: float
    currency: str = "EUR"
    image_url: Optional[HttpUrl] = None
    # nuove colonne presenti in tabella
    size: Optional[str] = None             # es. "44" o "44.5" (EU)
    color: Optional[str] = None            # es. "black"
    return_policy: Optional[str] = None    # testo in inglese
    # campo comodo lato client (non in tabella)
    available: bool = True
