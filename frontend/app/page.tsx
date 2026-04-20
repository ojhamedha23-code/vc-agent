"use client"
import { useEffect, useState, useCallback, useMemo } from "react"
import { useRouter } from "next/navigation"
import {
  Plus, Loader2, Link2, X, FileText,
  TrendingUp, CheckCircle2, XCircle, LayoutList, ChevronDown, Trash2
} from "lucide-react"
import { api } from "@/lib/api"
import { DealSummary } from "@/types"
import { ActionBadge } from "@/components/ActionBadge"
import { FitBar } from "@/components/FitBar"
import { UploadZone } from "@/components/UploadZone"
import { ProgressTracker } from "@/components/ProgressTracker"
import { formatDate } from "@/lib/utils"

type SortKey = "created_at" | "fit_pct" | "company"
type StatusFilter = "ALL" | "REVIEW" | "ARCHIVE" | "PASS"

function getGreeting() {
  const h = new Date().getHours()
  if (h < 12) return "Good morning"
  if (h < 17) return "Good afternoon"
  return "Good evening"
}

function getDateLabel() {
  return new Date().toLocaleDateString("en-US", {
    weekday: "long", day: "numeric", month: "long", year: "numeric",
  }).toUpperCase()
}

function MetricCard({ label, value, icon: Icon }: {
  label: string; value: string | number; icon: React.ElementType
}) {
  return (
    <div className="rounded-xl px-5 py-4 flex items-center gap-4"
      style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
      <div className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0"
        style={{ background: "rgba(59,130,246,0.15)" }}>
        <Icon size={17} className="text-blue-400" />
      </div>
      <div>
        <p className="text-2xl font-bold text-white tabular-nums leading-none">{value}</p>
        <p className="text-xs mt-1 font-medium" style={{ color: "var(--text-2)" }}>{label}</p>
      </div>
    </div>
  )
}

function SelectFilter({ label, value, options, onChange }: {
  label: string; value: string; options: string[]; onChange: (v: string) => void
}) {
  return (
    <div className="relative">
      <select
        value={value}
        onChange={e => onChange(e.target.value)}
        className="appearance-none text-sm rounded-lg pl-3 pr-7 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer"
        style={{ background: "var(--bg-card)", border: "1px solid var(--border-md)", color: "var(--text-1)" }}
      >
        <option value="">{label}: All</option>
        {options.map(o => <option key={o} value={o}>{o}</option>)}
      </select>
      <ChevronDown size={12} className="absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none" style={{ color: "var(--text-2)" }} />
    </div>
  )
}

export default function Dashboard() {
  const router = useRouter()
  const [deals, setDeals] = useState<DealSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [showUpload, setShowUpload] = useState(false)
  const [urlMode, setUrlMode] = useState(false)
  const [urlInput, setUrlInput] = useState("")
  const [running, setRunning] = useState(false)
  const [messages, setMessages] = useState<string[]>([])
  const [error, setError] = useState("")
  const [status, setStatus] = useState<StatusFilter>("ALL")
  const [sort, setSort] = useState<SortKey>("created_at")
  const [stageFilter, setStageFilter] = useState("")
  const [geoFilter, setGeoFilter] = useState("")
  const [dateFilter, setDateFilter] = useState("")
  const [deletingId, setDeletingId] = useState<string | null>(null)

  async function handleDelete(e: React.MouseEvent, dealId: string) {
    e.stopPropagation()
    if (!confirm("Delete this deal? This cannot be undone.")) return
    setDeletingId(dealId)
    await api.deleteDeal(dealId)
    setDeals(prev => prev.filter(d => d.id !== dealId))
    setDeletingId(null)
  }

  const load = useCallback(async () => {
    try { setDeals(await api.getDeals()) } finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const stages = useMemo(() =>
    [...new Set(deals.map(d => d.stage).filter(Boolean) as string[])].sort(), [deals])
  const geos = useMemo(() =>
    [...new Set(deals.map(d => d.hq).filter(Boolean) as string[])].sort(), [deals])

  const reviewCount = deals.filter(d => d.action === "REVIEW").length
  const passCount = deals.filter(d => d.action === "PASS").length
  const fitDeals = deals.filter(d => d.fit_pct !== null)
  const avgFit = fitDeals.length
    ? Math.round(fitDeals.reduce((s, d) => s + (d.fit_pct ?? 0), 0) / fitDeals.length)
    : null

  const counts = {
    ALL: deals.length,
    REVIEW: reviewCount,
    ARCHIVE: deals.filter(d => d.action === "ARCHIVE").length,
    PASS: passCount,
  }

  const filtered = useMemo(() => {
    const now = Date.now()
    return [...deals]
      .filter(d => status === "ALL" || d.action === status)
      .filter(d => !stageFilter || d.stage === stageFilter)
      .filter(d => !geoFilter || d.hq === geoFilter)
      .filter(d => {
        if (!dateFilter) return true
        const age = now - new Date(d.created_at).getTime()
        if (dateFilter === "7d") return age < 7 * 86400000
        if (dateFilter === "30d") return age < 30 * 86400000
        return true
      })
      .sort((a, b) => {
        if (sort === "fit_pct") return (b.fit_pct ?? -1) - (a.fit_pct ?? -1)
        if (sort === "company") return a.company.localeCompare(b.company)
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      })
  }, [deals, status, stageFilter, geoFilter, dateFilter, sort])

  async function startAnalysis(file?: File, url?: string) {
    setRunning(true); setMessages([]); setError("")
    try {
      const { job_id } = file ? await api.analyzeFile(file) : await api.analyzeUrl(url!)
      api.streamProgress(
        job_id,
        e => setMessages(m => [...m, e.message ?? ""]),
        dealId => { setRunning(false); setShowUpload(false); load(); router.push(`/deals/${dealId}`) },
        msg => { setError(msg); setRunning(false) }
      )
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to start analysis")
      setRunning(false)
    }
  }

  return (
    <div className="max-w-6xl mx-auto px-6 space-y-6">

      {/* ── Hero / Greeting ─────────────────────────────────── */}
      <div className="relative py-12 text-center overflow-hidden rounded-b-2xl"
        style={{ background: "linear-gradient(180deg, #0a1628 0%, var(--bg) 100%)" }}>
        {/* Sparkle decorations */}
        {[
          "top-4 left-10", "top-8 left-1/4", "top-3 right-16", "top-6 right-1/3",
          "bottom-6 left-16", "bottom-4 right-12",
        ].map((pos, i) => (
          <span key={i} className={`absolute ${pos} text-blue-400/30 text-lg select-none`}>✦</span>
        ))}

        <h1 className="text-5xl font-bold text-white leading-tight tracking-tight text-center">
          GenAI built for moving deals faster
        </h1>
        <p className="mt-4 text-base leading-relaxed text-center mx-auto" style={{ color: "var(--text-2)", maxWidth: "640px" }}>
          With Insiders Den, you can do in minutes tasks that used to take hours. Comb through more data, move on deals faster and focus on work that wins.
        </p>
      </div>

      {/* ── Metric cards ────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard label="Deals Screened" value={deals.length} icon={LayoutList} />
        <MetricCard label="Avg Fit Score" value={avgFit !== null ? `${avgFit}%` : "—"} icon={TrendingUp} />
        <MetricCard label="To Review" value={reviewCount} icon={CheckCircle2} />
        <MetricCard label="Deals Passed" value={passCount} icon={XCircle} />
      </div>

      {/* ── Filter bar ──────────────────────────────────────── */}
      <div className="rounded-xl px-4 py-3 flex flex-wrap items-center gap-3"
        style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
        {/* Status tabs */}
        <div className="flex items-center gap-1">
          {(["ALL", "REVIEW", "ARCHIVE", "PASS"] as StatusFilter[]).map(s => (
            <button
              key={s}
              onClick={() => setStatus(s)}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors"
              style={status === s
                ? { background: "#3b82f6", color: "#fff" }
                : { color: "var(--text-2)" }}
            >
              {s} <span className="opacity-50 ml-0.5">{counts[s]}</span>
            </button>
          ))}
        </div>

        <div className="w-px h-5" style={{ background: "var(--border-md)" }} />

        <SelectFilter label="Stage" value={stageFilter} options={stages} onChange={setStageFilter} />
        <SelectFilter label="Geography" value={geoFilter} options={geos} onChange={setGeoFilter} />
        <div className="relative">
          <select
            value={dateFilter}
            onChange={e => setDateFilter(e.target.value)}
            className="appearance-none text-sm rounded-lg pl-3 pr-7 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer"
            style={{ background: "var(--bg-card)", border: "1px solid var(--border-md)", color: "var(--text-1)" }}
          >
            <option value="">Date: All Time</option>
            <option value="7d">Last 7 days</option>
            <option value="30d">Last 30 days</option>
          </select>
          <ChevronDown size={12} className="absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none" style={{ color: "var(--text-2)" }} />
        </div>

        <div className="ml-auto flex items-center gap-1 text-sm" style={{ color: "var(--text-2)" }}>
          Sort:
          {([["created_at", "Date"], ["fit_pct", "Fit %"], ["company", "Name"]] as [SortKey, string][]).map(([key, label]) => (
            <button
              key={key}
              onClick={() => setSort(key)}
              className="px-2 py-1 rounded-lg transition-colors font-medium"
              style={sort === key
                ? { color: "#3b82f6", background: "rgba(59,130,246,0.1)" }
                : { color: "var(--text-2)" }}
            >
              {label}
            </button>
          ))}
        </div>

        <button
          onClick={() => setShowUpload(true)}
          className="flex items-center gap-2 text-sm font-semibold px-4 py-2 rounded-lg transition-colors ml-2"
          style={{ background: "#3b82f6", color: "#fff" }}
        >
          <Plus size={15} /> Screen a Deck
        </button>
      </div>

      {/* ── Deal list ───────────────────────────────────────── */}
      {loading ? (
        <div className="flex items-center justify-center py-24" style={{ color: "var(--text-3)" }}>
          <Loader2 size={24} className="animate-spin" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-24 rounded-xl" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
          <FileText size={36} className="mx-auto mb-3 opacity-20 text-white" />
          <p className="text-sm font-medium" style={{ color: "var(--text-2)" }}>No deals match your filters</p>
          {deals.length === 0 && (
            <button onClick={() => setShowUpload(true)} className="mt-3 text-blue-400 hover:underline text-sm font-semibold">
              Screen your first deck →
            </button>
          )}
        </div>
      ) : (
        <div className="rounded-xl overflow-hidden pb-6" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
          <table className="w-full">
            <thead>
              <tr className="text-xs font-semibold uppercase tracking-wider"
                style={{ borderBottom: "1px solid var(--border)", color: "var(--text-3)" }}>
                <th className="text-left px-5 py-3">Company</th>
                <th className="text-left px-4 py-3">Sector</th>
                <th className="text-left px-4 py-3">Stage</th>
                <th className="text-left px-4 py-3">Geography</th>
                <th className="text-left px-4 py-3">Thesis Fit</th>
                <th className="text-left px-4 py-3">Action</th>
                <th className="text-left px-4 py-3">Date</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((deal, i) => (
                <tr
                  key={deal.id}
                  onClick={() => router.push(`/deals/${deal.id}`)}
                  className="cursor-pointer transition-colors group"
                  style={{
                    borderTop: i === 0 ? "none" : `1px solid var(--border)`,
                  }}
                  onMouseEnter={e => (e.currentTarget.style.background = "var(--bg-hover)")}
                  onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
                >
                  <td className="px-5 py-3.5 font-semibold text-white text-[15px] group-hover:text-blue-400 transition-colors">
                    {deal.company}
                  </td>
                  <td className="px-4 py-3.5 text-sm" style={{ color: "var(--text-2)" }}>{deal.sector ?? "—"}</td>
                  <td className="px-4 py-3.5 text-sm" style={{ color: "var(--text-2)" }}>{deal.stage ?? "—"}</td>
                  <td className="px-4 py-3.5 text-sm" style={{ color: "var(--text-2)" }}>{deal.hq ?? "—"}</td>
                  <td className="px-4 py-3.5"><FitBar pct={deal.fit_pct} /></td>
                  <td className="px-4 py-3.5"><ActionBadge action={deal.action} /></td>
                  <td className="px-4 py-3.5 text-xs" style={{ color: "var(--text-3)" }}>{formatDate(deal.created_at)}</td>
                  <td className="px-4 py-3.5 text-right">
                    <button
                      onClick={e => handleDelete(e, deal.id)}
                      disabled={deletingId === deal.id}
                      className="opacity-0 group-hover:opacity-100 transition-opacity p-1.5 rounded-md"
                      style={{ color: "var(--text-3)" }}
                      onMouseEnter={e => (e.currentTarget.style.color = "#f87171")}
                      onMouseLeave={e => (e.currentTarget.style.color = "var(--text-3)")}
                      title="Delete deal"
                    >
                      {deletingId === deal.id
                        ? <Loader2 size={13} className="animate-spin" />
                        : <Trash2 size={13} />}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* bottom padding */}
      <div className="h-8" />

      {/* ── Upload modal ────────────────────────────────────── */}
      {showUpload && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "rgba(0,0,0,0.7)" }}>
          <div className="rounded-xl shadow-2xl w-full max-w-lg p-6" style={{ background: "var(--bg-card)", border: "1px solid var(--border-md)" }}>
            <div className="flex items-center justify-between mb-5">
              <div>
                <h2 className="font-bold text-white text-[15px]">Screen a New Deck</h2>
                <p className="text-xs mt-0.5" style={{ color: "var(--text-2)" }}>Upload a PDF or PPTX, or paste a PDF URL</p>
              </div>
              {!running && (
                <button onClick={() => { setShowUpload(false); setError("") }} style={{ color: "var(--text-2)" }}>
                  <X size={18} />
                </button>
              )}
            </div>

            {running ? (
              <div className="space-y-4">
                <p className="text-sm font-medium" style={{ color: "var(--text-1)" }}>Running 4-agent pipeline…</p>
                <ProgressTracker messages={messages} />
                {error && <p className="text-sm text-red-400">{error}</p>}
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex gap-2">
                  <button onClick={() => setUrlMode(false)}
                    className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full font-medium transition-colors"
                    style={!urlMode ? { background: "rgba(59,130,246,0.2)", color: "#60a5fa" } : { color: "var(--text-2)" }}>
                    <FileText size={12} /> Upload file
                  </button>
                  <button onClick={() => setUrlMode(true)}
                    className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full font-medium transition-colors"
                    style={urlMode ? { background: "rgba(59,130,246,0.2)", color: "#60a5fa" } : { color: "var(--text-2)" }}>
                    <Link2 size={12} /> PDF URL
                  </button>
                </div>

                {urlMode ? (
                  <div className="space-y-3">
                    <input
                      value={urlInput}
                      onChange={e => setUrlInput(e.target.value)}
                      placeholder="https://example.com/deck.pdf"
                      className="w-full rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      style={{ background: "rgba(255,255,255,0.05)", border: "1px solid var(--border-md)", color: "var(--text-1)" }}
                    />
                    <button disabled={!urlInput.trim()} onClick={() => startAnalysis(undefined, urlInput.trim())}
                      className="w-full text-white text-sm font-semibold py-2.5 rounded-lg transition-colors disabled:opacity-40"
                      style={{ background: "#3b82f6" }}>
                      Analyse URL
                    </button>
                  </div>
                ) : (
                  <UploadZone onFile={f => startAnalysis(f)} />
                )}

                {error && <p className="text-sm text-red-400">{error}</p>}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
