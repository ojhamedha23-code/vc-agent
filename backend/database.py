"""
PostgreSQL database for storing screened deals.
Falls back to SQLite if DATABASE_URL is not set (local dev without Supabase).
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

# ── Choose driver based on DATABASE_URL ───────────────────────────────────────
if DATABASE_URL.startswith("postgresql"):
    import psycopg2
    import psycopg2.extras

    def _conn():
        conn = psycopg2.connect(DATABASE_URL)
        return conn

    def _rows(cursor):
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]

    def _one(cursor):
        cols = [d[0] for d in cursor.description]
        row = cursor.fetchone()
        return dict(zip(cols, row)) if row else None

    PLACEHOLDER = "%s"
    UPSERT = """
        INSERT INTO deals
        (id, company, sector, stage, hq, fit_pct, action, confidence,
         bonus_pts, deck_name, created_at, file_hash, claims_json, fact_json,
         thesis_json, memo_json, search_logs, slide_texts, errors_json)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
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
    USE_PG = True

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

    PLACEHOLDER = "?"
    UPSERT = """
        INSERT OR REPLACE INTO deals
        (id, company, sector, stage, hq, fit_pct, action, confidence,
         bonus_pts, deck_name, created_at, file_hash, claims_json, fact_json,
         thesis_json, memo_json, search_logs, slide_texts, errors_json)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """
    USE_PG = False


@contextmanager
def get_db():
    conn = _conn()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS deals (
                id          TEXT PRIMARY KEY,
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
        # Add file_hash column if it doesn't exist (for existing DBs)
        try:
            cur.execute("ALTER TABLE deals ADD COLUMN file_hash TEXT")
        except Exception:
            pass


def get_deal_by_hash(file_hash: str) -> Optional[dict]:
    """Return existing deal if same file was already screened."""
    with get_db() as conn:
        cur = conn.cursor()
        if USE_PG:
            cur.execute("SELECT * FROM deals WHERE file_hash = %s LIMIT 1", (file_hash,))
        else:
            cur.execute("SELECT * FROM deals WHERE file_hash = ? LIMIT 1", (file_hash,))
        return _one(cur)


def save_deal(deal_id: str, deck_name: str, result, file_hash: str = None) -> dict:
    claims  = result.claims
    thesis  = result.thesis_result
    memo    = result.memo

    row = (
        deal_id,
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
        cur.execute(UPSERT, row)

    return {"id": deal_id, "company": row[1]}


def get_all_deals() -> List[dict]:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM deals ORDER BY created_at DESC")
        return _rows(cur)


def get_deal(deal_id: str) -> Optional[dict]:
    with get_db() as conn:
        cur = conn.cursor()
        if USE_PG:
            cur.execute("SELECT * FROM deals WHERE id = %s", (deal_id,))
        else:
            cur.execute("SELECT * FROM deals WHERE id = ?", (deal_id,))
        return _one(cur)


def delete_deal(deal_id: str):
    with get_db() as conn:
        cur = conn.cursor()
        if USE_PG:
            cur.execute("DELETE FROM deals WHERE id = %s", (deal_id,))
        else:
            cur.execute("DELETE FROM deals WHERE id = ?", (deal_id,))
