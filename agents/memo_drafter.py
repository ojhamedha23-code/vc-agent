"""
Agent 4: Memo Drafter
Synthesizes all prior agent outputs into a structured investment memo.
Uses Claude Opus 4.6 for highest-quality prose.
"""
import json
from pathlib import Path

import anthropic

from schemas.models import (
    BonusPoints,
    ClaimsJSON,
    DealBreakerFlags,
    FactCheckResult,
    InvestmentMemo,
    ThesisFitResult,
)

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "memo_drafter.txt"
SYSTEM_PROMPT = PROMPT_PATH.read_text()


def _build_score_table(thesis_result: ThesisFitResult) -> str:
    rows = [
        ("Sector Fit", thesis_result.sector_fit.score, "40%"),
        ("Geography Fit", thesis_result.geography_fit.score, "25%"),
        ("Stage Fit", thesis_result.stage_fit.score, "10%"),
        ("ARR / Traction Fit", thesis_result.arr_traction_fit.score, "25%"),
    ]
    lines = [
        "| Dimension | Score | Weight | Weighted |",
        "|-----------|-------|--------|----------|",
    ]
    for name, score, weight in rows:
        w = float(weight.strip("%")) / 100
        weighted = score * w
        lines.append(f"| {name} | {score} | {weight} | {weighted:.1f} |")
    lines.append(f"| **OVERALL** | | | **{thesis_result.overall_fit:.1f}** |")
    return "\n".join(lines)


def _build_deal_breaker_text(db: DealBreakerFlags) -> str:
    if not db.any_triggered():
        return (
            "Deal Breaker: **NO** — No deal breakers triggered.\n"
            "✓ Has recurring revenue (not pilots/LOIs only)\n"
            "✓ B2B software model confirmed\n"
            "✓ B2B ICP confirmed"
        )
    flags = []
    if db.pre_product_pre_revenue:
        flags.append("✗ Pre-product / pre-revenue (no signed recurring contracts)")
    if db.hardware_business_model:
        flags.append("✗ Hardware business model (capital-intensive, low margin)")
    if db.d2c_consumer_ecommerce:
        flags.append("✗ D2C / Consumer / E-commerce model detected")
    return "Deal Breaker: **YES**\n" + "\n".join(flags)


def _build_bonus_text(bp: BonusPoints) -> str:
    total = bp.total()
    lines = [f"Bonus Points: **{total} / 3**"]
    lines.append("✓ Renowned VC backers" if bp.renowned_vc_backers else "✗ No renowned VC backers on cap table")
    lines.append("✓ Clear path to profitability" if bp.clear_path_to_profitability else "✗ Path to profitability not clearly articulated")
    lines.append("✓ Repeat founder / serial entrepreneur" if bp.repeat_founder else "✗ First-time founder")
    return "\n".join(lines)


def run(
    claims: ClaimsJSON,
    fact_result: FactCheckResult,
    thesis_result: ThesisFitResult,
    client: anthropic.Anthropic,
) -> InvestmentMemo:
    score_table = _build_score_table(thesis_result)
    deal_breaker_text = _build_deal_breaker_text(fact_result.deal_breakers)
    bonus_text = _build_bonus_text(thesis_result.bonus_points)

    user_content = (
        f"ACTION: {thesis_result.action}\n\n"
        f"CLAIMS:\n{claims.model_dump_json(indent=2)}\n\n"
        f"FACT CHECK RESULTS:\n{fact_result.model_dump_json(indent=2)}\n\n"
        f"THESIS FIT SCORES:\n{thesis_result.model_dump_json(indent=2)}\n\n"
        f"PRE-BUILT SCORE TABLE (use this verbatim in thesis_score_table):\n{score_table}\n\n"
        f"PRE-BUILT DEAL BREAKER TEXT (use this verbatim in deal_breaker_status):\n{deal_breaker_text}\n\n"
        f"PRE-BUILT BONUS POINTS TEXT (use this verbatim in bonus_points_summary):\n{bonus_text}"
    )

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    data = json.loads(raw)

    return InvestmentMemo(
        startup_name=claims.startup_name,
        overall_fit=thesis_result.overall_fit,
        action=thesis_result.action,
        confidence=thesis_result.confidence,
        thesis_score_table=data.get("thesis_score_table", score_table),
        deal_breaker_status=data.get("deal_breaker_status", deal_breaker_text),
        bonus_points_summary=data.get("bonus_points_summary", bonus_text),
        summary_business=data.get("summary_business", ""),
        summary_market=data.get("summary_market", ""),
        summary_unit_econ=data.get("summary_unit_econ", ""),
        summary_traction=data.get("summary_traction", ""),
        summary_product=data.get("summary_product", ""),
        summary_team=data.get("summary_team", ""),
        top_3_risks=data.get("top_3_risks", []),
        reasons_to_invest=data.get("reasons_to_invest", []),
        reasons_to_pass=data.get("reasons_to_pass", []),
        founder_questions=data.get("founder_questions", []),
        recommended_next_step=data.get("recommended_next_step", ""),
    )
