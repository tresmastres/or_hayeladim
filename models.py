from typing import Optional, List
from datetime import date, datetime
from sqlmodel import SQLModel, Field, Relationship

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    hashed_password: str
    is_admin: bool = False

class Family(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    family_name: str
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None

    members: List["Member"] = Relationship(back_populates="family")

class Member(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    first_name: str
    last_name: str
    email: Optional[str] = Field(default=None, index=True)
    birth_date: Optional[date] = None
    affiliation: Optional[str] = None
    anniversary: Optional[date] = None
    yahrzeit: Optional[date] = None

    family_id: Optional[int] = Field(default=None, foreign_key="family.id")
    family: Optional[Family] = Relationship(back_populates="members")

class Invoice(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    member_id: int = Field(foreign_key="member.id")
    issue_date: date
    due_date: Optional[date] = None
    description: str
    amount_cents: int
    currency: str = "EUR"
    status: str = Field(default="open")  # open, paid, void
    # Numeración fiscal
    series: Optional[str] = None
    number: Optional[int] = None
    full_number: Optional[str] = None

class InvoiceSequence(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    series: str = Field(index=True)
    year: int = Field(index=True)
    next_number: int = 1

class Payment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    invoice_id: int = Field(foreign_key="invoice.id")
    paid_at: datetime
    amount_cents: int
    method: str  # cash, bank, stripe
    external_id: Optional[str] = None

class Donation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    member_id: Optional[int] = Field(default=None, foreign_key="member.id")
    donated_at: datetime
    amount_cents: int
    currency: str = "EUR"
    campaign: Optional[str] = None
    note: Optional[str] = None
    method: str = "stripe"
    external_id: Optional[str] = None
