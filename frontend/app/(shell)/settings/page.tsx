"use client"
import { useEffect, useRef, useState } from "react"
import { CheckCircle2, Loader2, Save, Info, Upload, FileSpreadsheet, FileText } from "lucide-react"
import { api } from "@/lib/api"

const PLACEHOLDER = `Paste your fund thesis here in plain English. For example:

We are a Seed and Series A fund focused on B2B SaaS and enterprise software companies based in Southeast Asia (Singapore, Indonesia, Vietnam, Malaysia, Philippines). We write initial checks of $500K–$2M and target companies with at least $100K ARR showing strong month-over-month growth. We do not invest in consumer, e-commerce, D2C, or hardware-heavy businesses. We value repeat founders with domain expertise, and strong preference for teams with prior exits or top-tier institutional co-investors.`

export default function SettingsPage() {
  const [text, setText] = useState("")
  const [saved, setSaved] = useState("")
  const [saving, setSaving] = useState(false)
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState("")
  const [uploadName, setUploadName] = useState("")
  const fileRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    api.getThesis()
      .then(r => { setText(r.text); setSaved(r.text) })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  async function handleSave() {
    if (!text.trim()) return
    setSaving(true)
    setError("")
    setSuccess(false)
    try {
      await api.saveThesis(text.trim())
      setSaved(text.trim())
      setSuccess(true)
      setTimeout(() => setSuccess(false), 3000)
    } catch {
      setError("Failed to save thesis. Is the backend running?")
    } finally {
      setSaving(false)
    }
  }

  async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    setError("")
    setUploadName(file.name)
    try {
      const { text: extracted } = await api.uploadThesisFile(file)
      setText(extracted)
      setUploadName(file.name)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to parse file")
      setUploadName("")
    } finally {
      setUploading(false)
      if (fileRef.current) fileRef.current.value = ""
    }
  }

  const isDirty = text.trim() !== saved.trim()

  return (
    <div className="p-8 max-w-3xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold" style={{ color: "var(--text-1)" }}>Fund Thesis</h1>
        <p className="text-sm mt-0.5" style={{ color: "var(--text-2)" }}>
          Define your investment mandate. Agent 3 uses this to score every deck you screen.
        </p>
      </div>

      {/* Info callout */}
      <div className="rounded-xl px-4 py-3 flex gap-3 mb-6" style={{ background: "rgba(59,130,246,0.08)", border: "1px solid rgba(59,130,246,0.2)" }}>
        <Info size={16} className="shrink-0 mt-0.5" style={{ color: "#93c5fd" }} />
        <div className="space-y-1">
          <p className="text-sm font-medium" style={{ color: "#93c5fd" }}>How this works</p>
          <p className="text-xs leading-relaxed" style={{ color: "#bfdbfe" }}>
            The AI reads your thesis at screening time and scores deals on four dimensions: sector fit, geography fit, stage fit, and ARR/traction fit — using only what you write here. You can paste text directly or upload a PDF or Excel file to extract the content automatically.
          </p>
        </div>
      </div>

      {/* Upload from file */}
      <div className="rounded-xl px-4 py-4 mb-4 flex items-center justify-between gap-4" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
        <div>
          <p className="text-sm font-medium" style={{ color: "var(--text-1)" }}>Import from file</p>
          <p className="text-xs mt-0.5" style={{ color: "var(--text-3)" }}>Upload a PDF or Excel file — text will be extracted into the editor below</p>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          {uploadName && !uploading && (
            <div className="flex items-center gap-1.5 text-xs text-emerald-400">
              <CheckCircle2 size={13} />
              <span className="max-w-[140px] truncate">{uploadName} imported</span>
            </div>
          )}
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,.xlsx,.xls"
            className="hidden"
            onChange={handleFileUpload}
          />
          <button
            onClick={() => fileRef.current?.click()}
            disabled={uploading || loading}
            className="flex items-center gap-2 text-sm font-medium px-4 py-2 rounded-lg transition-colors disabled:opacity-40"
            style={{ background: "var(--bg-hover)", border: "1px solid var(--border-md)", color: "var(--text-1)" }}
          >
            {uploading ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <Upload size={14} />
            )}
            {uploading ? "Extracting…" : "Upload PDF or Excel"}
          </button>
        </div>
      </div>

      {/* Format hints */}
      <div className="flex gap-3 mb-4">
        <div className="flex items-center gap-1.5 text-xs" style={{ color: "var(--text-3)" }}>
          <FileText size={12} /> PDF thesis document
        </div>
        <div className="flex items-center gap-1.5 text-xs" style={{ color: "var(--text-3)" }}>
          <FileSpreadsheet size={12} /> Excel (.xlsx) scoring model
        </div>
      </div>

      {/* Textarea */}
      <div className="rounded-xl overflow-hidden" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
        <div className="flex items-center justify-between px-4 py-3" style={{ borderBottom: "1px solid var(--border)", background: "var(--bg)" }}>
          <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-3)" }}>Your Fund Thesis</p>
          {saved && (
            <span className="text-xs" style={{ color: "var(--text-3)" }}>{saved.length} characters saved</span>
          )}
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-24" style={{ color: "var(--text-3)" }}>
            <Loader2 size={20} className="animate-spin" />
          </div>
        ) : (
          <textarea
            value={text}
            onChange={e => setText(e.target.value)}
            placeholder={PLACEHOLDER}
            rows={20}
            className="w-full px-5 py-4 text-sm leading-relaxed resize-none focus:outline-none font-mono"
            style={{
              background: "var(--bg-card)",
              color: "var(--text-1)",
            }}
            spellCheck={false}
          />
        )}
      </div>

      {/* Word count */}
      {text && (
        <p className="text-xs mt-2" style={{ color: "var(--text-3)" }}>
          {text.trim().split(/\s+/).filter(Boolean).length} words
        </p>
      )}

      {/* Save row */}
      <div className="flex items-center gap-3 mt-4">
        <button
          onClick={handleSave}
          disabled={saving || !isDirty || !text.trim()}
          className="flex items-center gap-2 text-white text-sm font-medium px-5 py-2.5 rounded-lg transition-colors disabled:opacity-40"
          style={{ background: "var(--accent)" }}
        >
          {saving ? <Loader2 size={15} className="animate-spin" /> : <Save size={15} />}
          {saving ? "Saving…" : "Save Thesis"}
        </button>

        {success && (
          <div className="flex items-center gap-1.5 text-sm text-emerald-400">
            <CheckCircle2 size={15} /> Saved successfully
          </div>
        )}

        {error && <p className="text-sm text-red-400">{error}</p>}

        {isDirty && !saving && (
          <p className="text-xs ml-auto" style={{ color: "#fbbf24" }}>Unsaved changes</p>
        )}
      </div>

      {/* Tips */}
      <div className="mt-8 rounded-xl p-5" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
        <p className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: "var(--text-3)" }}>Tips for a strong thesis definition</p>
        <ul className="space-y-2 text-sm" style={{ color: "var(--text-2)" }}>
          {[
            "Be explicit about sectors you target AND sectors you exclude (e.g. \"no D2C, no e-commerce, no hardware\")",
            "Specify geographies with country names, not just regions (e.g. \"Singapore, Indonesia, Vietnam\")",
            "Include your traction bar — minimum ARR, MRR, or growth rate you require",
            "Name notable co-investors you consider a positive signal (e.g. \"Y Combinator, East Ventures, Sequoia\")",
            "Mention deal-breakers explicitly — the AI uses these to flag red flags automatically",
          ].map((tip, i) => (
            <li key={i} className="flex gap-2.5">
              <span className="shrink-0 w-4 h-4 rounded-full text-xs flex items-center justify-center font-bold mt-0.5" style={{ background: "rgba(59,130,246,0.15)", color: "#93c5fd" }}>{i + 1}</span>
              {tip}
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
