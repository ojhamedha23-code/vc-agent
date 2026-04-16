from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel


# ── Agent 1: Claim Extractor ─────────────────────────────────────────────────

class MarketClaims(BaseModel):
    tam: Optional[str] = None
    tam_slide: Optional[int] = None
    problem: Optional[str] = None
    competition: List[str] = []
    tailwinds: List[str] = []
    headwinds: List[str] = []

class ProductClaims(BaseModel):
    solution: Optional[str] = None
    moat: Optional[str] = None
    how_it_works: Optional[str] = None

class BusinessModelClaims(BaseModel):
    model_type: Optional[str] = None
    pricing: Optional[str] = None
    gtm: Optional[str] = None
    arr: Optional[str] = None
    arr_growth: Optional[str] = None
    num_customers: Optional[str] = None
    gross_margin: Optional[str] = None
    cac: Optional[str] = None
    ltv: Optional[str] = None
    pipeline: Optional[str] = None

class TeamClaims(BaseModel):
    ceo: Optional[str] = None
    cofounders: List[str] = []
    domain_expertise: Optional[bool] = None
    serial_entrepreneur: Optional[bool] = None
    notable_investors: List[str] = []

class InvestmentOffer(BaseModel):
    series: Optional[str] = None
    ask_usd: Optional[str] = None
    post_money_valuation: Optional[str] = None
    use_of_funds: Optional[str] = None
    runway: Optional[str] = None

class ClaimsJSON(BaseModel):
    startup_name: str
    hq_location: Optional[str] = None
    market: MarketClaims = MarketClaims()
    product: ProductClaims = ProductClaims()
    business_model: BusinessModelClaims = BusinessModelClaims()
    team: TeamClaims = TeamClaims()
    investment: InvestmentOffer = InvestmentOffer()
    missing_info: List[str] = []


# ── Agent 2: Fact Checker ────────────────────────────────────────────────────

class ClaimCheck(BaseModel):
    claim: str
    category: Literal["market_size", "traction", "competition", "team", "other"]
    status: Literal["verified", "unverified", "contradicted"]
    source: Optional[str] = None
    source_url: Optional[str] = None
    confidence: Literal["high", "medium", "low"]
    notes: str = ""

class DealBreakerFlags(BaseModel):
    pre_product_pre_revenue: bool = False
    hardware_business_model: bool = False
    d2c_consumer_ecommerce: bool = False

    def any_triggered(self) -> bool:
        return any([
            self.pre_product_pre_revenue,
            self.hardware_business_model,
            self.d2c_consumer_ecommerce,
        ])

class FactCheckResult(BaseModel):
    fact_checks: List[ClaimCheck] = []
    deal_breakers: DealBreakerFlags = DealBreakerFlags()
    red_flags: List[str] = []
    overall_credibility: Literal["high", "medium", "low"] = "low"


# ── Agent 3: Thesis Scorer ───────────────────────────────────────────────────

class DimensionScore(BaseModel):
    score: int   # must be one of 0, 25, 50, 75, 100
    reasoning: str

class BonusPoints(BaseModel):
    renowned_vc_backers: bool = False
    clear_path_to_profitability: bool = False
    repeat_founder: bool = False

    def total(self) -> int:
        return sum([
            self.renowned_vc_backers,
            self.clear_path_to_profitability,
            self.repeat_founder,
        ])

class ThesisFitResult(BaseModel):
    sector_fit: DimensionScore
    geography_fit: DimensionScore
    stage_fit: DimensionScore
    arr_traction_fit: DimensionScore
    overall_fit: float
    confidence: Literal["High", "Medium", "Low"]
    missing_data_points: List[str] = []
    bonus_points: BonusPoints = BonusPoints()
    action: Literal["REVIEW", "PASS", "ARCHIVE"]
    action_reasoning: str = ""


# ── Agent 4: Memo Drafter ────────────────────────────────────────────────────

class InvestmentMemo(BaseModel):
    startup_name: str
    overall_fit: float
    action: Literal["REVIEW", "PASS", "ARCHIVE"]
    confidence: str

    # Section A
    thesis_score_table: str

    # Section B
    deal_breaker_status: str

    # Section C
    bonus_points_summary: str

    # Section D — only for REVIEW
    summary_business: str = ""
    summary_market: str = ""
    summary_unit_econ: str = ""
    summary_traction: str = ""
    summary_product: str = ""
    summary_team: str = ""
    top_3_risks: List[str] = []

    # Section E — only for REVIEW
    reasons_to_invest: List[str] = []
    reasons_to_pass: List[str] = []

    # Section F — only for REVIEW
    founder_questions: List[str] = []
    recommended_next_step: str = ""

    def to_markdown(self) -> str:
        lines = [
            "━" * 60,
            f"INVESTMENT MEMO: {self.startup_name}",
            "━" * 60,
            "",
            f"**Overall Thesis Fit:** {self.overall_fit:.1f}%  |  "
            f"**Action:** {self.action}  |  **Confidence:** {self.confidence}",
            "",
            "## A) THESIS FIT SCORE",
            self.thesis_score_table,
            "",
            "## B) DEAL BREAKER STATUS",
            self.deal_breaker_status,
            "",
            "## C) BONUS POINTS",
            self.bonus_points_summary,
            "",
        ]

        if self.action == "REVIEW":
            lines += [
                "## D) STARTUP SUMMARY & RISKS",
                f"**Business:** {self.summary_business}",
                "",
                f"**Market:** {self.summary_market}",
                "",
                f"**Unit Economics:** {self.summary_unit_econ}",
                "",
                f"**Traction:** {self.summary_traction}",
                "",
                f"**Product / Differentiation:** {self.summary_product}",
                "",
                f"**Team:** {self.summary_team}",
                "",
                "**Top 3 Risks Identified:**",
            ]
            for i, risk in enumerate(self.top_3_risks, 1):
                lines.append(f"{i}. {risk}")

            lines += [
                "",
                "## E) INVESTMENT CASE",
                "**3 Reasons to Invest:**",
            ]
            for i, r in enumerate(self.reasons_to_invest, 1):
                lines.append(f"{i}. {r}")

            lines += ["", "**3 Reasons to Pass:**"]
            for i, r in enumerate(self.reasons_to_pass, 1):
                lines.append(f"{i}. {r}")

            lines += [
                "",
                "## F) NEXT STEPS",
                f"**Action:** {self.recommended_next_step}",
                "",
                "**5 Questions for Founder Meeting:**",
            ]
            for i, q in enumerate(self.founder_questions, 1):
                lines.append(f"{i}. {q}")

        lines += ["", "━" * 60]
        return "\n".join(lines)


# ── Pipeline Result (full transparency) ─────────────────────────────────────

class SearchLog(BaseModel):
    query: str
    results: List[Dict[str, Any]] = []   # [{title, url, content, score}]


class PipelineResult(BaseModel):
    """Holds every intermediate output from the pipeline for full transparency."""
    # Raw slide text
    slide_texts: List[Dict[str, Any]] = []   # [{slide_num, text, is_image_based}]

    # Agent outputs
    claims: Optional[ClaimsJSON] = None
    fact_result: Optional[FactCheckResult] = None
    thesis_result: Optional[ThesisFitResult] = None
    memo: Optional[InvestmentMemo] = None

    # Tavily search log
    search_logs: List[SearchLog] = []

    # Error tracking per agent
    errors: Dict[str, str] = {}           # {"agent_1": "error msg", ...}
