from sqlalchemy import create_engine, Column, Integer, String, Boolean, Date, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data.db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# --- MODELOS BASE ---
class Family(Base):
    __tablename__ = "families"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=True)

    members = relationship("Member", back_populates="family")


class Member(Base):
    __tablename__ = "members"
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    date_of_birth = Column(Date, nullable=True)
    family_id = Column(Integer, ForeignKey("families.id"))

    family = relationship("Family", back_populates="members")
    invoices = relationship("Invoice", back_populates="member")


class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"))
    amount_cents = Column(Integer, nullable=False)
    currency = Column(String, default="EUR")
    issue_date = Column(Date, nullable=False)
    status = Column(String, default="open")
    full_number = Column(String, nullable=True)

    member = relationship("Member", back_populates="invoices")
    payments = relationship("Payment", back_populates="invoice")


class Bank(Base):
    __tablename__ = "banks"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    numero_cuenta = Column(String, nullable=True)
    swift = Column(String, nullable=True)
    activo = Column(Boolean, default=True)


class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"))
    amount_cents = Column(Integer, nullable=False)
    metodo = Column(String, nullable=False)  # efectivo, tpv, transferencia
    banco_id = Column(Integer, ForeignKey("banks.id"), nullable=True)
    fecha = Column(Date, nullable=False)

    invoice = relationship("Invoice", back_populates="payments")
    banco = relationship("Bank")


def init_db():
    Base.metadata.create_all(bind=engine)


def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
