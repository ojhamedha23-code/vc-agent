import { fitBarColor, fitColor } from "@/lib/utils"

export function FitBar({ pct }: { pct: number | null }) {
  if (pct === null) return <span className="text-slate-400 text-sm">—</span>
  return (
    <div className="flex items-center gap-2">
      <div className="w-20 h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${fitBarColor(pct)}`} style={{ width: `${pct}%` }} />
      </div>
      <span className={`text-sm font-semibold tabular-nums ${fitColor(pct)}`}>{pct.toFixed(0)}%</span>
    </div>
  )
}
