"""
Pipeline Orchestrator — returns PipelineResult with ALL intermediate outputs.

Input modes:
  run_pipeline()         → local PDF file path
  run_pipeline_url()     → direct PDF URL
  run_pipeline_images()  → list of image bytes (screenshots)
  run_pipeline_pptx()    → local PPTX file path
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Callable, List, Optional, Tuple, Union

import anthropic
from dotenv import load_dotenv
from tavily import TavilyClient

import agents.extractor as extractor
import agents.fact_checker as fact_checker
import agents.memo_drafter as memo_drafter
import agents.thesis_scorer as thesis_scorer
from schemas.models import (
    ClaimsJSON, FactCheckResult, InvestmentMemo,
    PipelineResult, SearchLog, ThesisFitResult,
)
from tools.pdf_parser import (
    parse_deck, parse_from_images, parse_from_pptx, parse_from_url,
)

load_dotenv()

DEFAULT_THESIS_TEXT_PATH = Path(__file__).parent / "config" / "thesis_text.txt"


def load_thesis_text(thesis_text_path: Union[str, Path] = DEFAULT_THESIS_TEXT_PATH) -> str:
    """Load the fund's investment thesis as plain free text."""
    return Path(thesis_text_path).read_text().strip()


def _make_clients() -> Tuple[anthropic.Anthropic, TavilyClient]:
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    tavily_key = os.getenv("TAVILY_API_KEY")
    if not anthropic_key:
        raise ValueError("ANTHROPIC_API_KEY not set in .env")
    if not tavily_key:
        raise ValueError("TAVILY_API_KEY not set in .env")
    return anthropic.Anthropic(api_key=anthropic_key), TavilyClient(api_key=tavily_key)


async def _run_parallel(
    claims: ClaimsJSON,
    thesis_text: str,
    anthropic_client: anthropic.Anthropic,
    tavily_client: TavilyClient,
) -> Tuple[FactCheckResult, ThesisFitResult, List[SearchLog]]:
    loop = asyncio.get_event_loop()

    fact_task = loop.run_in_executor(
        None, fact_checker.run, claims, anthropic_client, tavily_client
    )

    placeholder_fact = FactCheckResult()
    thesis_task = loop.run_in_executor(
        None, thesis_scorer.run, claims, placeholder_fact, thesis_text, anthropic_client
    )

    (fact_result, search_logs), thesis_result = await asyncio.gather(fact_task, thesis_task)

    # Always enforce decision rules programmatically — never trust Agent 3's action
    if fact_result.deal_breakers.any_triggered():
        if thesis_result.overall_fit >= 75:
            thesis_result.action = "ARCHIVE"
            thesis_result.action_reasoning = (
                "High thesis fit but deal breaker triggered — archive for future opportunities."
            )
        else:
            thesis_result.action = "PASS"
            thesis_result.action_reasoning = (
                "Deal breaker triggered and thesis fit below 75% — pass."
            )
    else:
        # No deal breakers — action is purely based on fit score
        if thesis_result.overall_fit >= 50:
            thesis_result.action = "REVIEW"
        else:
            thesis_result.action = "PASS"

    return fact_result, thesis_result, search_logs


def _run_core(
    slides,
    thesis_text: str,
    anthropic_client: anthropic.Anthropic,
    tavily_client: TavilyClient,
    progress_callback: Optional[Callable],
) -> PipelineResult:
    """Shared core: runs Agents 1→2+3→4, returns full PipelineResult."""
    result = PipelineResult(
        slide_texts=[
            {"slide_num": s.slide_num, "text": s.text, "is_image_based": s.is_image_based}
            for s in slides
        ]
    )

    def _p(msg: str):
        if progress_callback:
            progress_callback(msg)

    # Agent 1
    _p("Agent 1: Extracting claims from deck...")
    try:
        result.claims = extractor.run(slides, anthropic_client)
    except Exception as e:
        result.errors["agent_1"] = str(e)
        _p(f"Agent 1 ERROR: {e}")
        return result

    # Agents 2 + 3 (parallel)
    _p("Agent 2 + 3: Fact-checking & scoring thesis fit (running in parallel)...")
    try:
        fact_result, thesis_result, search_logs = asyncio.run(
            _run_parallel(result.claims, thesis_text, anthropic_client, tavily_client)
        )
        result.fact_result = fact_result
        result.thesis_result = thesis_result
        result.search_logs = search_logs
    except Exception as e:
        result.errors["agent_2_3"] = str(e)
        _p(f"Agent 2/3 ERROR: {e}")
        return result

    # Agent 4
    _p(f"Agent 4: Drafting memo (Action: {thesis_result.action})...")
    try:
        result.memo = memo_drafter.run(
            result.claims, result.fact_result, result.thesis_result, anthropic_client
        )
    except Exception as e:
        result.errors["agent_4"] = str(e)
        _p(f"Agent 4 ERROR: {e}")

    _p("Done.")
    return result


# ── Public entry points ──────────────────────────────────────────────────────

def run_pipeline(
    pdf_path: str,
    thesis_text: str = "",
    progress_callback: Optional[Callable] = None,
) -> PipelineResult:
    def _p(msg):
        if progress_callback: progress_callback(msg)
    anthropic_client, tavily_client = _make_clients()
    if not thesis_text:
        thesis_text = load_thesis_text()
    _p("Parsing pitch deck PDF...")
    slides = parse_deck(pdf_path, anthropic_client)
    return _run_core(slides, thesis_text, anthropic_client, tavily_client, progress_callback)


def run_pipeline_pptx(
    pptx_path: str,
    thesis_text: str = "",
    progress_callback: Optional[Callable] = None,
) -> PipelineResult:
    def _p(msg):
        if progress_callback: progress_callback(msg)
    anthropic_client, tavily_client = _make_clients()
    if not thesis_text:
        thesis_text = load_thesis_text()
    _p("Parsing PPTX pitch deck...")
    slides = parse_from_pptx(pptx_path, anthropic_client)
    return _run_core(slides, thesis_text, anthropic_client, tavily_client, progress_callback)


def run_pipeline_url(
    pdf_url: str,
    thesis_text: str = "",
    progress_callback: Optional[Callable] = None,
) -> PipelineResult:
    def _p(msg):
        if progress_callback: progress_callback(msg)
    anthropic_client, tavily_client = _make_clients()
    if not thesis_text:
        thesis_text = load_thesis_text()
    _p("Downloading PDF from URL...")
    slides = parse_from_url(pdf_url, anthropic_client)
    return _run_core(slides, thesis_text, anthropic_client, tavily_client, progress_callback)


def run_pipeline_images(
    image_bytes_list: List[bytes],
    media_types: List[str],
    thesis_text: str = "",
    progress_callback: Optional[Callable] = None,
) -> PipelineResult:
    def _p(msg):
        if progress_callback: progress_callback(msg)
    anthropic_client, tavily_client = _make_clients()
    if not thesis_text:
        thesis_text = load_thesis_text()
    _p(f"Processing {len(image_bytes_list)} slide image(s) via Claude vision...")
    slides = parse_from_images(image_bytes_list, anthropic_client, media_types)
    return _run_core(slides, thesis_text, anthropic_client, tavily_client, progress_callback)
