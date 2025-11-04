from fastapi import APIRouter
from sqlalchemy import text
from app.db import engine

router = APIRouter(prefix="/dev", tags=["dev"])

SQL = """
CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  email VARCHAR(255) UNIQUE NOT NULL,
  name  VARCHAR(255),
  password_hash VARCHAR(255) NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
"""

@router.get("/init")
def init_db():
    with engine.begin() as conn:
        conn.execute(text(SQL))
    return {"ok": True, "message": "users table ready"}
