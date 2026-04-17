"use client"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { useEffect, useState } from "react"
import { Zap } from "lucide-react"

export function TopNav() {
  const path = usePathname()
  const onDeal = path.startsWith("/deals/")
  const [lastDealId, setLastDealId] = useState<string | null>(null)

  useEffect(() => {
    if (onDeal) {
      const id = path.split("/deals/")[1]
      if (id) { localStorage.setItem("lastDealId", id); setLastDealId(id) }
    } else {
      setLastDealId(localStorage.getItem("lastDealId"))
    }
  }, [path, onDeal])

  const memoHref = onDeal ? path : lastDealId ? `/deals/${lastDealId}` : null

  const tabs = [
    { label: "Dashboard", href: "/", active: path === "/" },
    { label: "Investment Memo", href: memoHref, active: onDeal },
    { label: "Thesis Setup", href: "/settings", active: path === "/settings" },
  ]

  return (
    <header className="sticky top-0 z-40" style={{ background: "var(--bg-card)", borderBottom: "1px solid var(--border)" }}>
      <div className="px-6 flex items-center h-14 gap-8">
        {/* Brand */}
        <Link href="/" className="flex items-center gap-2.5 shrink-0">
          <div className="w-7 h-7 bg-blue-600 rounded-lg flex items-center justify-center">
            <Zap size={13} className="text-white" />
          </div>
          <span className="font-bold text-white text-[15px] tracking-tight">InsidersDen</span>
        </Link>

        {/* Pill tabs on dark bg */}
        <nav className="flex items-center rounded-full p-1 gap-0.5" style={{ background: "rgba(255,255,255,0.05)" }}>
          {tabs.map(({ label, href, active }) => {
            const base = "px-4 py-1.5 rounded-full text-sm font-medium transition-all duration-150"
            const activeStyle = { background: "rgba(255,255,255,0.12)", color: "#fff" }
            const inactiveStyle = { color: "var(--text-2)" }
            const disabledStyle = { color: "var(--text-3)", cursor: "default" }

            if (href) return (
              <Link key={label} href={href} className={base} style={active ? activeStyle : inactiveStyle}>
                {label}
              </Link>
            )
            return (
              <span key={label} className={base} title="Open a deal first" style={disabledStyle}>
                {label}
              </span>
            )
          })}
        </nav>
      </div>
    </header>
  )
}
