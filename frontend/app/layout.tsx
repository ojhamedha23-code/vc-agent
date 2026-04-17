import type { Metadata } from "next"
import "./globals.css"
import { TopNav } from "@/components/TopNav"

export const metadata: Metadata = {
  title: "InsidersDen — VC Due Diligence",
  description: "AI-powered pitch deck screening for VC analysts",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full">
      <body className="h-full antialiased">
        <TopNav />
        <main className="min-h-screen">{children}</main>
      </body>
    </html>
  )
}
