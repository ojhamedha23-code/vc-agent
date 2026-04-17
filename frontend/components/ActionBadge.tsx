import { Action } from "@/types"
import { actionColor } from "@/lib/utils"

export function ActionBadge({ action }: { action: Action }) {
  const c = actionColor(action)
  const label = { REVIEW: "Review", ARCHIVE: "Archive", PASS: "Pass", ERROR: "Error" }[action]
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${c.bg} ${c.text} ${c.border}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${c.dot}`} />
      {label}
    </span>
  )
}
