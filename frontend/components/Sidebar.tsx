"use client"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { LayoutDashboard, Settings, Search } from "lucide-react"
import { cn } from "@/lib/utils"

const nav = [
  { href: "/", label: "Pipeline", icon: LayoutDashboard },
  { href: "/settings", label: "Fund Thesis", icon: Settings },
]

export function Sidebar() {
  const path = usePathname()
  return (
    <aside className="w-56 shrink-0 bg-slate-900 flex flex-col h-full">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 bg-indigo-500 rounded-lg flex items-center justify-center">
            <Search size={14} className="text-white" />
          </div>
          <span className="font-semibold text-white tracking-tight">DealLens</span>
        </div>
        <p className="text-xs text-slate-500 mt-1">VC Due Diligence Agent</p>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        {nav.map(({ href, label, icon: Icon }) => {
          const active = path === href
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors",
                active
                  ? "bg-indigo-600 text-white font-medium"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800"
              )}
            >
              <Icon size={16} />
              {label}
            </Link>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="px-5 py-4 border-t border-slate-800">
        <p className="text-xs text-slate-600">Powered by Claude Sonnet + Opus</p>
      </div>
    </aside>
  )
}
