import { CheckCircle, Loader2, Circle } from "lucide-react"

const STEPS = [
  { key: "parse", label: "Parsing deck" },
  { key: "agent1", label: "Agent 1 — Extracting claims" },
  { key: "agent23", label: "Agent 2 + 3 — Fact-check & thesis score" },
  { key: "agent4", label: "Agent 4 — Drafting memo" },
]

function matchStep(msg: string): string {
  if (msg.startsWith("Parsing") || msg.startsWith("Downloading") || msg.startsWith("Processing")) return "parse"
  if (msg.startsWith("Agent 1")) return "agent1"
  if (msg.startsWith("Agent 2")) return "agent23"
  if (msg.startsWith("Agent 4")) return "agent4"
  return ""
}

export function ProgressTracker({ messages }: { messages: string[] }) {
  const active = messages.length > 0 ? matchStep(messages[messages.length - 1]) : ""
  const done = messages.some(m => m === "Done.")

  const completedSteps = new Set<string>()
  let foundActive = false
  for (const step of STEPS) {
    if (step.key === active) { foundActive = true; break }
    completedSteps.add(step.key)
  }
  if (done) STEPS.forEach(s => completedSteps.add(s.key))

  return (
    <div className="space-y-3 py-2">
      {STEPS.map((step) => {
        const isComplete = completedSteps.has(step.key)
        const isActive = step.key === active && !done
        return (
          <div key={step.key} className="flex items-center gap-3">
            {isComplete
              ? <CheckCircle size={18} className="text-emerald-500 shrink-0" />
              : isActive
              ? <Loader2 size={18} className="text-indigo-500 shrink-0 animate-spin" />
              : <Circle size={18} className="text-slate-300 shrink-0" />}
            <span className={`text-sm ${isComplete ? "text-slate-600" : isActive ? "text-slate-900 font-medium" : "text-slate-400"}`}>
              {step.label}
            </span>
          </div>
        )
      })}
    </div>
  )
}
