"use client"
import { useEffect } from "react"
import { useOrganizationList, useOrganization, useAuth } from "@clerk/nextjs"

/**
 * Automatically activates the user's first org if none is currently active.
 * This ensures org_id is present in the Clerk JWT so the backend can scope data.
 */
export function AutoSelectOrg() {
  const { isSignedIn } = useAuth()
  const { organization } = useOrganization()
  const { userMemberships, setActive, isLoaded } = useOrganizationList({
    userMemberships: true,
  })

  useEffect(() => {
    if (!isSignedIn || !isLoaded) return
    if (organization) return // already active
    const memberships = userMemberships as any
    const data = memberships?.data ?? []
    const first = data[0]?.organization
    if (first && setActive) {
      setActive({ organization: first.id })
    }
  }, [isSignedIn, isLoaded, organization, userMemberships, setActive])

  return null
}
