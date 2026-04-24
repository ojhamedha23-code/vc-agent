"use client"

import { useAuth, useOrganization } from "@clerk/nextjs"
import { useMemo } from "react"
import { createApi } from "@/lib/api"

/**
 * Returns an authenticated API client bound to the current Clerk session.
 * Every method automatically attaches `Authorization: Bearer <token>`.
 *
 * Passes organizationId explicitly to getToken() so the JWT always contains
 * org_id — even if Clerk's session cache hasn't refreshed yet.
 */
export function useApi() {
  const { getToken } = useAuth()
  const { organization } = useOrganization()
  const orgId = organization?.id

  return useMemo(
    () => createApi(() => getToken({ organizationId: orgId })),
    [getToken, orgId],
  )
}
