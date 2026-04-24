"use client"
import { useEffect } from "react"
import { useOrganizationList, useOrganization } from "@clerk/nextjs"

/**
 * Automatically activates the user's first org if none is currently active.
 * This ensures org_id is present in the Clerk JWT so the backend can scope data.
 */
export function AutoSelectOrg() {
  const { organization } = useOrganization()
  const { userMemberships, setActive, isLoaded } = useOrganizationList({
    userMemberships: { infinite: true },
  })

  useEffect(() => {
    if (!isLoaded || organization) return
    const first = userMemberships?.data?.[0]?.organization
    if (first && setActive) {
      setActive({ organization: first.id })
    }
  }, [isLoaded, organization, userMemberships, setActive])

  return null
}
