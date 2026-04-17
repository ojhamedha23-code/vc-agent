"""
Agent 3: Thesis Fit Scorer
Scores the startup against the VC's investment thesis using free-text thesis input.
Discrete anchors: 0 / 25 / 50 / 75 / 100.
Runs in parallel with Agent 2.
"""
from __future__ import annotations

import json
from pathlib import Path

import anthropic

from schemas.models import ClaimsJSON, FactCheckResult, ThesisFitResult

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "thesis_scorer.txt"
SYSTEM_PROMPT = PROMPT_PATH.read_text()


def run(
    claims: ClaimsJSON,
    fact_result: FactCheckResult,
    thesis_text: str,
    client: anthropic.Anthropic,
) -> ThesisFitResult:
    """
    thesis_text: the fund's investment thesis as plain English free text.
    """
    user_content = (
        f"FUND INVESTMENT THESIS (free text — use this as the source of truth):\n"
        f"{thesis_text}\n\n"
        f"EXTRACTED CLAIMS FROM PITCH DECK:\n{claims.model_dump_json(indent=2)}\n\n"
        f"DEAL BREAKERS DETECTED BY AGENT 2:\n{fact_result.deal_breakers.model_dump_json(indent=2)}\n\n"
        f"MISSING INFO FLAGS FROM DECK: {claims.missing_info}"
    )

    response = client.messages.create(
        model="claude-sonnet-4-6",
        temperature=0,
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    data = json.loads(raw)

    # thesis_interpretation is extra context — store in action_reasoning if present
    interpretation = data.pop("thesis_interpretation", "")
    if interpretation and not data.get("action_reasoning"):
        data["action_reasoning"] = interpretation

    return ThesisFitResult(**data)
