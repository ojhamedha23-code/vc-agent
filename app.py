"""
VC Due Diligence Agent — Streamlit UI
"""
import json
import os
import tempfile
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="VC Due Diligence Agent",
    page_icon="🔍",
    layout="wide",
)

THESIS_TEXT_PATH = Path(__file__).parent / "config" / "thesis_text.txt"
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


# ── Helpers ──────────────────────────────────────────────────────────────────

def load_thesis_text() -> str:
    if THESIS_TEXT_PATH.exists():
        return THESIS_TEXT_PATH.read_text().strip()
    return ""


def save_thesis_text(text: str):
    THESIS_TEXT_PATH.write_text(text)


def action_badge(action: str) -> str:
    return {"REVIEW": "🟢 REVIEW", "ARCHIVE": "🟡 ARCHIVE", "PASS": "🔴 PASS"}.get(action, action)


PROGRESS_STEPS = {
    "Parsing pitch deck PDF...": 8,
    "Parsing PPTX pitch deck...": 8,
    "Downloading PDF from URL...": 8,
    "Processing": 8,
    "Agent 1: Extracting claims from deck...": 30,
    "Agent 2 + 3: Fact-checking & scoring thesis fit (running in parallel)...": 70,
    "Agent 4: Drafting memo": 90,
    "Done.": 100,
}


def _make_progress_callback():
    bar = st.progress(0, text="Starting pipeline...")

    def update(msg: str):
        for key, pct in PROGRESS_STEPS.items():
            if msg.startswith(key):
                bar.progress(pct, text=msg)
                return
        bar.progress(50, text=msg)

    return update


def _save_and_store(result, deck_name: str):
    st.session_state["latest_result"] = result
    st.session_state["latest_filename"] = deck_name
    if result.memo:
        out = OUTPUT_DIR / f"{deck_name}_memo.md"
        out.write_text(result.memo.to_markdown())


# ── Sidebar: Thesis Setup ────────────────────────────────────────────────────

with st.sidebar:
    st.title("⚙️ Fund Thesis")

    saved_thesis = load_thesis_text()
    is_placeholder = saved_thesis.startswith("Paste your fund") or not saved_thesis

    thesis_input = st.text_area(
        "Paste your investment thesis here",
        value="" if is_placeholder else saved_thesis,
        height=220,
        placeholder=(
            "Example: Our fund focuses on early-stage B2B SaaS companies in Southeast Asia "
            "with at least $250K ARR. We back exceptional founding teams solving real enterprise "
            "pain points. Target check size is $500K–$2M at Seed to Series A stage."
        ),
        help="This is the only input Agent 3 uses for scoring. Be as specific as you like — sectors, geographies, stage, check size, what you won't invest in, etc.",
    )

    col_save, col_clear = st.columns(2)
    with col_save:
        if st.button("💾 Save", use_container_width=True):
            if thesis_input.strip():
                save_thesis_text(thesis_input.strip())
                st.success("Thesis saved!")
            else:
                st.warning("Thesis is empty.")
    with col_clear:
        if st.button("🗑️ Clear", use_container_width=True):
            save_thesis_text("")
            st.rerun()

    # Active thesis preview
    active_thesis = thesis_input.strip() if thesis_input.strip() else saved_thesis
    if active_thesis and not active_thesis.startswith("Paste your fund"):
        st.divider()
        st.caption("**Active thesis (first 200 chars):**")
        st.caption(f"_{active_thesis[:200]}{'...' if len(active_thesis) > 200 else ''}_")
    else:
        st.divider()
        st.warning("⚠️ No thesis set. Add one above before running an analysis.")

    st.divider()
    anthropic_ok = bool(os.getenv("ANTHROPIC_API_KEY"))
    tavily_ok = bool(os.getenv("TAVILY_API_KEY"))
    st.caption(f"{'✅' if anthropic_ok else '❌'} Anthropic API")
    st.caption(f"{'✅' if tavily_ok else '❌'} Tavily API")


# ── Main UI ──────────────────────────────────────────────────────────────────

st.title("🔍 VC Due Diligence Agent")
st.caption("Upload a pitch deck → structured investment memo in minutes.")

tab_run, tab_results, tab_agents, tab_history = st.tabs([
    "📤 Screen a Deck",
    "📄 Investment Memo",
    "🔬 Agent Transparency",
    "📁 History",
])


# ── Tab 1: Screen a Deck ─────────────────────────────────────────────────────

with tab_run:
    keys_ok = anthropic_ok and tavily_ok
    active_thesis = thesis_input.strip() if thesis_input.strip() else load_thesis_text()
    thesis_ok = bool(active_thesis and not active_thesis.startswith("Paste your fund"))

    if not keys_ok:
        st.error("Missing API keys. Add ANTHROPIC_API_KEY and TAVILY_API_KEY to your .env file.")
    if not thesis_ok:
        st.warning("⚠️ No thesis set. Paste your fund thesis in the sidebar before running.")

    can_run = keys_ok and thesis_ok

    input_mode = st.radio(
        "Input method",
        ["📄 Upload PDF", "📊 Upload PPTX", "🔗 Paste PDF URL", "🖼️ Upload Slide Screenshots"],
        horizontal=True,
    )

    result = None
    deck_name = "deck"

    # ── PDF Upload ──────────────────────────────────────────────────────────
    if input_mode == "📄 Upload PDF":
        f = st.file_uploader("Drop a PDF pitch deck", type=["pdf"])
        if f:
            st.info(f"**{f.name}** — {f.size / 1024:.0f} KB")
            deck_name = f.name.replace(".pdf", "")
            if st.button("🚀 Run Analysis", type="primary", disabled=not can_run):
                from pipeline import run_pipeline
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                    tmp.write(f.getbuffer()); tmp_path = tmp.name
                try:
                    result = run_pipeline(tmp_path, active_thesis, _make_progress_callback())
                except Exception as e:
                    st.error(f"Error: {e}"); raise
                finally:
                    os.unlink(tmp_path)

    # ── PPTX Upload ─────────────────────────────────────────────────────────
    elif input_mode == "📊 Upload PPTX":
        f = st.file_uploader("Drop a PPTX pitch deck", type=["pptx"])
        if f:
            st.info(f"**{f.name}** — {f.size / 1024:.0f} KB")
            deck_name = f.name.replace(".pptx", "")
            if st.button("🚀 Run Analysis", type="primary", disabled=not can_run):
                from pipeline import run_pipeline_pptx
                with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as tmp:
                    tmp.write(f.getbuffer()); tmp_path = tmp.name
                try:
                    result = run_pipeline_pptx(tmp_path, active_thesis, _make_progress_callback())
                except Exception as e:
                    st.error(f"Error: {e}"); raise
                finally:
                    os.unlink(tmp_path)

    # ── PDF URL ─────────────────────────────────────────────────────────────
    elif input_mode == "🔗 Paste PDF URL":
        st.caption("Paste a direct link to a .pdf file")
        pdf_url = st.text_input("PDF URL", placeholder="https://example.com/deck.pdf")
        if pdf_url:
            deck_name = pdf_url.split("/")[-1].replace(".pdf", "") or "url-deck"
            if st.button("🚀 Download & Analyse", type="primary", disabled=not can_run):
                from pipeline import run_pipeline_url
                try:
                    result = run_pipeline_url(pdf_url, active_thesis, _make_progress_callback())
                except ValueError as e:
                    st.error(str(e))
                except Exception as e:
                    st.error(f"Error: {e}"); raise

    # ── Screenshot Upload ───────────────────────────────────────────────────
    elif input_mode == "🖼️ Upload Slide Screenshots":
        st.caption("Screenshot each slide (`Cmd+Shift+4` on Mac) and upload all PNGs/JPGs here. Name them 01.png, 02.png... to keep order.")
        imgs = st.file_uploader("Upload slide screenshots", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
        if imgs:
            imgs = sorted(imgs, key=lambda x: x.name)
            st.info(f"**{len(imgs)} slide(s)** — {', '.join(i.name for i in imgs[:4])}{'...' if len(imgs) > 4 else ''}")
            with st.expander("Preview slides"):
                cols = st.columns(min(len(imgs), 4))
                for i, (col, img) in enumerate(zip(cols, imgs)):
                    col.image(img, caption=f"Slide {i+1}", use_column_width=True)
            deck_name = "screenshot-deck"
            if st.button("🚀 Run Analysis on Screenshots", type="primary", disabled=not can_run):
                from pipeline import run_pipeline_images
                img_bytes = [i.read() for i in imgs]
                media_types = ["image/jpeg" if i.name.lower().endswith((".jpg", ".jpeg")) else "image/png" for i in imgs]
                try:
                    result = run_pipeline_images(img_bytes, media_types, active_thesis, _make_progress_callback())
                except Exception as e:
                    st.error(f"Error: {e}"); raise

    # ── On success ──────────────────────────────────────────────────────────
    if result is not None:
        if result.errors:
            for agent, err in result.errors.items():
                st.error(f"**{agent} failed:** {err}")

        _save_and_store(result, deck_name)

        if result.memo:
            st.success(f"{action_badge(result.memo.action)} — Analysis complete!")
            st.info("👉 Switch to **Investment Memo** and **Agent Transparency** tabs to see results.")
        elif result.claims:
            st.warning("Pipeline partially completed. Check the **Agent Transparency** tab for errors.")
        else:
            st.error("Pipeline failed at claim extraction. Check the **Agent Transparency** tab.")


# ── Tab 2: Investment Memo ────────────────────────────────────────────────────

with tab_results:
    if "latest_result" not in st.session_state or st.session_state["latest_result"].memo is None:
        st.info("No memo yet — run an analysis first.")
    else:
        result = st.session_state["latest_result"]
        memo = result.memo

        # Top metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Startup", memo.startup_name)
        col2.metric("Thesis Fit", f"{memo.overall_fit:.1f}%")
        col3.metric("Action", action_badge(memo.action))
        col4.metric("Confidence", memo.confidence)

        if memo.action != "REVIEW":
            st.warning(
                f"**Action is {memo.action}** — Full memo sections (Summary, Investment Case, Next Steps) "
                f"are only generated for REVIEW decks. See the scoring breakdown below for the reason."
            )

        st.divider()

        sec_tabs = st.tabs(["A) Score", "B) Deal Breakers", "C) Bonus", "D) Summary", "E) Case", "F) Next Steps", "📋 Full Memo"])

        with sec_tabs[0]:
            st.subheader("Thesis Fit Score")
            st.markdown(memo.thesis_score_table)
            if result.thesis_result:
                tr = result.thesis_result
                st.divider()
                st.markdown(f"**Action reasoning:** {tr.action_reasoning}")
                if tr.missing_data_points:
                    st.markdown(f"**Missing data that lowered confidence:** {', '.join(tr.missing_data_points)}")

        with sec_tabs[1]:
            st.subheader("Deal Breaker Status")
            st.markdown(memo.deal_breaker_status)

        with sec_tabs[2]:
            st.subheader("Bonus Points")
            st.markdown(memo.bonus_points_summary)

        with sec_tabs[3]:
            if memo.action == "REVIEW" and memo.summary_business:
                for label, text in [
                    ("📦 Business", memo.summary_business),
                    ("📊 Market", memo.summary_market),
                    ("💰 Unit Economics", memo.summary_unit_econ),
                    ("📈 Traction", memo.summary_traction),
                    ("🛡️ Product / Differentiation", memo.summary_product),
                    ("👥 Team", memo.summary_team),
                ]:
                    st.markdown(f"**{label}:** {text}")
                    st.divider()
                if memo.top_3_risks:
                    st.subheader("⚠️ Top 3 Risks")
                    for i, r in enumerate(memo.top_3_risks, 1):
                        st.markdown(f"{i}. {r}")
            else:
                st.info(f"Summary only available for REVIEW decks. This deck: **{memo.action}**")

        with sec_tabs[4]:
            if memo.action == "REVIEW" and memo.reasons_to_invest:
                c1, c2 = st.columns(2)
                with c1:
                    st.subheader("✅ 3 Reasons to Invest")
                    for i, r in enumerate(memo.reasons_to_invest, 1): st.markdown(f"{i}. {r}")
                with c2:
                    st.subheader("❌ 3 Reasons to Pass")
                    for i, r in enumerate(memo.reasons_to_pass, 1): st.markdown(f"{i}. {r}")
            else:
                st.info(f"Investment case only for REVIEW decks. This deck: **{memo.action}**")

        with sec_tabs[5]:
            if memo.action == "REVIEW" and memo.recommended_next_step:
                st.info(f"**Next Step:** {memo.recommended_next_step}")
                st.subheader("5 Questions for Founder Meeting")
                for i, q in enumerate(memo.founder_questions, 1): st.markdown(f"{i}. {q}")
            else:
                st.info(f"Next steps only for REVIEW decks. This deck: **{memo.action}**")

        with sec_tabs[6]:
            st.markdown(memo.to_markdown())
            st.download_button("⬇️ Download Memo (.md)", memo.to_markdown(),
                               f"{memo.startup_name}_memo.md", "text/markdown")


# ── Tab 3: Agent Transparency ─────────────────────────────────────────────────

with tab_agents:
    if "latest_result" not in st.session_state:
        st.info("No run yet — upload a deck to see agent outputs here.")
    else:
        result = st.session_state["latest_result"]
        st.subheader("🔬 Full Agent Transparency")
        st.caption("Everything each agent did, saw, and decided.")

        agent_tabs = st.tabs([
            "📝 Parsed Slides",
            "🤖 Agent 1: Claims",
            "🌐 Agent 2: Fact Check + Tavily",
            "🎯 Agent 3: Thesis Score",
            "✍️ Agent 4: Memo",
            "⚠️ Errors",
        ])

        # Parsed slides
        with agent_tabs[0]:
            st.markdown("**Raw text extracted from each slide before any AI processing.**")
            if result.slide_texts:
                for s in result.slide_texts:
                    label = f"Slide {s['slide_num']}" + (" 🖼️ [vision]" if s.get("is_image_based") else "")
                    with st.expander(label):
                        st.text(s["text"] or "[empty]")
            else:
                st.warning("No slide text available.")

        # Agent 1
        with agent_tabs[1]:
            st.markdown("**Agent 1** extracted these structured claims from the deck. This is the input to Agents 2 and 3.")
            if result.claims:
                st.json(result.claims.model_dump())
            else:
                st.error("Agent 1 did not produce output." + (f" Error: {result.errors.get('agent_1', 'unknown')}" if result.errors.get('agent_1') else ""))

        # Agent 2 + Tavily
        with agent_tabs[2]:
            col_a, col_b = st.columns([1, 1])

            with col_a:
                st.markdown("**🌐 Tavily Web Searches**")
                st.caption(f"Searches run: {len(result.search_logs)}")
                if result.search_logs:
                    for log in result.search_logs:
                        with st.expander(f"🔍 \"{log.query}\""):
                            if log.results:
                                for r in log.results:
                                    st.markdown(f"**[{r['title']}]({r['url']})**")
                                    st.caption(r["content"][:300] + "..." if len(r["content"]) > 300 else r["content"])
                                    st.markdown(f"*Relevance score: {r.get('score', 'n/a')}*")
                                    st.divider()
                            else:
                                st.warning("No results found from trusted sources for this query.")
                else:
                    st.warning("No Tavily searches were run.")

            with col_b:
                st.markdown("**🤖 Agent 2 Fact-Check Output**")
                if result.fact_result:
                    # Deal breakers
                    db = result.fact_result.deal_breakers
                    st.markdown("**Deal Breakers Detected:**")
                    st.markdown(f"- Pre-product/pre-revenue: {'🔴 YES' if db.pre_product_pre_revenue else '✅ No'}")
                    st.markdown(f"- Hardware model: {'🔴 YES' if db.hardware_business_model else '✅ No'}")
                    st.markdown(f"- D2C/Consumer: {'🔴 YES' if db.d2c_consumer_ecommerce else '✅ No'}")

                    st.divider()
                    st.markdown(f"**Overall Credibility:** {result.fact_result.overall_credibility.upper()}")

                    if result.fact_result.red_flags:
                        st.markdown("**Red Flags:**")
                        for flag in result.fact_result.red_flags:
                            st.markdown(f"- ⚠️ {flag}")

                    st.divider()
                    st.markdown("**Claim-by-Claim Checks:**")
                    for fc in result.fact_result.fact_checks:
                        icon = {"verified": "✅", "unverified": "❓", "contradicted": "🔴"}.get(fc.status, "❓")
                        with st.expander(f"{icon} {fc.claim[:80]}..."):
                            st.markdown(f"**Status:** {fc.status.upper()}")
                            st.markdown(f"**Category:** {fc.category}")
                            st.markdown(f"**Confidence:** {fc.confidence}")
                            if fc.source_url:
                                st.markdown(f"**Source:** [{fc.source}]({fc.source_url})")
                            if fc.notes:
                                st.markdown(f"**Notes:** {fc.notes}")
                else:
                    st.error("Agent 2 did not produce output." + (f" Error: {result.errors.get('agent_2_3', 'unknown')}" if result.errors.get('agent_2_3') else ""))

        # Agent 3
        with agent_tabs[3]:
            st.markdown("**Agent 3** scored the startup against the fund thesis using 0/25/50/75/100 discrete anchors.")
            if result.thesis_result:
                tr = result.thesis_result

                # Score breakdown
                dims = [
                    ("Sector Fit", tr.sector_fit, "40%"),
                    ("Geography Fit", tr.geography_fit, "25%"),
                    ("Stage Fit", tr.stage_fit, "10%"),
                    ("ARR / Traction Fit", tr.arr_traction_fit, "25%"),
                ]
                for name, dim, weight in dims:
                    with st.expander(f"**{name}** — Score: {dim.score}/100 (weight {weight})"):
                        st.progress(dim.score / 100)
                        st.markdown(f"**Reasoning:** {dim.reasoning}")

                st.divider()
                col1, col2, col3 = st.columns(3)
                col1.metric("Overall Fit", f"{tr.overall_fit:.1f}%")
                col2.metric("Confidence", tr.confidence)
                col3.metric("Action", action_badge(tr.action))

                st.markdown(f"**Action reasoning:** {tr.action_reasoning}")

                if tr.missing_data_points:
                    st.markdown("**Missing data flagged:**")
                    for m in tr.missing_data_points:
                        st.markdown(f"- ❓ {m}")

                st.divider()
                bp = tr.bonus_points
                st.markdown("**Bonus Points:**")
                st.markdown(f"- Renowned VC backers: {'✅' if bp.renowned_vc_backers else '❌'}")
                st.markdown(f"- Path to profitability: {'✅' if bp.clear_path_to_profitability else '❌'}")
                st.markdown(f"- Repeat founder: {'✅' if bp.repeat_founder else '❌'}")
                st.markdown(f"**Total: {bp.total()} / 3 bonus points**")
            else:
                st.error("Agent 3 did not produce output.")

        # Agent 4
        with agent_tabs[4]:
            st.markdown("**Agent 4** synthesized all prior outputs into the final memo using Claude Opus 4.6.")
            if result.memo:
                st.success(f"Memo generated successfully. Action: **{result.memo.action}**")
                st.markdown("Full memo output is in the **Investment Memo** tab.")
            else:
                st.error("Agent 4 did not produce a memo." + (f" Error: {result.errors.get('agent_4', 'unknown')}" if result.errors.get('agent_4') else ""))

        # Errors
        with agent_tabs[5]:
            if result.errors:
                for agent, err in result.errors.items():
                    st.error(f"**{agent}:** {err}")
            else:
                st.success("No errors — all agents completed successfully.")


# ── Tab 4: History ────────────────────────────────────────────────────────────

with tab_history:
    md_files = list(OUTPUT_DIR.glob("*.md"))
    if not md_files:
        st.info("No memos saved yet.")
    else:
        st.subheader(f"{len(md_files)} memo(s) on file")
        for f in sorted(md_files, key=lambda x: x.stat().st_mtime, reverse=True):
            with st.expander(f.stem):
                st.markdown(f.read_text())
                st.download_button("⬇️ Download", f.read_text(), f.name, key=str(f))
