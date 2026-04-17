import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"
import { Action } from "@/types"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function actionColor(action: Action) {
  return {
    REVIEW: { bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-200", dot: "bg-emerald-500" },
    ARCHIVE: { bg: "bg-amber-50", text: "text-amber-700", border: "border-amber-200", dot: "bg-amber-500" },
    PASS: { bg: "bg-red-50", text: "text-red-700", border: "border-red-200", dot: "bg-red-500" },
    ERROR: { bg: "bg-slate-50", text: "text-slate-500", border: "border-slate-200", dot: "bg-slate-400" },
  }[action] ?? { bg: "bg-slate-50", text: "text-slate-500", border: "border-slate-200", dot: "bg-slate-400" }
}

export function fitColor(pct: number | null) {
  if (pct === null) return "text-slate-400"
  if (pct >= 75) return "text-emerald-600"
  if (pct >= 50) return "text-amber-600"
  return "text-red-500"
}

export function fitBarColor(pct: number | null) {
  if (pct === null) return "bg-slate-200"
  if (pct >= 75) return "bg-emerald-500"
  if (pct >= 50) return "bg-amber-500"
  return "bg-red-400"
}

export function formatDate(iso: string) {
  const d = new Date(iso)
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
}

export function scoreLabel(score: number) {
  if (score === 100) return "Perfect fit"
  if (score === 75) return "Strong fit"
  if (score === 50) return "Partial fit"
  if (score === 25) return "Weak fit"
  return "No fit"
}
