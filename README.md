# Insiders Den — VC Pitch Screening Agent

A multi-agent AI pipeline that automates the initial pitch deck screening workflow for early-stage VCs, from raw PDF upload to a structured investment memo with a PASS / REVIEW / ARCHIVE decision.

Built as an INSEAD MBA "Generative AI for Business" group project.

## The problem

Early-stage funds screen 2,500 to 5,000 decks a year to make 5 to 10 investments. Most rejections happen in minutes, and the same analyst applies different standards to deck #1 and deck #47 on a Friday afternoon. This pipeline handles Stage 1 screening consistently, so human attention goes to the decks that actually merit it.

## How it works

A VC analyst uploads a pitch deck PDF. The fund's investment thesis is pre-configured (target sectors, geographies, stage, ARR targets, and deal-breaker rules). The pipeline returns a decision and, for promising decks, a full memo.

### The 4-agent pipeline

1. **Claim Extractor** (Claude Sonnet 4.6) reads every slide and extracts structured data: TAM, ARR, team, stage, geography, product, traction. Flags missing or ambiguous fields. Outputs `ClaimsJSON`.
2. **Fact Checker** (Claude Sonnet 4.6, parallel) validates claims against whitelisted trusted sources via Tavily and assigns each a status: `verified`, `contradicted`, `unverified`, `not_found`. Also detects the fund's hard deal-breakers. Holds veto power over the Thesis Scorer.
3. **Thesis Scorer** (Claude Sonnet 4.6, parallel) scores the deck against the fund thesis across Sector Fit, Geography Fit, Stage Fit, and Financial Traction. Produces a preliminary decision.
4. **Memo Drafter** (Claude Opus 4.6) fires only on a REVIEW decision, synthesizes all prior outputs, and writes a structured investment memo.

A post-processing Decision Engine applies the Fact Checker's deal-breaker veto to the Thesis Scorer's output to produce the final PASS / REVIEW / ARCHIVE decision.

## Tech stack

| Layer      | Tool              | Hosting       |
| ---------- | ----------------- | ------------- |
| Frontend   | Next.js           | Vercel        |
| Backend    | FastAPI (Python)  | Render        |
| Database   | PostgreSQL        | Supabase      |
| Agents 1-3 | Claude Sonnet 4.6 | Anthropic API |
| Agent 4    | Claude Opus 4.6   | Anthropic API |
| Web search | Tavily API        |               |
| Email      | Resend API        |               |

## Notable engineering decisions

- **Two-pass PDF parser.** Most decks are Keynote or Figma exports with no extractable text. The parser tries `pdfplumber` first; slides returning under 50 characters are routed to Claude's Vision API to be read visually.
- **Deterministic output.** `temperature=0` across all agents, plus file-hash deduplication so the same deck returns a cached result instead of re-running.
- **Cost control.** The expensive memo model runs only on decks that pass screening, not on every upload.

## Repository structure

```
agents/      Agent definitions
backend/     FastAPI service
config/      Fund thesis and deal-breaker rules
frontend/    Next.js app
prompts/     Agent system prompts
schemas/     Structured output schemas
tools/       Tavily, Resend, and parser utilities
app.py       Entry point
pipeline.py  Orchestration
rag.py       Retrieval logic
```

## Running locally

1. Copy `.env.example` to `.env` and add your API keys (Anthropic, Tavily, Resend, Supabase).
2. Install dependencies: `pip install -r requirements.txt`
3. Start the backend: `python app.py`
4. Start the frontend from `frontend/` per its own README.

## Live demo

[insidersden.vercel.app](https://insidersden.vercel.app) — full case study at [medhaojha.com/case-studies/vc-agent](https://medhaojha.com/case-studies/vc-agent).
