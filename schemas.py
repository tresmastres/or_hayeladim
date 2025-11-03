from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import date, datetime

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserRead(BaseModel):
    id: int
    email: EmailStr
    is_admin: bool

class FamilyCreate(BaseModel):
    family_name: str
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None

class FamilyRead(FamilyCreate):
    id: int

class MemberCreate(BaseModel):
    first_name: str
    last_name: str
    email: Optional[EmailStr] = None
    birth_date: Optional[date] = None
    affiliation: Optional[str] = None
    anniversary: Optional[date] = None
    yahrzeit: Optional[date] = None
    family_id: Optional[int] = None

class MemberRead(MemberCreate):
    id: int

class InvoiceCreate(BaseModel):
    member_id: int
    issue_date: date
    due_date: Optional[date] = None
    description: str
    amount_cents: int
    currency: str = "EUR"

class InvoiceRead(InvoiceCreate):
    id: int
    status: str
    series: Optional[str] = None
    number: Optional[int] = None
    full_number: Optional[str] = None

class PaymentCreate(BaseModel):
    invoice_id: int
    paid_at: datetime
    amount_cents: int
    method: str
    external_id: Optional[str] = None

class PaymentRead(PaymentCreate):
    id: int

class DonationCreate(BaseModel):
    member_id: Optional[int] = None
    donated_at: datetime
    amount_cents: int
    currency: str = "EUR"
    campaign: Optional[str] = None
    note: Optional[str] = None
    method: str = "stripe"
    external_id: Optional[str] = None

class DonationRead(DonationCreate):
    id: int
