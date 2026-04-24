"""
PostgreSQL / SQLite database for storing screened deals.
Falls back to SQLite if DATABASE_URL is not set (local dev).

Multi-tenancy: every deal is scoped to an `org_id` (Clerk org).
Org-level settings (thesis text, notify email) live in `org_settings`.
"""
from __future__ import annotations

import json
import os
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", "")

# ── Choose driver ─────────────────────────────────────────────────────────────
if DATABASE_URL.startswith("postgresql"):
    import psycopg2
    import psycopg2.extras  # noqa: F401

    def _conn():
        return psycopg2.connect(DATABASE_URL)

    def _rows(cursor):
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]

    def _one(cursor):
        cols = [d[0] for d in cursor.description]
        row = cursor.fetchone()
        return dict(zip(cols, row)) if row else None

    P = "%s"  # placeholder
    USE_PG = True

    UPSERT_DEAL = f"""
        INSERT INTO deals
          (id, org_id, uploaded_by, company, sector, stage, hq,
           fit_pct, action, confidence, bonus_pts, deck_name,
           created_at, file_hash,
           claims_json, fact_json, thesis_json, memo_json,
           search_logs, slide_texts, errors_json)
        VALUES ({", ".join([P]*21)})
        ON CONFLICT (id) DO UPDATE SET
          company=EXCLUDED.company, sector=EXCLUDED.sector,
          stage=EXCLUDED.stage, hq=EXCLUDED.hq,
          fit_pct=EXCLUDED.fit_pct, action=EXCLUDED.action,
          confidence=EXCLUDED.confidence, bonus_pts=EXCLUDED.bonus_pts,
          deck_name=EXCLUDED.deck_name, created_at=EXCLUDED.created_at,
          file_hash=EXCLUDED.file_hash,
          claims_json=EXCLUDED.claims_json, fact_json=EXCLUDED.fact_json,
          thesis_json=EXCLUDED.thesis_json, memo_json=EXCLUDED.memo_json,
          search_logs=EXCLUDED.search_logs, slide_texts=EXCLUDED.slide_texts,
          errors_json=EXCLUDED.errors_json
    """

else:
    import sqlite3

    DB_PATH = Path(__file__).parent.parent / "output" / "deals.db"
    DB_PATH.parent.mkdir(exist_ok=True)

    def _conn():
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        return conn

    def _rows(cursor):
        return [dict(r) for r in cursor.fetchall()]

    def _one(cursor):
        row = cursor.fetchone()
        return dict(row) if row else None

    P = "?"
    USE_PG = False

    UPSERT_DEAL = f"""
        INSERT OR REPLACE INTO deals
          (id, org_id, uploaded_by, company, sector, stage, hq,
           fit_pct, action, confidence, bonus_pts, deck_name,
           created_at, file_hash,
           claims_json, fact_json, thesis_json, memo_json,
           search_logs, slide_texts, errors_json)
        VALUES ({", ".join([P]*21)})
    """


# ── Connection context manager ────────────────────────────────────────────────

@contextmanager
def get_db():
    conn = _conn()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


# ── Schema init ───────────────────────────────────────────────────────────────

def init_db():
    with get_db() as conn:
        cur = conn.cursor()

        # ── deals table ───────────────────────────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS deals (
                id          TEXT PRIMARY KEY,
                org_id      TEXT,
                uploaded_by TEXT,
                company     TEXT NOT NULL,
                sector      TEXT,
                stage       TEXT,
                hq          TEXT,
                fit_pct     REAL,
                action      TEXT,
                confidence  TEXT,
                bonus_pts   INTEGER DEFAULT 0,
                deck_name   TEXT,
                created_at  TEXT,
                file_hash   TEXT,
                claims_json TEXT,
                fact_json   TEXT,
                thesis_json TEXT,
                memo_json   TEXT,
                search_logs TEXT,
                slide_texts TEXT,
                errors_json TEXT
            )
        """)

        # Migrate existing DBs — add new columns if absent
        for col, definition in [
            ("org_id",      "TEXT"),
            ("uploaded_by", "TEXT"),
            ("file_hash",   "TEXT"),
        ]:
            try:
                cur.execute(f"ALTER TABLE deals ADD COLUMN {col} {definition}")
            except Exception:
                pass  # column already exists

        # ── org_settings table ────────────────────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS org_settings (
                org_id       TEXT PRIMARY KEY,
                thesis_text  TEXT DEFAULT '',
                notify_email TEXT DEFAULT '',
                updated_at   TEXT
            )
        """)


# ── Deal queries ──────────────────────────────────────────────────────────────

def get_deal_by_hash(file_hash: str, org_id: str) -> Optional[dict]:
    """Return existing deal if the same file was already screened by this org."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            f"SELECT * FROM deals WHERE file_hash = {P} AND org_id = {P} LIMIT 1",
            (file_hash, org_id),
        )
        return _one(cur)


def save_deal(
    deal_id: str,
    deck_name: str,
    result,
    org_id: str = "default_org",
    uploaded_by: str = "unknown",
    file_hash: str = None,
) -> dict:
    claims = result.claims
    thesis = result.thesis_result
    memo   = result.memo

    row = (
        deal_id,
        org_id,
        uploaded_by,
        claims.startup_name if claims else deck_name,
        claims.business_model.model_type if claims else None,
        claims.investment.series if claims else None,
        claims.hq_location if claims else None,
        thesis.overall_fit if thesis else None,
        thesis.action if thesis else "ERROR",
        thesis.confidence if thesis else None,
        thesis.bonus_points.total() if thesis else 0,
        deck_name,
        datetime.utcnow().isoformat(),
        file_hash,
        claims.model_dump_json() if claims else None,
        result.fact_result.model_dump_json() if result.fact_result else None,
        thesis.model_dump_json() if thesis else None,
        memo.model_dump_json() if memo else None,
        json.dumps([s.model_dump() for s in result.search_logs]),
        json.dumps(result.slide_texts),
        json.dumps(result.errors),
    )

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(UPSERT_DEAL, row)

    return {"id": deal_id, "company": row[3]}


def get_all_deals(org_id: str = "default_org") -> List[dict]:
    """Return all deals for this organisation, newest first."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            f"SELECT * FROM deals WHERE org_id = {P} ORDER BY created_at DESC",
            (org_id,),
        )
        return _rows(cur)


def get_deal(deal_id: str, org_id: str = "default_org") -> Optional[dict]:
    """Return a single deal, ensuring it belongs to the caller's org."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            f"SELECT * FROM deals WHERE id = {P} AND org_id = {P}",
            (deal_id, org_id),
        )
        return _one(cur)


def delete_deal(deal_id: str, org_id: str = "default_org"):
    """Delete a deal, enforcing org ownership."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            f"DELETE FROM deals WHERE id = {P} AND org_id = {P}",
            (deal_id, org_id),
        )


# ── Org settings ──────────────────────────────────────────────────────────────

_THESIS_FILE  = Path(__file__).parent.parent / "config" / "thesis_text.txt"
_EMAIL_FILE   = Path(__file__).parent.parent / "config" / "notify_email.txt"


def get_org_settings(org_id: str) -> dict:
    """
    Fetch per-org settings (thesis text + notify email).
    Falls back to legacy config files for backward compatibility.
    """
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM org_settings WHERE org_id = {P}", (org_id,))
        row = _one(cur)

    if row:
        return {"thesis_text": row.get("thesis_text", ""), "notify_email": row.get("notify_email", "")}

    # ── Legacy fallback (single-tenant file config) ───────────────────────────
    thesis = _THESIS_FILE.read_text().strip() if _THESIS_FILE.exists() else ""
    email  = _EMAIL_FILE.read_text().strip()  if _EMAIL_FILE.exists()  else ""
    return {"thesis_text": thesis, "notify_email": email}


def save_org_thesis(org_id: str, thesis_text: str):
    """Upsert the thesis text for an org."""
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        cur = conn.cursor()
        if USE_PG:
            cur.execute("""
                INSERT INTO org_settings (org_id, thesis_text, updated_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (org_id) DO UPDATE SET
                  thesis_text = EXCLUDED.thesis_text,
                  updated_at  = EXCLUDED.updated_at
            """, (org_id, thesis_text, now))
        else:
            cur.execute("""
                INSERT INTO org_settings (org_id, thesis_text, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(org_id) DO UPDATE SET
                  thesis_text = excluded.thesis_text,
                  updated_at  = excluded.updated_at
            """, (org_id, thesis_text, now))


def save_org_email(org_id: str, notify_email: str):
    """Upsert the notification email for an org."""
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        cur = conn.cursor()
        if USE_PG:
            cur.execute("""
                INSERT INTO org_settings (org_id, notify_email, updated_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (org_id) DO UPDATE SET
                  notify_email = EXCLUDED.notify_email,
                  updated_at   = EXCLUDED.updated_at
            """, (org_id, notify_email, now))
        else:
            cur.execute("""
                INSERT INTO org_settings (org_id, notify_email, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(org_id) DO UPDATE SET
                  notify_email = excluded.notify_email,
                  updated_at   = excluded.updated_at
            """, (org_id, notify_email, now))
