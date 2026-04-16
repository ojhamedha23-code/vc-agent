"""
Web Search Tool — Tavily wrapper with curated domain whitelist.
Only queries credible, VC-relevant sources to reduce hallucination risk.
"""
from dataclasses import dataclass

from tavily import TavilyClient

TRUSTED_DOMAINS = [
    "crunchbase.com",
    "techcrunch.com",
    "statista.com",
    "bloomberg.com",
    "reuters.com",
    "pitchbook.com",
    "cbinsights.com",
    "dealstreetasia.com",
    "e27.co",
    "techinasia.com",
    "fortune.com",
    "wsj.com",
    "ft.com",
    "sec.gov",
    "marketsandmarkets.com",
    "grandviewresearch.com",
]


@dataclass
class SearchResult:
    title: str
    url: str
    content: str
    score: float


def search(query: str, client: TavilyClient, max_results: int = 3) -> list[SearchResult]:
    """
    Search the web using Tavily, restricted to trusted domains.
    Returns up to max_results results.
    """
    try:
        response = client.search(
            query=query,
            include_domains=TRUSTED_DOMAINS,
            max_results=max_results,
            search_depth="advanced",
        )
        results = []
        for r in response.get("results", []):
            results.append(SearchResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                content=r.get("content", "")[:800],  # cap context length
                score=r.get("score", 0.0),
            ))
        return results
    except Exception:
        return []


def format_results_for_prompt(results: list[SearchResult]) -> str:
    """Format search results as a compact string for LLM context."""
    if not results:
        return "No results found from trusted sources."
    parts = []
    for i, r in enumerate(results, 1):
        parts.append(f"[{i}] {r.title}\nURL: {r.url}\n{r.content}")
    return "\n\n".join(parts)
