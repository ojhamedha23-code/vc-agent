"use client"

import { useOrganization } from "@clerk/nextjs"

/**
 * Role system with two tiers mapped from Clerk's built-in roles:
 *
 *   Clerk "org:admin"  → our "admin"   (org creator / full access)
 *   Clerk "org:member" → role from publicMetadata.role, defaulting to "analyst"
 *
 * To assign a higher member role via Clerk Dashboard:
 *   Users → click user → Organization Memberships → Edit metadata
 *   Set publicMetadata: { "role": "senior_analyst" }  or  "partner"
 *
 * If custom Clerk roles ARE available (Roles tab found):
 *   Create keys: analyst | senior_analyst | partner
 *   This hook will automatically pick them up via membership.role
 */
export type Role = "analyst" | "senior_analyst" | "partner" | "admin"

const ROLE_PERMISSIONS: Record<Role, Set<string>> = {
  analyst:         new Set(["upload", "view"]),
  senior_analyst:  new Set(["upload", "view", "delete"]),
  partner:         new Set(["upload", "view", "delete", "edit_thesis"]),
  admin:           new Set(["upload", "view", "delete", "edit_thesis", "invite"]),
}

const ROLE_LABELS: Record<Role, string> = {
  analyst:        "Analyst",
  senior_analyst: "Senior Analyst",
  partner:        "Partner",
  admin:          "Admin",
}

const VALID_ROLES = new Set<Role>(["analyst", "senior_analyst", "partner", "admin"])

/**
 * Resolve role from Clerk membership:
 * 1. Strip "org:" prefix from membership.role
 * 2. If it's a valid custom role (senior_analyst, partner) → use it
 * 3. If it's "admin" → admin
 * 4. If it's "member" → check publicMetadata.role for sub-role
 * 5. Default → analyst
 */
function parseRole(
  clerkRole: string | undefined,
  publicMetadata: Record<string, unknown> | undefined,
): Role {
  if (!clerkRole) return "analyst"

  const key = clerkRole.replace("org:", "")

  // Custom Clerk roles (if org has them configured)
  if (key === "admin") return "admin"
  if (VALID_ROLES.has(key as Role)) return key as Role

  // Default "member" role — check publicMetadata for sub-role
  if (key === "member") {
    const metaRole = (publicMetadata?.role as string | undefined)?.toLowerCase()
    if (metaRole && VALID_ROLES.has(metaRole as Role)) return metaRole as Role
    return "analyst"
  }

  return "analyst"
}

/**
 * Returns the current user's role within their active Clerk organisation,
 * plus a `can(permission)` helper.
 *
 * Usage:
 *   const { role, label, can } = useRole()
 *   if (can("delete")) { ... }
 */
export function useRole() {
  const { membership } = useOrganization()

  const role = parseRole(
    membership?.role,
    membership?.publicMetadata as Record<string, unknown> | undefined,
  )

  return {
    role,
    label: ROLE_LABELS[role],
    can: (permission: string) => ROLE_PERMISSIONS[role]?.has(permission) ?? false,
  }
}
