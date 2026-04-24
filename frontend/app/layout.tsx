import type { Metadata } from "next"
import { ClerkProvider } from "@clerk/nextjs"
import "./globals.css"
import { TopNav } from "@/components/TopNav"
import { AutoSelectOrg } from "@/components/AutoSelectOrg"

export const metadata: Metadata = {
  title: "Insiders Den — VC Due Diligence",
  description: "AI-powered pitch deck screening for VC analysts",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <ClerkProvider>
      <html lang="en" className="h-full">
        <body className="h-full antialiased">
          <AutoSelectOrg />
          <TopNav />
          <main className="min-h-screen">{children}</main>
        </body>
      </html>
    </ClerkProvider>
  )
}
