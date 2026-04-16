"""
SQLite database for storing screened deals.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import List, Optional

DB_PATH = Path(__file__).parent.parent / "output" / "deals.db"
DB_PATH.parent.mkdir(exist_ok=True)


def _conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


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
        conn.execute("""
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
                claims_json TEXT,
                fact_json   TEXT,
                thesis_json TEXT,
                memo_json   TEXT,
                search_logs TEXT,
                slide_texts TEXT,
                errors_json TEXT
            )
        """)


def save_deal(deal_id: str, deck_name: str, result) -> dict:
    """Persist a PipelineResult to the database."""
    claims = result.claims
    thesis = result.thesis_result
    memo = result.memo

    row = {
        "id": deal_id,
        "company": claims.startup_name if claims else deck_name,
        "sector": (claims.business_model.model_type if claims else None),
        "stage": (claims.investment.series if claims else None),
        "hq": (claims.hq_location if claims else None),
        "fit_pct": (thesis.overall_fit if thesis else None),
        "action": (thesis.action if thesis else "ERROR"),
        "confidence": (thesis.confidence if thesis else None),
        "bonus_pts": (thesis.bonus_points.total() if thesis else 0),
        "deck_name": deck_name,
        "created_at": datetime.utcnow().isoformat(),
        "claims_json": claims.model_dump_json() if claims else None,
        "fact_json": result.fact_result.model_dump_json() if result.fact_result else None,
        "thesis_json": thesis.model_dump_json() if thesis else None,
        "memo_json": memo.model_dump_json() if memo else None,
        "search_logs": json.dumps([s.model_dump() for s in result.search_logs]),
        "slide_texts": json.dumps(result.slide_texts),
        "errors_json": json.dumps(result.errors),
    }

    with get_db() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO deals
            (id, company, sector, stage, hq, fit_pct, action, confidence,
             bonus_pts, deck_name, created_at, claims_json, fact_json,
             thesis_json, memo_json, search_logs, slide_texts, errors_json)
            VALUES
            (:id, :company, :sector, :stage, :hq, :fit_pct, :action, :confidence,
             :bonus_pts, :deck_name, :created_at, :claims_json, :fact_json,
             :thesis_json, :memo_json, :search_logs, :slide_texts, :errors_json)
        """, row)
    return row


def get_all_deals() -> List[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM deals ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_deal(deal_id: str) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM deals WHERE id = ?", (deal_id,)
        ).fetchone()
    return dict(row) if row else None


def delete_deal(deal_id: str):
    with get_db() as conn:
        conn.execute("DELETE FROM deals WHERE id = ?", (deal_id,))
