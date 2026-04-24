"use client"
import { useEffect, useRef, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { useAuth } from "@clerk/nextjs"
import {
  ArrowLeft, CheckCircle2, XCircle, AlertCircle,
  ChevronDown, ChevronUp, Loader2, ExternalLink, Trash2, AlertTriangle
} from "lucide-react"
import { useApi } from "@/hooks/useApi"
import { useRole } from "@/hooks/useRole"
import { DealDetail, DimensionScore } from "@/types"
import { ScoreRing } from "@/components/ScoreRing"
import { ActionBadge } from "@/components/ActionBadge"
import { cn, scoreLabel, fitBarColor, fitColor, formatDate } from "@/lib/utils"

// ── Mini-TOC sections ─────────────────────────────────────────────────────────
const SECTIONS = [
  { id: "score", label: "Score" },
  { id: "breakers", label: "Breakers" },
  { id: "bonus", label: "Bonus" },
  { id: "summary", label: "Summary" },
  { id: "case", label: "Case" },
  { id: "nextsteps", label: "Next Steps" },
]

function scrollTo(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" })
}

// ── Sub-components ────────────────────────────────────────────────────────────
function DimBar({ label, dim, weight }: { label: string; dim: DimensionScore; weight: string }) {
  return (
    <div className="space-y-1" title={dim.reasoning}>
      <div className="flex items-center justify-between text-xs">
        <span style={{ color: "var(--text-2)" }} className="font-medium">{label}</span>
        <div className="flex items-center gap-2">
          <span style={{ color: "var(--text-3)" }}>{weight}</span>
          <span className={cn("font-semibold tabular-nums", fitColor(dim.score))}>{dim.score}</span>
        </div>
      </div>
      <div className="h-1.5 rounded-full overflow-hidden" style={{ background: "rgba(255,255,255,0.07)" }}>
        <div className={cn("h-full rounded-full transition-all", fitBarColor(dim.score))} style={{ width: `${dim.score}%` }} />
      </div>
    </div>
  )
}

function BoolRow({ label, value }: { label: string; value: boolean }) {
  return (
    <div className="flex items-center gap-2 text-xs">
      {value
        ? <XCircle size={13} className="text-red-500 shrink-0" />
        : <CheckCircle2 size={13} className="text-emerald-500 shrink-0" />}
      <span style={{ color: value ? "#f87171" : "var(--text-2)" }}>{label}</span>
    </div>
  )
}

function BonusRow({ label, value }: { label: string; value: boolean }) {
  return (
    <div className="flex items-center gap-2 text-xs">
      {value
        ? <CheckCircle2 size={13} className="text-emerald-500 shrink-0" />
        : <XCircle size={13} className="shrink-0" style={{ color: "var(--text-3)" }} />}
      <span style={{ color: value ? "var(--text-1)" : "var(--text-3)" }}>{label}</span>
    </div>
  )
}

function Accordion({ title, children }: { title: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="rounded-lg overflow-hidden" style={{ border: "1px solid var(--border)" }}>
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-3 text-sm font-medium transition-colors"
        style={{ background: "var(--bg)", color: "var(--text-2)" }}
        onMouseEnter={e => (e.currentTarget.style.background = "var(--bg-hover)")}
        onMouseLeave={e => (e.currentTarget.style.background = "var(--bg)")}
      >
        {title}
        {open ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
      </button>
      {open && (
        <div className="px-4 py-4" style={{ background: "var(--bg-card)" }}>
          {children}
        </div>
      )}
    </div>
  )
}

function CredBadge({ status }: { status: string }) {
  const map: Record<string, { style: React.CSSProperties; label: string }> = {
    verified:     { style: { background: "rgba(16,185,129,0.12)",  color: "#34d399", border: "1px solid rgba(16,185,129,0.25)" }, label: "verified" },
    contradicted: { style: { background: "rgba(239,68,68,0.12)",   color: "#f87171", border: "1px solid rgba(239,68,68,0.25)"  }, label: "contradicted" },
    unverified:   { style: { background: "rgba(251,191,36,0.1)",   color: "#fbbf24", border: "1px solid rgba(251,191,36,0.25)" }, label: "unverified" },
    not_found:    { style: { background: "rgba(255,255,255,0.05)", color: "var(--text-3)", border: "1px solid var(--border)"   }, label: "not found" },
  }
  const entry = map[status] ?? map.not_found
  return (
    <span className="text-xs px-2 py-0.5 rounded-full font-medium shrink-0" style={entry.style}>
      {entry.label}
    </span>
  )
}

function SectionHeader({ title }: { title: string }) {
  return (
    <div className="mb-4">
      <h3 className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-2)" }}>{title}</h3>
      <hr className="mt-2" style={{ borderColor: "var(--border)" }} />
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function DealPage() {
  const api = useApi()
  const { can } = useRole()
  const { isLoaded, isSignedIn } = useAuth()
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const [deal, setDeal] = useState<DealDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [deleting, setDeleting] = useState(false)
  const [activeSection, setActiveSection] = useState("score")
  const rightPanelRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (isLoaded && isSignedIn) {
      api.getDeal(id).then(setDeal).finally(() => setLoading(false))
    }
  }, [id, isLoaded, isSignedIn])

  // Track active section on scroll
  useEffect(() => {
    const panel = rightPanelRef.current
    if (!panel) return
    const handler = () => {
      for (const { id: sid } of [...SECTIONS].reverse()) {
        const el = document.getElementById(sid)
        if (el && el.getBoundingClientRect().top <= 120) {
          setActiveSection(sid)
          break
        }
      }
    }
    panel.addEventListener("scroll", handler)
    return () => panel.removeEventListener("scroll", handler)
  }, [deal])

  async function handleDelete() {
    if (!confirm("Delete this deal? This cannot be undone.")) return
    setDeleting(true)
    await api.deleteDeal(id)
    router.push("/")
  }

  if (loading) return (
    <div className="flex items-center justify-center h-screen" style={{ color: "var(--text-3)" }}>
      <Loader2 size={28} className="animate-spin" />
    </div>
  )

  if (!deal) return <div className="p-8" style={{ color: "var(--text-2)" }}>Deal not found.</div>

  const t = deal.thesis_json
  const f = deal.fact_json
  const m = deal.memo_json
  const db = f?.deal_breakers
  const showFullMemo = deal.action === "REVIEW"
  const bonusCount = t?.bonus_points
    ? [t.bonus_points.renowned_vc_backers, t.bonus_points.clear_path_to_profitability, t.bonus_points.repeat_founder].filter(Boolean).length
    : 0

  return (
    <div className="flex" style={{ height: "calc(100vh - 57px)" }}>

      {/* ── Left panel ────────────────────────────────────────── */}
      <div className="w-64 shrink-0 flex flex-col overflow-y-auto" style={{ borderRight: "1px solid var(--border)", background: "var(--bg-card)" }}>

        {/* Company header */}
        <div className="px-4 py-3" style={{ borderBottom: "1px solid var(--border)" }}>
          <button
            onClick={() => router.push("/")}
            className="flex items-center gap-1.5 text-xs transition-colors mb-2"
            style={{ color: "var(--text-3)" }}
            onMouseEnter={e => (e.currentTarget.style.color = "var(--accent)")}
            onMouseLeave={e => (e.currentTarget.style.color = "var(--text-3)")}
          >
            <ArrowLeft size={12} /> Back
          </button>
          <div className="flex items-start justify-between gap-2">
            <h1 className="font-bold text-sm leading-snug" style={{ color: "var(--text-1)" }}>{deal.company}</h1>
            <ActionBadge action={deal.action} />
          </div>
          {deal.deck_name && (
            <p className="text-xs mt-0.5 truncate" style={{ color: "var(--text-3)" }} title={deal.deck_name}>{deal.deck_name}</p>
          )}
          <p className="text-xs mt-0.5" style={{ color: "var(--text-3)" }}>{formatDate(deal.created_at)}</p>
        </div>

        {/* Score ring */}
        <div className="flex flex-col items-center py-4 gap-1.5" style={{ borderBottom: "1px solid var(--border)" }}>
          <ScoreRing pct={deal.fit_pct} size={88} />
          <p className="text-xs font-medium" style={{ color: "var(--text-2)" }}>Thesis Fit</p>
          {deal.confidence && <span className="text-xs" style={{ color: "var(--text-3)" }}>{deal.confidence} confidence</span>}
        </div>

        {/* Dimension scores */}
        {t && (
          <div className="px-4 py-3 space-y-3" style={{ borderBottom: "1px solid var(--border)" }}>
            <p className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: "var(--text-3)" }}>Score Breakdown</p>
            <DimBar label="Sector" dim={t.sector_fit} weight="40%" />
            <DimBar label="Geography" dim={t.geography_fit} weight="25%" />
            <DimBar label="ARR / Traction" dim={t.arr_traction_fit} weight="25%" />
            <DimBar label="Stage" dim={t.stage_fit} weight="10%" />
          </div>
        )}

        {/* Deal breakers */}
        {db && (
          <div className="px-4 py-3 space-y-2" style={{ borderBottom: "1px solid var(--border)" }}>
            <p className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: "var(--text-3)" }}>Deal Breakers</p>
            <BoolRow label="Pre-product / pre-revenue" value={db.pre_product_pre_revenue} />
            <BoolRow label="Hardware model" value={db.hardware_business_model} />
            <BoolRow label="D2C / Consumer" value={db.d2c_consumer_ecommerce} />
          </div>
        )}

        {/* Bonus points */}
        {t?.bonus_points && (
          <div className="px-4 py-3 space-y-2" style={{ borderBottom: "1px solid var(--border)" }}>
            <div className="flex items-center justify-between">
              <p className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: "var(--text-3)" }}>Bonus Points</p>
              <span className="text-xs font-bold text-blue-400">{bonusCount}/3</span>
            </div>
            <BonusRow label="Renowned VC backers" value={t.bonus_points.renowned_vc_backers} />
            <BonusRow label="Path to profitability" value={t.bonus_points.clear_path_to_profitability} />
            <BonusRow label="Repeat founder" value={t.bonus_points.repeat_founder} />
          </div>
        )}

        {/* Metadata */}
        <div className="px-4 py-3 space-y-1.5">
          {deal.sector && <div className="flex justify-between text-xs"><span style={{ color: "var(--text-3)" }}>Sector</span><span style={{ color: "var(--text-1)" }} className="font-medium">{deal.sector}</span></div>}
          {deal.stage && <div className="flex justify-between text-xs"><span style={{ color: "var(--text-3)" }}>Stage</span><span style={{ color: "var(--text-1)" }} className="font-medium">{deal.stage}</span></div>}
          {deal.hq && <div className="flex justify-between text-xs"><span style={{ color: "var(--text-3)" }}>HQ</span><span style={{ color: "var(--text-1)" }} className="font-medium">{deal.hq}</span></div>}
        </div>

        {/* Delete — only for Senior Analyst, Partner, Admin */}
        {can("delete") && (
          <div className="px-4 py-3 mt-auto" style={{ borderTop: "1px solid var(--border)" }}>
            <button
              onClick={handleDelete}
              disabled={deleting}
              className="flex items-center gap-1.5 text-xs transition-colors"
              style={{ color: "var(--text-3)" }}
              onMouseEnter={e => (e.currentTarget.style.color = "#f87171")}
              onMouseLeave={e => (e.currentTarget.style.color = "var(--text-3)")}
            >
              <Trash2 size={12} /> Delete deal
            </button>
          </div>
        )}
      </div>

      {/* ── Right panel ───────────────────────────────────────── */}
      <div ref={rightPanelRef} className="flex-1 overflow-y-auto relative" style={{ background: "var(--bg)" }}>
        <div className="max-w-2xl mx-auto px-8 py-8 space-y-10">

          {/* Page title */}
          <div>
            <h2 className="text-xl font-bold" style={{ color: "var(--text-1)" }}>Investment Memo</h2>
            {t?.action_reasoning && (
              <p className="text-sm mt-1 leading-relaxed" style={{ color: "var(--text-2)" }}>{t.action_reasoning}</p>
            )}
          </div>

          {/* ── A) Thesis Fit Score ────────────────────────────── */}
          <section id="score">
            <SectionHeader title="A — Thesis Fit Score" />
            {t ? (
              <div className="space-y-4">
                {/* Score summary row */}
                <div className="flex items-center gap-4 pb-3" style={{ borderBottom: "1px solid var(--border)" }}>
                  <div>
                    <p className="text-2xl font-bold" style={{ color: "var(--text-1)" }}>{t.overall_fit.toFixed(1)}%</p>
                    <p className="text-xs" style={{ color: "var(--text-3)" }}>Overall Thesis Fit</p>
                  </div>
                  <div className="ml-auto text-right">
                    <p className="text-sm font-medium" style={{ color: "var(--text-2)" }}>{t.confidence} confidence</p>
                    {t.missing_data_points?.length > 0 && (
                      <p className="text-xs" style={{ color: "var(--text-3)" }}>{t.missing_data_points.length} data point{t.missing_data_points.length > 1 ? "s" : ""} missing</p>
                    )}
                  </div>
                </div>

                {/* Structured score table */}
                <div className="memo-table">
                  <table>
                    <thead>
                      <tr>
                        <th>Dimension</th>
                        <th>Score</th>
                        <th>Weight</th>
                        <th>Weighted</th>
                      </tr>
                    </thead>
                    <tbody>
                      {[
                        { label: "Sector Fit",        dim: t.sector_fit,      weight: 0.40 },
                        { label: "Geography Fit",     dim: t.geography_fit,   weight: 0.25 },
                        { label: "ARR / Traction Fit",dim: t.arr_traction_fit,weight: 0.25 },
                        { label: "Stage Fit",         dim: t.stage_fit,       weight: 0.10 },
                      ].map(({ label, dim, weight }) => (
                        <tr key={label} title={dim.reasoning}>
                          <td>{label}</td>
                          <td className={cn("font-semibold", fitColor(dim.score))}>{dim.score}</td>
                          <td>{(weight * 100).toFixed(0)}%</td>
                          <td>{(dim.score * weight).toFixed(1)}</td>
                        </tr>
                      ))}
                      <tr style={{ fontWeight: 700 }}>
                        <td>OVERALL</td>
                        <td colSpan={2}></td>
                        <td>{t.overall_fit.toFixed(1)}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                {/* Missing data */}
                {t.missing_data_points && t.missing_data_points.length > 0 && (
                  <div className="rounded-lg px-4 py-3" style={{ background: "rgba(251,191,36,0.08)", border: "1px solid rgba(251,191,36,0.2)" }}>
                    <p className="text-xs font-semibold mb-1" style={{ color: "#fbbf24" }}>Missing data flagged</p>
                    <ul className="text-xs space-y-0.5" style={{ color: "#fcd34d" }}>
                      {t.missing_data_points.map((p, i) => <li key={i}>• {p}</li>)}
                    </ul>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-sm" style={{ color: "var(--text-3)" }}>Score data unavailable.</p>
            )}
          </section>

          {/* ── B) Deal Breaker Status ─────────────────────────── */}
          <section id="breakers">
            <SectionHeader title="B — Deal Breaker Status" />
            {m && <pre className="text-sm whitespace-pre-wrap font-sans leading-relaxed" style={{ color: "var(--text-1)" }}>{m.deal_breaker_status}</pre>}
            {f?.red_flags && f.red_flags.length > 0 && (
              <div className="mt-3 rounded-lg px-4 py-3" style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)" }}>
                <p className="text-xs font-semibold mb-1" style={{ color: "#f87171" }}>Red flags from fact-checking</p>
                <ul className="text-xs space-y-0.5" style={{ color: "#fca5a5" }}>
                  {f.red_flags.map((fl, i) => <li key={i}>• {fl}</li>)}
                </ul>
              </div>
            )}
          </section>

          {/* ── C) Bonus Points ───────────────────────────────── */}
          <section id="bonus">
            <SectionHeader title="C — Bonus Points" />
            {m
              ? <pre className="text-sm whitespace-pre-wrap font-sans leading-relaxed" style={{ color: "var(--text-1)" }}>{m.bonus_points_summary}</pre>
              : <p className="text-sm" style={{ color: "var(--text-3)" }}>Bonus data unavailable.</p>}
          </section>

          {/* PASS / ARCHIVE gate */}
          {!showFullMemo && (
            <div className="rounded-xl p-5 flex gap-3" style={{ background: "rgba(251,191,36,0.08)", border: "1px solid rgba(251,191,36,0.2)" }}>
              <AlertCircle size={18} className="shrink-0 mt-0.5" style={{ color: "#fbbf24" }} />
              <div>
                <p className="text-sm font-semibold" style={{ color: "#fcd34d" }}>Full memo not drafted</p>
                <p className="text-xs mt-1 leading-relaxed" style={{ color: "#fde68a" }}>
                  Sections D–F are only generated for REVIEW decisions. This deal was marked{" "}
                  <strong>{deal.action}</strong>.
                </p>
              </div>
            </div>
          )}

          {showFullMemo && m && (
            <>
              {/* ── D) Summary & Risks ────────────────────────── */}
              <section id="summary">
                <SectionHeader title="D — Summary & Risks" />
                <div className="space-y-5">
                  {[
                    { label: "Business", text: m.summary_business },
                    { label: "Market", text: m.summary_market },
                    { label: "Unit Economics", text: m.summary_unit_econ },
                    { label: "Traction", text: m.summary_traction },
                    { label: "Product / Differentiation", text: m.summary_product },
                    { label: "Team", text: m.summary_team },
                  ].filter(s => s.text).map(({ label, text }) => (
                    <div key={label} className="rounded-lg px-4 py-3" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
                      <p className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--text-3)" }}>{label}</p>
                      <p className="text-sm leading-relaxed" style={{ color: "var(--text-1)" }}>{text}</p>
                    </div>
                  ))}
                  {m.top_3_risks && m.top_3_risks.length > 0 && (
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--text-3)" }}>Top Risks</p>
                      <div className="space-y-2">
                        {m.top_3_risks.map((r, i) => (
                          <div key={i} className="flex gap-2 rounded-lg px-3 py-2" style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.15)" }}>
                            <AlertTriangle size={13} className="shrink-0 mt-0.5" style={{ color: "#f87171" }} />
                            <p className="text-sm" style={{ color: "#fca5a5" }}>{r}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </section>

              {/* ── E) Investment Case ────────────────────────── */}
              <section id="case">
                <SectionHeader title="E — Investment Case" />
                <div className="space-y-5">
                  {m.reasons_to_invest && m.reasons_to_invest.length > 0 && (
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wider mb-2 text-emerald-400">Reasons to Invest</p>
                      <div className="space-y-2">
                        {m.reasons_to_invest.map((r, i) => (
                          <div key={i} className="flex gap-2 rounded-lg px-3 py-2" style={{ background: "rgba(16,185,129,0.08)", border: "1px solid rgba(16,185,129,0.15)" }}>
                            <CheckCircle2 size={13} className="text-emerald-500 shrink-0 mt-0.5" />
                            <p className="text-sm" style={{ color: "#6ee7b7" }}>{r}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {m.reasons_to_pass && m.reasons_to_pass.length > 0 && (
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wider mb-2 text-red-400">Reasons to Pass</p>
                      <div className="space-y-2">
                        {m.reasons_to_pass.map((r, i) => (
                          <div key={i} className="flex gap-2 rounded-lg px-3 py-2" style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.15)" }}>
                            <XCircle size={13} className="text-red-400 shrink-0 mt-0.5" />
                            <p className="text-sm" style={{ color: "#fca5a5" }}>{r}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </section>

              {/* ── F) Next Steps ─────────────────────────────── */}
              <section id="nextsteps">
                <SectionHeader title="F — Next Steps" />
                <div className="space-y-5">
                  {m.recommended_next_step && (
                    <div className="rounded-lg px-4 py-3" style={{ background: "rgba(59,130,246,0.1)", border: "1px solid rgba(59,130,246,0.2)" }}>
                      <p className="text-xs font-semibold mb-1" style={{ color: "#93c5fd" }}>Recommended Action</p>
                      <p className="text-sm" style={{ color: "#bfdbfe" }}>{m.recommended_next_step}</p>
                    </div>
                  )}
                  {m.founder_questions && m.founder_questions.length > 0 && (
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: "var(--text-3)" }}>Questions for Founder Meeting</p>
                      <ol className="space-y-2.5">
                        {m.founder_questions.map((q, i) => (
                          <li key={i} className="flex gap-3 text-sm" style={{ color: "var(--text-1)" }}>
                            <span className="shrink-0 w-5 h-5 rounded-full text-xs flex items-center justify-center font-bold mt-0.5" style={{ background: "rgba(59,130,246,0.15)", color: "#93c5fd" }}>{i + 1}</span>
                            <span className="leading-relaxed">{q}</span>
                          </li>
                        ))}
                      </ol>
                    </div>
                  )}
                </div>
              </section>
            </>
          )}

          {/* ── Agent Transparency ────────────────────────────── */}
          <div className="space-y-2.5 pt-2">
            <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-3)" }}>Agent Transparency</p>

            {deal.slide_texts && deal.slide_texts.length > 0 && (
              <Accordion title={`Parsed Slides (${deal.slide_texts.length})`}>
                <div className="space-y-3 max-h-72 overflow-y-auto">
                  {deal.slide_texts.map(s => (
                    <div key={s.slide_num} className="text-xs">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="font-semibold" style={{ color: "var(--text-2)" }}>Slide {s.slide_num}</span>
                        {s.is_image_based && <span className="px-1.5 py-0.5 rounded text-xs" style={{ background: "rgba(139,92,246,0.15)", color: "#c4b5fd" }}>Vision</span>}
                      </div>
                      <p className="leading-relaxed whitespace-pre-wrap" style={{ color: "var(--text-2)" }}>{s.text.slice(0, 400)}{s.text.length > 400 ? "…" : ""}</p>
                    </div>
                  ))}
                </div>
              </Accordion>
            )}

            {deal.claims_json && (
              <Accordion title="Agent 1 — Extracted Claims">
                <div className="space-y-2 text-xs">
                  {[
                    ["TAM", deal.claims_json.market.tam],
                    ["Problem", deal.claims_json.market.problem],
                    ["ARR", deal.claims_json.business_model.arr],
                    ["Model", deal.claims_json.business_model.model_type],
                    ["CEO", deal.claims_json.team.ceo],
                    ["Ask", deal.claims_json.investment.ask_usd],
                  ].filter(([, v]) => v).map(([k, v]) => (
                    <div key={k as string}><span style={{ color: "var(--text-3)" }}>{k}: </span><span style={{ color: "var(--text-1)" }}>{v as string}</span></div>
                  ))}
                  {deal.claims_json.missing_info.length > 0 && (
                    <div className="rounded px-3 py-2 mt-2" style={{ background: "rgba(251,191,36,0.08)", border: "1px solid rgba(251,191,36,0.15)" }}>
                      <span className="font-semibold" style={{ color: "#fbbf24" }}>Missing: </span>
                      <span style={{ color: "#fcd34d" }}>{deal.claims_json.missing_info.join(", ")}</span>
                    </div>
                  )}
                </div>
              </Accordion>
            )}

            {deal.fact_json && (
              <Accordion title={`Agent 2 — Fact Checks (${deal.fact_json.fact_checks.length})`}>
                <div className="space-y-3">
                  {deal.fact_json.fact_checks.map((fc, i) => (
                    <div key={i} className="rounded-lg p-3 space-y-1.5" style={{ border: "1px solid var(--border)" }}>
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-xs font-medium leading-snug" style={{ color: "var(--text-1)" }}>{fc.claim}</p>
                        <CredBadge status={fc.status} />
                      </div>
                      {fc.notes && <p className="text-xs" style={{ color: "var(--text-2)" }}>{fc.notes}</p>}
                      {fc.source_url && (
                        <a href={fc.source_url} target="_blank" rel="noreferrer" className="flex items-center gap-1 text-xs text-blue-400 hover:underline">
                          <ExternalLink size={10} /> {fc.source ?? fc.source_url}
                        </a>
                      )}
                    </div>
                  ))}
                </div>
              </Accordion>
            )}

            {deal.search_logs && deal.search_logs.length > 0 && (
              <Accordion title={`Tavily Searches (${deal.search_logs.length} queries)`}>
                <div className="space-y-4">
                  {deal.search_logs.map((log, i) => (
                    <div key={i}>
                      <p className="text-xs font-semibold mb-1" style={{ color: "var(--text-2)" }}>"{log.query}"</p>
                      <div className="space-y-1">
                        {log.results.slice(0, 3).map((r, j) => (
                          <a key={j} href={r.url} target="_blank" rel="noreferrer" className="flex items-center gap-1.5 text-xs text-blue-400 hover:underline truncate">
                            <ExternalLink size={10} /> {r.title}
                          </a>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </Accordion>
            )}

            {t && (
              <Accordion title="Agent 3 — Scoring Reasoning">
                <div className="space-y-3 text-xs">
                  {[
                    { label: "Sector Fit", dim: t.sector_fit },
                    { label: "Geography Fit", dim: t.geography_fit },
                    { label: "Stage Fit", dim: t.stage_fit },
                    { label: "ARR / Traction", dim: t.arr_traction_fit },
                  ].map(({ label, dim }) => (
                    <div key={label}>
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="font-semibold" style={{ color: "var(--text-2)" }}>{label}</span>
                        <span className={cn("font-bold tabular-nums", fitColor(dim.score))}>{dim.score}/100</span>
                        <span style={{ color: "var(--text-3)" }}>({scoreLabel(dim.score)})</span>
                      </div>
                      <p style={{ color: "var(--text-2)" }} className="leading-snug">{dim.reasoning}</p>
                    </div>
                  ))}
                </div>
              </Accordion>
            )}

            {deal.errors_json && Object.keys(deal.errors_json).length > 0 && (
              <Accordion title="Pipeline Errors">
                <div className="space-y-2">
                  {Object.entries(deal.errors_json).map(([agent, msg]) => (
                    <div key={agent} className="flex gap-2 text-xs">
                      <AlertCircle size={12} className="text-red-400 shrink-0 mt-0.5" />
                      <div><span className="font-semibold text-red-400">{agent}: </span><span style={{ color: "#fca5a5" }}>{msg}</span></div>
                    </div>
                  ))}
                </div>
              </Accordion>
            )}
          </div>
        </div>

        {/* ── Floating mini-TOC ────────────────────────────────── */}
        <div className="fixed right-4 top-1/2 -translate-y-1/2 flex flex-col gap-1 z-30">
          {SECTIONS.map(({ id: sid, label }) => (
            <button
              key={sid}
              onClick={() => scrollTo(sid)}
              className="text-[11px] font-medium text-right transition-colors px-2 py-0.5 rounded"
              style={
                activeSection === sid
                  ? { color: "#93c5fd", background: "rgba(59,130,246,0.15)" }
                  : { color: "var(--text-3)" }
              }
            >
              {label}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
