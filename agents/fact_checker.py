"""
Agent 2: Fact Checker / Red Flag Detector
Cross-references pitch deck claims against whitelisted web sources.
Runs in parallel with Agent 3.
Returns both FactCheckResult and a list of SearchLogs for transparency.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Tuple

import anthropic
from tavily import TavilyClient

from schemas.models import ClaimsJSON, FactCheckResult, SearchLog
from tools.web_search import format_results_for_prompt, search

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "fact_checker.txt"
SYSTEM_PROMPT = PROMPT_PATH.read_text()


def _build_search_queries(claims: ClaimsJSON) -> List[str]:
    queries = []
    if claims.market.tam:
        queries.append(f"{claims.startup_name} market size TAM {claims.market.tam}")
    if claims.market.competition:
        comp = claims.market.competition[0]
        queries.append(f"{comp} startup funding crunchbase")
    if claims.startup_name:
        queries.append(f"{claims.startup_name} startup news funding")
    # Always search the market category for TAM verification
    if claims.product.solution:
        queries.append(f"{claims.startup_name} industry market size forecast")
    return queries


def run(
    claims: ClaimsJSON,
    anthropic_client: anthropic.Anthropic,
    tavily_client: TavilyClient,
) -> Tuple[FactCheckResult, List[SearchLog]]:
    """Returns (FactCheckResult, search_logs) for full transparency."""
    queries = _build_search_queries(claims)
    search_logs: List[SearchLog] = []
    all_results = []

    for q in queries:
        results = search(q, tavily_client)
        search_logs.append(SearchLog(
            query=q,
            results=[{"title": r.title, "url": r.url, "content": r.content, "score": r.score}
                     for r in results]
        ))
        all_results.extend(results)

    search_context = format_results_for_prompt(all_results)

    user_content = (
        f"CLAIMS FROM PITCH DECK:\n{claims.model_dump_json(indent=2)}\n\n"
        f"WEB SEARCH RESULTS (trusted sources only):\n{search_context}"
    )

    response = anthropic_client.messages.create(
        model="claude-sonnet-4-6",
        temperature=0,
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
    return FactCheckResult(**data), search_logs
