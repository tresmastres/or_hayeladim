from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import date, datetime

from database import (
    init_db, get_session, Family, Member, Invoice, Bank, Payment
)

app = FastAPI(title="ShulCloud-Lite Español")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    init_db()


# --- Familias ---
@app.get("/families")
def list_families(session: Session = Depends(get_session)):
    return session.query(Family).all()

@app.post("/families")
def create_family(data: dict, session: Session = Depends(get_session)):
    fam = Family(name=data["name"], email=data.get("email"))
    session.add(fam); session.commit(); session.refresh(fam)
    return fam


# --- Miembros ---
@app.get("/members")
def list_members(session: Session = Depends(get_session)):
    return session.query(Member).all()

@app.post("/members")
def create_member(data: dict, session: Session = Depends(get_session)):
    mem = Member(
        first_name=data["first_name"],
        last_name=data["last_name"],
        date_of_birth=data.get("date_of_birth"),
        family_id=data.get("family_id")
    )
    session.add(mem); session.commit(); session.refresh(mem)
    return mem


# --- Facturas ---
@app.get("/invoices")
def list_invoices(session: Session = Depends(get_session)):
    return session.query(Invoice).all()

@app.post("/invoices")
def create_invoice(data: dict, session: Session = Depends(get_session)):
    inv = Invoice(
        member_id=data["member_id"],
        amount_cents=data["amount_cents"],
        currency=data.get("currency", "EUR"),
        issue_date=data.get("issue_date", date.today()),
        status="open",
    )
    session.add(inv); session.commit(); session.refresh(inv)
    return inv


# --- Bancos ---
@app.get("/banks")
def list_banks(session: Session = Depends(get_session)):
    return session.query(Bank).all()

@app.post("/banks")
def create_bank(data: dict, session: Session = Depends(get_session)):
    bank = Bank(
        nombre=data["nombre"],
        numero_cuenta=data.get("numero_cuenta"),
        swift=data.get("swift"),
        activo=True
    )
    session.add(bank); session.commit(); session.refresh(bank)
    return bank


# --- Cobros ---
@app.get("/payments")
def list_payments(session: Session = Depends(get_session)):
    return session.query(Payment).all()

@app.post("/payments")
def register_payment(data: dict, session: Session = Depends(get_session)):
    inv = session.get(Invoice, data["invoice_id"])
    if not inv:
        raise HTTPException(404, "Factura no encontrada")

    pay = Payment(
        invoice_id=inv.id,
        amount_cents=data["amount_cents"],
        metodo=data["metodo"],
        banco_id=data.get("banco_id"),
        fecha=data.get("fecha", date.today())
    )
    session.add(pay)

    # Actualiza estado de factura
    total_pagado = sum(p.amount_cents for p in inv.payments) + data["amount_cents"]
    inv.status = "paid" if total_pagado >= inv.amount_cents else "partial"
    session.add(inv)

    session.commit(); session.refresh(pay)
    return pay


# --- Estado de cuenta ---
@app.get("/members/{member_id}/account")
def member_account(member_id: int, session: Session = Depends(get_session)):
    member = session.get(Member, member_id)
    if not member:
        raise HTTPException(404, "Miembro no encontrado")

    invoices = session.query(Invoice).filter_by(member_id=member_id).all()
    cobros = session.query(Payment).filter(Payment.invoice_id.in_([i.id for i in invoices])).all()

    resumen = []
    for inv in invoices:
        pagado = sum(c.amount_cents for c in cobros if c.invoice_id == inv.id)
        balance = max(inv.amount_cents - pagado, 0)
        resumen.append({
            "invoice_id": inv.id,
            "amount": inv.amount_cents / 100,
            "paid": pagado / 100,
            "balance": balance / 100,
            "status": inv.status,
        })

    return {"member": member_id, "invoices": resumen}


@app.get("/")
def home():
    return {"status": "ok", "message": "ShulCloud Lite listo 🚀"}
