
from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional, Literal

ISO_CURRENCY = Literal["EUR","USD","GBP"]

class Address(BaseModel):
    line1: Optional[str] = None
    line2: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = Field(default=None, min_length=2, max_length=2, description="ISO 3166-1 alpha-2")
    region: Optional[str] = None

class Buyer(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    address: Optional[Address] = None

class Item(BaseModel):
    product_id: str
    quantity: int = Field(default=1, ge=1, le=100)

class CreateSessionRequest(BaseModel):
    item: Item
    buyer: Buyer
    currency: ISO_CURRENCY = "EUR"
    shared_payment_token: Optional[str] = Field(default=None, description="Agent-provided SPT")

class Session(BaseModel):
    id: str
    status: Literal["requires_confirmation", "succeeded", "failed"]
    payment_intent_id: Optional[str] = None

class ConfirmSessionResponse(Session):
    pass
