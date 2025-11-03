import os, io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from datetime import datetime

ISSUER_NAME = os.getenv("INVOICE_ISSUER_NAME", "Mi Comunidad")
ISSUER_TAXID = os.getenv("INVOICE_ISSUER_TAXID", "B12345678")
ISSUER_ADDRESS = os.getenv("INVOICE_ISSUER_ADDRESS", "Calle Mayor 1, Madrid")

def _draw_header(c):
    c.setFont("Helvetica-Bold", 16)
    c.drawString(20*mm, 280*mm, ISSUER_NAME)
    c.setFont("Helvetica", 10)
    c.drawString(20*mm, 275*mm, f"NIF: {ISSUER_TAXID}")
    c.drawString(20*mm, 270*mm, ISSUER_ADDRESS)

def _draw_footer(c):
    c.setFont("Helvetica", 8)
    c.drawString(20*mm, 10*mm, f"Generado el {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")

def build_invoice_pdf(invoice, member) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    _draw_header(c)

    # Cabecera de factura
    c.setFont("Helvetica-Bold", 14)
    label = f"Factura {getattr(invoice, 'full_number', '') or '#' + str(invoice.id)}"
    c.drawString(20*mm, 255*mm, label)

    c.setFont("Helvetica", 11)
    y = 245*mm
    c.drawString(20*mm, y, f"Fecha emisión: {invoice.issue_date}")
    y -= 6*mm
    if invoice.due_date:
        c.drawString(20*mm, y, f"Fecha vencimiento: {invoice.due_date}")
        y -= 6*mm

    # Cliente
    full_name = f"{member.first_name} {member.last_name}" if member else "Miembro"
    c.drawString(20*mm, y, f"Cliente: {full_name}")
    y -= 6*mm
    if member and member.email:
        c.drawString(20*mm, y, f"Email: {member.email}")
        y -= 6*mm

    # Concepto
    y -= 6*mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(20*mm, y, "Detalle")
    y -= 8*mm
    c.setFont("Helvetica", 11)
    c.drawString(22*mm, y, invoice.description)

    # Importe
    y -= 12*mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(20*mm, y, "Importe")
    c.setFont("Helvetica", 11)
    c.drawString(22*mm, y-8*mm, f"{invoice.amount_cents/100:.2f} {invoice.currency}")

    # Estado
    c.setFont("Helvetica", 11)
    c.drawString(20*mm, y-20*mm, f"Estado: {invoice.status}")

    _draw_footer(c)
    c.showPage()
    c.save()

    buffer.seek(0)
    return buffer.getvalue()
