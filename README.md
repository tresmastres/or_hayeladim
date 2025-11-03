# ShulCloud-Lite (Español) — Miembros, Facturación y Donaciones

Backend listo para **Render** con **PostgreSQL gratuito**. Incluye:
- FastAPI + SQLModel
- JWT Auth
- Miembros/Familias
- Facturación con **numeración fiscal por año**
- Pagos, Donaciones
- **PDF de facturas** (ReportLab)
- **Emails SMTP** (envío de factura y confirmación de pago)
- **Stripe Checkout + Webhook** (opcional)

## 1) Uso local (opcional)
```bash
python -m venv .venv && source .venv/bin/activate  # Win: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# ajusta DATABASE_URL (puedes usar sqlite:///./app.db para probar)
uvicorn main:app --reload
```
Docs: http://localhost:8000/docs

## 2) Despliegue en Render (con PostgreSQL gratis)
1. Sube este proyecto a GitHub.
2. Crea **Database** en Render → PostgreSQL (Free). Copia su **Internal Database URL**.
3. Crea **Web Service** en Render (Docker). Variables de entorno (desde Settings → Environment):
   - `DATABASE_URL` = Internal Database URL de Render, pero con prefijo **postgresql+psycopg://**
   - `JWT_SECRET` = una cadena aleatoria larga
   - `INVOICE_ISSUER_*` según tu entidad
   - SMTP: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_TLS`
   - (Opcional) Stripe: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`
4. Deploy. El servicio quedará disponible en una URL pública de Render (`https://...onrender.com`).

## 3) Flujo básico
1. `POST /auth/register` → crea admin
2. `POST /auth/login` → copia el token y pulsa **Authorize** en Swagger
3. Crea familia → miembro → factura
4. Abre `GET /invoices/{id}/pdf` (PDF)
5. Registra pago (`/payments`) o usa Stripe (`/stripe/checkout` + webhook)
6. Revisa el email del miembro (recibe PDF)

## 4) Notas
- La **serie** de factura es el **año** de `issue_date`. Formato `AÑO-00001`.
- Ajusta el logo/estilo de PDF en `pdf.py` si quieres.
- Para SQLite local: cambia `DATABASE_URL=sqlite:///./app.db`.

¡Listo para usar!
