import { DealDetail, DealSummary, ProgressEvent } from "@/types"

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

// ── Core fetch wrapper ────────────────────────────────────────────────────────

async function req<T>(
  path: string,
  init?: RequestInit,
  token?: string | null,
): Promise<T> {
  const headers: Record<string, string> = {}

  if (token) {
    headers["Authorization"] = `Bearer ${token}`
  }

  // Don't set Content-Type for FormData — browser sets it with the boundary
  if (!(init?.body instanceof FormData)) {
    headers["Content-Type"] = "application/json"
  }

  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { ...headers, ...(init?.headers as Record<string, string> | undefined) },
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? "Request failed")
  }
  return res.json() as Promise<T>
}

// ── Authenticated API factory ─────────────────────────────────────────────────
// Pass Clerk's getToken() so every call carries the JWT automatically.

export function createApi(getToken: () => Promise<string | null>) {
  const t = () => getToken()

  return {
    // Thesis
    getThesis: () =>
      t().then(tok => req<{ text: string }>("/api/thesis", undefined, tok)),
    saveThesis: (text: string) =>
      t().then(tok => req("/api/thesis", { method: "POST", body: JSON.stringify({ text }) }, tok)),
    uploadThesisFile: (file: File) => {
      const form = new FormData()
      form.append("file", file)
      return t().then(tok => req<{ text: string }>("/api/thesis/upload", { method: "POST", body: form }, tok))
    },

    // Deals
    getDeals: () =>
      t().then(tok => req<DealSummary[]>("/api/deals", undefined, tok)),
    getDeal: (id: string) =>
      t().then(tok => req<DealDetail>(`/api/deals/${id}`, undefined, tok)),
    deleteDeal: (id: string) =>
      t().then(tok => req(`/api/deals/${id}`, { method: "DELETE" }, tok)),

    // Analysis
    analyzeFile: (file: File) => {
      const form = new FormData()
      form.append("file", file)
      return t().then(tok => req<{ job_id: string }>("/api/analyze/file", { method: "POST", body: form }, tok))
    },
    analyzeUrl: (url: string) =>
      t().then(tok =>
        req<{ job_id: string }>("/api/analyze/url", { method: "POST", body: JSON.stringify({ url }) }, tok)
      ),

    // Notify email
    getNotifyEmail: () =>
      t().then(tok => req<{ email: string }>("/api/notify-email", undefined, tok)),
    saveNotifyEmail: (email: string) =>
      t().then(tok =>
        req("/api/notify-email", { method: "POST", body: JSON.stringify({ email }) }, tok)
      ),

    // Me (role info from backend)
    getMe: () =>
      t().then(tok =>
        req<{ user_id: string; org_id: string; role: string }>("/api/me", undefined, tok)
      ),

    // SSE progress stream — no auth needed (job_id is the access token)
    streamProgress: (
      jobId: string,
      onMessage: (e: ProgressEvent) => void,
      onDone: (dealId: string) => void,
      onError: (msg: string) => void,
    ) => {
      const es = new EventSource(`${BASE}/api/analyze/progress/${jobId}`)
      es.onmessage = event => {
        const data: ProgressEvent = JSON.parse(event.data)
        if (data.type === "done") {
          es.close()
          onDone(data.deal_id!)
        } else if (data.type === "error") {
          es.close()
          onError(data.message ?? "Unknown error")
        } else {
          onMessage(data)
        }
      }
      es.onerror = () => {
        es.close()
        onError("Connection lost")
      }
      return () => es.close()
    },
  }
}

export type Api = ReturnType<typeof createApi>
