"use client"

import { useAuth } from "@clerk/nextjs"
import { useMemo } from "react"
import { createApi } from "@/lib/api"

/**
 * Returns an authenticated API client bound to the current Clerk session.
 * Every method automatically attaches `Authorization: Bearer <token>`.
 *
 * Usage:
 *   const api = useApi()
 *   const deals = await api.getDeals()
 */
export function useApi() {
  const { getToken } = useAuth()
  // Memoised so the same object reference is returned between renders
  return useMemo(() => createApi(getToken), [getToken])
}
