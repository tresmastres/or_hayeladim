from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from sqlmodel import Session, select
from typing import List
from datetime import datetime
import os, stripe

from database import init_db, get_session
from models import User, Family, Member, Invoice, InvoiceSequence, Payment, Donation
from schemas import (
    Token, UserCreate, UserRead,
    FamilyCreate, FamilyRead,
    MemberCreate, MemberRead,
    InvoiceCreate, InvoiceRead,
    PaymentCreate, PaymentRead,
    DonationCreate, DonationRead
)
from utils import hash_password, verify_password, create_access_token
from auth import get_current_user
from pdf import build_invoice_pdf
from emailer import send_mail

app = FastAPI(title="ShulCloud-Lite (Español) — Miembros, Facturación y Donaciones")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

@app.on_event("startup")
def on_startup():
    init_db()

# ── Auth ─────────────────────────────────────────────────────────────────
@app.post("/auth/register", response_model=UserRead, tags=["Auth"])
def register(data: UserCreate, session: Session = Depends(get_session)):
    if session.exec(select(User).where(User.email == data.email)).first():
        raise HTTPException(400, "El email ya está registrado")
    user = User(email=data.email, hashed_password=hash_password(data.password), is_admin=True)
    session.add(user); session.commit(); session.refresh(user)
    return UserRead(id=user.id, email=user.email, is_admin=user.is_admin)

@app.post("/auth/login", response_model=Token, tags=["Auth"])
def login(data: UserCreate, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.email == data.email)).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(401, "Credenciales inválidas")
    return Token(access_token=create_access_token(user.email))

# ── Familias ──────────────────────────────────────────────────────────────
@app.post("/families", response_model=FamilyRead, tags=["Familias"])
def create_family(payload: FamilyCreate, session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    fam = Family(**payload.dict())
    session.add(fam); session.commit(); session.refresh(fam)
    return fam

@app.get("/families", response_model=List[FamilyRead], tags=["Familias"])
def list_families(session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    return session.exec(select(Family)).all()

# ── Miembros ──────────────────────────────────────────────────────────────
@app.post("/members", response_model=MemberRead, tags=["Miembros"])
def create_member(payload: MemberCreate, session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    m = Member(**payload.dict())
    session.add(m); session.commit(); session.refresh(m)
    return m

@app.get("/members", response_model=List[MemberRead], tags=["Miembros"])
def list_members(session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    return session.exec(select(Member)).all()

# ── Facturación ───────────────────────────────────────────────────────────
@app.post("/invoices", response_model=InvoiceRead, tags=["Facturación"])
def create_invoice(payload: InvoiceCreate, session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    # Numeración fiscal: serie por año (por defecto = año de emisión)
    year = payload.issue_date.year
    series = str(year)
    seq = session.exec(select(InvoiceSequence).where(InvoiceSequence.series == series, InvoiceSequence.year == year)).first()
    if not seq:
        seq = InvoiceSequence(series=series, year=year, next_number=1)
        session.add(seq); session.flush()
    number = seq.next_number
    seq.next_number = number + 1

    inv = Invoice(**payload.dict())
    inv.series = series
    inv.number = number
    inv.full_number = f"{series}-{number:05d}"

    session.add(inv)
    session.commit(); session.refresh(inv)

    # Envío automático de PDF
    member = session.get(Member, inv.member_id)
    if member and member.email:
        pdf_bytes = build_invoice_pdf(inv, member)
        try:
            send_mail(
                to_addrs=[member.email],
                subject=f"Factura {inv.full_number}",
                body=(f"Hola {member.first_name},\n\nAdjuntamos tu factura {inv.full_number} por "
                      f"{inv.amount_cents/100:.2f} {inv.currency}.\n\nSaludos."),
                attachments=[(f"Factura_{inv.full_number}.pdf", pdf_bytes, "application/pdf")],
            )
        except Exception:
            pass

    return inv

@app.get("/invoices", response_model=List[InvoiceRead], tags=["Facturación"])
def list_invoices(session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    return session.exec(select(Invoice)).all()

@app.get("/invoices/{invoice_id}/pdf", tags=["Facturación"])
def invoice_pdf(invoice_id: int, session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    inv = session.get(Invoice, invoice_id)
    if not inv:
        raise HTTPException(404, "Factura no encontrada")
    member = session.get(Member, inv.member_id)
    pdf_bytes = build_invoice_pdf(inv, member)
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f"inline; filename=invoice_{invoice_id}.pdf"})

@app.post("/payments", response_model=PaymentRead, tags=["Pagos"])
def register_payment(payload: PaymentCreate, session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    inv = session.get(Invoice, payload.invoice_id)
    if not inv:
        raise HTTPException(404, "Factura no encontrada")
    pay = Payment(**payload.dict())
    session.add(pay)
    inv.status = "paid" if payload.amount_cents >= inv.amount_cents else inv.status
    session.add(inv)
    session.commit(); session.refresh(pay)

    # Email de pago recibido
    member = session.get(Member, inv.member_id)
    if member and member.email and inv.status == "paid":
        pdf_bytes = build_invoice_pdf(inv, member)
        try:
            send_mail(
                to_addrs=[member.email],
                subject=f"Pago recibido - Factura {inv.full_number}",
                body=(f"Hola {member.first_name},\n\nHemos registrado tu pago de "
                      f"{payload.amount_cents/100:.2f} {inv.currency}. Adjuntamos la factura como pagada.\n\nGracias."),
                attachments=[(f"Factura_{inv.full_number}_pagada.pdf", pdf_bytes, "application/pdf")],
            )
        except Exception:
            pass

    return pay

# ── Donaciones ────────────────────────────────────────────────────────────
@app.post("/donations", response_model=DonationRead, tags=["Donaciones"])
def create_donation(payload: DonationCreate, session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    d = Donation(**payload.dict())
    session.add(d); session.commit(); session.refresh(d)
    return d

@app.get("/donations", response_model=List[DonationRead], tags=["Donaciones"])
def list_donations(session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    return session.exec(select(Donation)).all()

# ── Stripe (opcional) ────────────────────────────────────────────────────
@app.post("/stripe/checkout", tags=["Stripe"])
def create_checkout_session(member_id: int, amount_cents: int, description: str, invoice_id: int | None = None):
    if not stripe.api_key:
        raise HTTPException(400, "Stripe no está configurado")
    session_obj = stripe.checkout.Session.create(
        mode="payment",
        line_items=[{"price_data": {"currency": "eur", "product_data": {"name": description}, "unit_amount": amount_cents}, "quantity": 1}],
        success_url="https://example.org/success",
        cancel_url="https://example.org/cancel",
        metadata={"member_id": str(member_id), "invoice_id": str(invoice_id) if invoice_id else ""},
    )
    return {"checkout_url": session_obj.url}

@app.post("/stripe/webhook", tags=["Stripe"])
async def stripe_webhook(request: Request, session: Session = Depends(get_session)):
    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(400, "Falta STRIPE_WEBHOOK_SECRET")
    payload = await request.body()
    sig = request.headers.get("stripe-signature")
    try:
        event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
    except Exception as e:
        raise HTTPException(400, f"Error de webhook: {e}")

    if event["type"] == "checkout.session.completed":
        data = event["data"]["object"]
        amount_total = data.get("amount_total")
        metadata = data.get("metadata", {}) or {}
        member_id = metadata.get("member_id")
        invoice_id = metadata.get("invoice_id")
        payment_intent = data.get("payment_intent")

        if invoice_id:
            inv = session.get(Invoice, int(invoice_id))
            if inv:
                pay = Payment(
                    invoice_id=inv.id,
                    paid_at=datetime.utcnow(),
                    amount_cents=amount_total,
                    method="stripe",
                    external_id=payment_intent,
                )
                inv.status = "paid"
                session.add(pay); session.add(inv); session.commit()

                # Email factura pagada
                member = session.get(Member, inv.member_id)
                if member and member.email:
                    pdf_bytes = build_invoice_pdf(inv, member)
                    try:
                        send_mail(
                            to_addrs=[member.email],
                            subject=f"Pago recibido - Factura {inv.full_number}",
                            body=(f"Hola {member.first_name},\n\nHemos recibido tu pago por "
                                  f"{inv.amount_cents/100:.2f} {inv.currency}. Adjuntamos la factura marcada como pagada.\n\nGracias."),
                            attachments=[(f"Factura_{inv.full_number}_pagada.pdf", pdf_bytes, "application/pdf")],
                        )
                    except Exception:
                        pass
        else:
            don = Donation(
                member_id=int(member_id) if member_id else None,
                donated_at=datetime.utcnow(),
                amount_cents=amount_total,
                currency="EUR",
                campaign="Stripe Checkout",
                method="stripe",
                external_id=payment_intent,
            )
            session.add(don); session.commit()

    return {"received": True}

from fastapi import APIRouter
from sqlalchemy.orm import Session
from database import SessionLocal

router = APIRouter(prefix="/reports", tags=["Reports"])

@router.get("/summary")
def get_summary():
    db: Session = SessionLocal()
    invoices = db.query(Invoice).all()
    total_invoices_eur = sum(i.amount_cents for i in invoices if i.currency == "EUR") / 100
    open_invoices = sum(1 for i in invoices if i.status == "open")
    paid_invoices = sum(1 for i in invoices if i.status == "paid")
    return {
        "total_invoices_eur": total_invoices_eur,
        "open_invoices": open_invoices,
        "paid_invoices": paid_invoices,
        "total_donations_eur": 0
    }

app.include_router(router)

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from database import engine  # o SessionLocal si lo usas
# importa tus modelos existentes:
# from models import Invoice, Member, ...
# y los nuevos:
from database import Banco, Cobro  # o desde models si los pusiste ahí

def get_session():
    with Session(engine) as session:
        yield session

api_bancos = APIRouter(prefix="/banks", tags=["Banks"])
api_cobros = APIRouter(prefix="/payments", tags=["Payments"])
api_reportes = APIRouter(prefix="/reports", tags=["Reports"])  # si aún no lo tenías
api_members = APIRouter(prefix="/members", tags=["Members"])   # para estado de cuenta

# --- BANCOS ---
@api_bancos.get("", response_model=list[Banco])
def list_bancos(session: Session = Depends(get_session)):
    return session.exec(select(Banco).order_by(Banco.nombre)).all()

@api_bancos.post("", response_model=Banco)
def create_banco(data: Banco, session: Session = Depends(get_session)):
    session.add(data)
    session.commit()
    session.refresh(data)
    return data

# --- COBROS ---
class CobroIn(SQLModel):
    invoice_id: int
    amount_cents: int
    metodo: str  # 'efectivo' | 'tpv' | 'transferencia'
    banco_id: Optional[int] = None
    fecha: Optional[date] = None

@api_cobros.get("")
def list_cobros(
    invoice_id: Optional[int] = Query(default=None),
    session: Session = Depends(get_session)
):
    q = select(Cobro)
    if invoice_id:
        q = q.where(Cobro.invoice_id == invoice_id)
    return session.exec(q.order_by(Cobro.fecha.desc(), Cobro.id.desc())).all()

@api_cobros.post("", status_code=201)
def create_cobro(payload: CobroIn, session: Session = Depends(get_session)):
    # validar factura
    inv = session.exec(select(Invoice).where(Invoice.id == payload.invoice_id)).first()
    if not inv:
        raise HTTPException(404, "Invoice not found")

    # crear cobro
    cobro = Cobro(
        invoice_id=payload.invoice_id,
        amount_cents=payload.amount_cents,
        metodo=payload.metodo,
        banco_id=payload.banco_id,
        fecha=payload.fecha or datetime.utcnow().date()
    )
    session.add(cobro)

    # actualizar estado de factura según total cobrado
    total_cobrado = (session.exec(
        select(Cobro).where(Cobro.invoice_id == payload.invoice_id)
    ).all() or [])
    total_prev = sum(c.amount_cents for c in total_cobrado)
    total_final = total_prev + payload.amount_cents

    if total_final >= inv.amount_cents:
        inv.status = "paid"
    else:
        # si quieres soportar 'partial', úsalo; si no, deja 'open'
        inv.status = "partial"

    session.add(inv)
    session.commit()
    session.refresh(cobro)
    return {"ok": True, "payment_id": cobro.id, "invoice_status": inv.status}

# --- ESTADO DE CUENTA DEL MIEMBRO ---
@api_members.get("/{member_id}/account")
def member_account(member_id: int, session: Session = Depends(get_session)):
    # Facturas del miembro
    invoices = session.exec(select(Invoice).where(Invoice.member_id == member_id)).all()
    # Cobros de esas facturas
    ids = [i.id for i in invoices]
    cobros = []
    if ids:
        cobros = session.exec(select(Cobro).where(Cobro.invoice_id.in_(ids))).all()

    # Mapear totales por factura
    paid_map = {}
    for c in cobros:
        paid_map[c.invoice_id] = paid_map.get(c.invoice_id, 0) + c.amount_cents

    data = []
    for inv in invoices:
        paid = paid_map.get(inv.id, 0)
        balance = max(inv.amount_cents - paid, 0)
        data.append({
            "invoice_id": inv.id,
            "full_number": getattr(inv, "full_number", None),
            "issue_date": getattr(inv, "issue_date", None),
            "amount_cents": inv.amount_cents,
            "currency": inv.currency,
            "status": inv.status,
            "paid_cents": paid,
            "balance_cents": balance,
        })

    return {"member_id": member_id, "invoices": data, "total_balance_cents": sum(d["balance_cents"] for d in data)}

# Si aún no están incluidas:
app.include_router(api_bancos)
app.include_router(api_cobros)
app.include_router(api_members)  # ya existirá; si no, inclúyelo


