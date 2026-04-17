import { fitColor } from "@/lib/utils"

export function ScoreRing({ pct, size = 80 }: { pct: number | null; size?: number }) {
  const r = (size - 8) / 2
  const circ = 2 * Math.PI * r
  const fill = pct !== null ? (pct / 100) * circ : 0
  const color = pct === null ? "#94a3b8" : pct >= 75 ? "#10b981" : pct >= 50 ? "#f59e0b" : "#ef4444"

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#f1f5f9" strokeWidth={6} />
        <circle
          cx={size / 2} cy={size / 2} r={r} fill="none"
          stroke={color} strokeWidth={6}
          strokeDasharray={circ}
          strokeDashoffset={circ - fill}
          strokeLinecap="round"
          style={{ transition: "stroke-dashoffset 0.5s ease" }}
        />
      </svg>
      <span className={`absolute text-sm font-bold tabular-nums ${fitColor(pct)}`}>
        {pct !== null ? `${pct.toFixed(0)}%` : "—"}
      </span>
    </div>
  )
}
