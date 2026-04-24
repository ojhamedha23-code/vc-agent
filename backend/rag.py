"""
RAG helpers for past-deal similarity.

This module owns three pure functions:
  - build_deal_text()              — concat deal fields into embeddable text
  - generate_embedding()           — call OpenAI text-embedding-3-small
  - format_similar_deals_for_prompt() — format retrieved deals for Agent 4

Storage and retrieval (pgvector queries) live in database.py:
  - database.update_deal_embedding()
  - database.get_similar_deals()

Degrades gracefully:
  - OPENAI_API_KEY missing  → generate_embedding() returns None
  - Any OpenAI error        → returns None, pipeline continues without RAG
  - SQLite local dev        → database.USE_PG is False, RAG skipped in pipeline
"""
from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY", "")
EMBEDDING_MODEL = "text-embedding-3-small"


# ── Text builder ──────────────────────────────────────────────────────────────

def build_deal_text(claims: dict, thesis: dict) -> str:
    """
    Concatenate the most semantically meaningful fields from a deal into a
    single string for embedding. All fields handled with .get() — fully optional.
    """
    parts: list[str] = []

    def _add(label: str, value):
        if value:
            parts.append(f"{label}: {value}")

    _add("Company",       claims.get("startup_name"))
    _add("Location",      claims.get("hq_location"))

    market = claims.get("market") or {}
    _add("Problem",       market.get("problem"))
    _add("TAM",           market.get("tam"))
    comp = market.get("competition") or []
    if comp:
        _add("Competition", ", ".join(comp))

    product = claims.get("product") or {}
    _add("Solution",      product.get("solution"))
    _add("Moat",          product.get("moat"))

    biz = claims.get("business_model") or {}
    _add("Business Model", biz.get("model_type"))
    _add("ARR",           biz.get("arr"))
    _add("ARR Growth",    biz.get("arr_growth"))
    _add("Customers",     biz.get("num_customers"))
    _add("Gross Margin",  biz.get("gross_margin"))

    team = claims.get("team") or {}
    _add("CEO",           team.get("ceo"))

    inv = claims.get("investment") or {}
    _add("Stage",         inv.get("series"))

    _add("Action",        thesis.get("action"))
    _add("Thesis Fit %",  thesis.get("overall_fit"))
    _add("Sector Reasoning", (thesis.get("sector_fit") or {}).get("reasoning"))
    _add("Geography Reasoning", (thesis.get("geography_fit") or {}).get("reasoning"))

    return "\n".join(parts)


# ── Embedding generation ──────────────────────────────────────────────────────

def generate_embedding(text: str) -> Optional[list[float]]:
    """Call OpenAI text-embedding-3-small. Returns None on any failure."""
    if not OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not set — skipping RAG embedding")
        return None
    if not text.strip():
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.embeddings.create(model=EMBEDDING_MODEL, input=text)
        return response.data[0].embedding
    except Exception as exc:
        logger.warning("Embedding generation failed (non-fatal): %s", exc)
        return None


# ── Prompt formatter ──────────────────────────────────────────────────────────

def format_similar_deals_for_prompt(similar_deals: list[dict]) -> str:
    """
    Format retrieved similar deals into a block for Agent 4's prompt.
    Returns empty string if the list is empty.
    """
    if not similar_deals:
        return ""

    import json
    lines = ["SIMILAR PAST DEALS FROM YOUR PORTFOLIO:"]

    for i, deal in enumerate(similar_deals, 1):
        company = deal.get("company", "Unknown")
        action  = deal.get("action", "?")
        fit_pct = deal.get("fit_pct")
        fit_str = f"{fit_pct:.0f}%" if fit_pct is not None else "N/A"

        sector_reasoning = ""
        top_risks: list[str] = []

        try:
            thesis = json.loads(deal.get("thesis_json") or "{}")
            sector_reasoning = (thesis.get("sector_fit") or {}).get("reasoning", "")
        except Exception:
            pass

        try:
            memo = json.loads(deal.get("memo_json") or "{}")
            top_risks = memo.get("top_3_risks") or []
        except Exception:
            pass

        lines.append(f"\n{i}. {company} ({action}, {fit_str} thesis fit)")
        if sector_reasoning:
            lines.append(f"   Sector: {sector_reasoning[:200]}")
        for risk in top_risks[:2]:
            lines.append(f"   Risk flagged: {risk}")

    return "\n".join(lines)
