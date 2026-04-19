import { DealDetail, DealSummary, ProgressEvent } from "@/types"

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? "Request failed")
  }
  return res.json()
}

export const api = {
  // Thesis
  getThesis: () => req<{ text: string }>("/api/thesis"),
  saveThesis: (text: string) =>
    req("/api/thesis", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    }),
  uploadThesisFile: (file: File) => {
    const form = new FormData()
    form.append("file", file)
    return req<{ text: string }>("/api/thesis/upload", { method: "POST", body: form })
  },

  // Deals
  getDeals: () => req<DealSummary[]>("/api/deals"),
  getDeal: (id: string) => req<DealDetail>(`/api/deals/${id}`),
  deleteDeal: (id: string) =>
    req(`/api/deals/${id}`, { method: "DELETE" }),

  // Analysis
  analyzeFile: (file: File) => {
    const form = new FormData()
    form.append("file", file)
    return req<{ job_id: string }>("/api/analyze/file", {
      method: "POST",
      body: form,
    })
  },
  analyzeUrl: (url: string) =>
    req<{ job_id: string }>("/api/analyze/url", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    }),

  // Notify email
  getNotifyEmail: () => req<{ email: string }>("/api/notify-email"),
  saveNotifyEmail: (email: string) =>
    req("/api/notify-email", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    }),

  // SSE progress stream
  streamProgress: (
    jobId: string,
    onMessage: (e: ProgressEvent) => void,
    onDone: (dealId: string) => void,
    onError: (msg: string) => void
  ) => {
    const es = new EventSource(`${BASE}/api/analyze/progress/${jobId}`)
    es.onmessage = (event) => {
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
