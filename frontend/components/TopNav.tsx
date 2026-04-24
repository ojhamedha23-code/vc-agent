"use client"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { useEffect, useState } from "react"
import {
  UserButton,
  OrganizationSwitcher,
  useOrganization,
} from "@clerk/nextjs"
import { useRole } from "@/hooks/useRole"

function InsidersDenLogo() {
  return (
    <svg width="28" height="28" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="28" height="28" rx="7" fill="#1e3a5f"/>
      {/* Rising trend line */}
      <polyline points="6,20 11,14 16,17 22,9"
        fill="none" stroke="#93c5fd" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
      {/* Arrow head */}
      <polyline points="18,9 22,9 22,13"
        fill="none" stroke="#93c5fd" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}

const ROLE_COLORS: Record<string, string> = {
  admin:           "rgba(239,68,68,0.15)",
  partner:         "rgba(168,85,247,0.15)",
  senior_analyst:  "rgba(59,130,246,0.15)",
  analyst:         "rgba(255,255,255,0.08)",
}
const ROLE_TEXT: Record<string, string> = {
  admin:           "#f87171",
  partner:         "#c084fc",
  senior_analyst:  "#93c5fd",
  analyst:         "var(--text-2)",
}

export function TopNav() {
  const path = usePathname()
  const onDeal = path.startsWith("/deals/")
  const [lastDealId, setLastDealId] = useState<string | null>(null)
  const { organization } = useOrganization()
  const { role, label } = useRole()

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
      <div className="px-6 flex items-center h-14 gap-4">

        {/* Brand — left */}
        <Link href="/" className="flex items-center gap-2.5 shrink-0">
          <InsidersDenLogo />
          <span className="font-bold text-white text-[15px] uppercase" style={{ letterSpacing: "0.12em" }}>
            Insiders Den
          </span>
        </Link>

        {/* Pill tabs — centered */}
        <nav className="flex-1 flex justify-center">
          <div className="flex items-center rounded-full p-1 gap-0.5" style={{ background: "rgba(255,255,255,0.05)" }}>
            {tabs.map(({ label: tabLabel, href, active }) => {
              const base = "px-4 py-1.5 rounded-full text-sm font-medium transition-all duration-150 whitespace-nowrap"
              const activeStyle = { background: "rgba(255,255,255,0.12)", color: "#fff" }
              const inactiveStyle = { color: "var(--text-2)" }
              const disabledStyle = { color: "var(--text-3)", cursor: "default" }

              if (href) return (
                <Link key={tabLabel} href={href} className={base} style={active ? activeStyle : inactiveStyle}>
                  {tabLabel}
                </Link>
              )
              return (
                <span key={tabLabel} className={base} title="Open a deal first" style={disabledStyle}>
                  {tabLabel}
                </span>
              )
            })}
          </div>
        </nav>

        {/* Right side — org switcher + role badge + user button */}
        <div className="flex items-center gap-3 shrink-0">

          {/* Role badge */}
          {organization && (
            <span
              className="text-xs font-semibold px-2.5 py-1 rounded-full"
              style={{
                background: ROLE_COLORS[role] ?? "rgba(255,255,255,0.08)",
                color: ROLE_TEXT[role] ?? "var(--text-2)",
              }}
            >
              {label}
            </span>
          )}

          {/* Org switcher — compact */}
          <OrganizationSwitcher
            hidePersonal
            afterCreateOrganizationUrl="/"
            afterLeaveOrganizationUrl="/"
            afterSelectOrganizationUrl="/"
            appearance={{
              elements: {
                rootBox: { display: "flex", alignItems: "center" },
                organizationSwitcherTrigger: {
                  padding: "4px 10px",
                  borderRadius: "8px",
                  border: "1px solid var(--border)",
                  background: "rgba(255,255,255,0.05)",
                  color: "var(--text-1)",
                  fontSize: "13px",
                  gap: "6px",
                },
              },
            }}
          />

          {/* User button */}
          <UserButton
            appearance={{
              elements: {
                avatarBox: { width: 32, height: 32 },
              },
            }}
          />
        </div>
      </div>
    </header>
  )
}
