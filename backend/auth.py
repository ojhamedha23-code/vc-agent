"""
Clerk JWT verification for FastAPI.

Verifies the session JWT sent from the Next.js frontend via
`Authorization: Bearer <token>`.  Uses Clerk's JWKS endpoint so
verification is local (no round-trip per request); keys are cached
for 1 hour.

Environment variables required (add to backend/.env):
  CLERK_JWKS_URL   e.g. https://<your-instance>.clerk.accounts.dev/.well-known/jwks.json
  CLERK_DEV_MODE   set to "true" to skip auth in local dev (no Clerk keys needed)

Role hierarchy (set via Clerk custom roles in the dashboard):
  org:admin           → Admin
  org:partner         → Partner
  org:senior_analyst  → Senior Analyst
  org:analyst         → Analyst  (default)
"""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Optional

import requests
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

CLERK_JWKS_URL = os.getenv("CLERK_JWKS_URL", "")
DEV_MODE = os.getenv("CLERK_DEV_MODE", "false").lower() == "true"

security = HTTPBearer(auto_error=False)

# ── JWKS cache ───────────────────────────────────────────────────────────────
_cache: dict = {"keys": {}, "fetched_at": 0.0}


def _load_jwks():
    """Fetch Clerk's public keys and cache them for 1 hour."""
    now = time.time()
    if now - _cache["fetched_at"] < 3600 and _cache["keys"]:
        return

    if not CLERK_JWKS_URL:
        logger.warning("CLERK_JWKS_URL not set — JWT verification disabled")
        return

    try:
        resp = requests.get(CLERK_JWKS_URL, timeout=5)
        resp.raise_for_status()
        from jwt.algorithms import RSAAlgorithm  # PyJWT

        new_keys: dict = {}
        for key_data in resp.json().get("keys", []):
            pub = RSAAlgorithm.from_jwk(json.dumps(key_data))
            new_keys[key_data["kid"]] = pub

        _cache["keys"] = new_keys
        _cache["fetched_at"] = now
        logger.info("Loaded %d JWKS keys from Clerk", len(new_keys))
    except Exception as exc:
        logger.error("Failed to load Clerk JWKS: %s", exc)


# ── Public API ────────────────────────────────────────────────────────────────

def verify_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
) -> dict:
    """
    FastAPI dependency.  Returns the decoded Clerk JWT payload.

    Raises HTTP 401 if the token is missing or invalid.
    In DEV_MODE (no Clerk configured) returns a mock admin payload.
    """
    # ── Dev bypass ────────────────────────────────────────────────────────────
    if DEV_MODE:
        if credentials is None:
            return {
                "sub": "dev_user_001",
                "org_id": "dev_org_001",
                "org_role": "org:admin",
                "email": "dev@insidersden.com",
            }

    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = credentials.credentials

    # ── No JWKS URL → pass-through (graceful degradation) ────────────────────
    if not CLERK_JWKS_URL:
        logger.warning("No CLERK_JWKS_URL — returning passthrough auth payload")
        return {
            "sub": "unknown",
            "org_id": "default_org",
            "org_role": "org:admin",
        }

    # ── Verify JWT ────────────────────────────────────────────────────────────
    _load_jwks()

    try:
        import jwt

        header = jwt.get_unverified_header(token)
        kid = header.get("kid", "")

        if kid not in _cache["keys"]:
            # Key not cached — force a refresh once
            _cache["fetched_at"] = 0.0
            _load_jwks()

        public_key = _cache["keys"].get(kid)
        if not public_key:
            raise ValueError(f"Unknown key ID: {kid!r}")

        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
        return payload

    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}") from exc


def require_org(payload: dict) -> str:
    """
    Extract org_id from JWT payload.
    Raises HTTP 403 if the user has no active organization.
    """
    org_id = payload.get("org_id")
    if not org_id:
        raise HTTPException(
            status_code=403,
            detail="No organization selected. Switch to an org in the app, then retry.",
        )
    return org_id


_VALID_ROLES = {"analyst", "senior_analyst", "partner", "admin"}


def get_role(payload: dict) -> str:
    """
    Map Clerk org_role → internal role string.

    Supports both:
    1. Clerk custom roles: org:admin | org:partner | org:senior_analyst | org:analyst
    2. Default built-in roles: org:admin | org:member
       → for "member", reads publicMetadata.role for sub-role assignment
    """
    raw = payload.get("org_role", "org:analyst")
    key = raw.replace("org:", "")

    if key == "admin":
        return "admin"
    if key in _VALID_ROLES:
        return key

    # Default "member" — check publicMetadata for sub-role
    if key == "member":
        meta = payload.get("org_public_metadata", {}) or {}
        meta_role = str(meta.get("role", "")).lower()
        if meta_role in _VALID_ROLES:
            return meta_role
        return "analyst"

    return "analyst"


# Permission sets per role
PERMISSIONS: dict[str, set[str]] = {
    "admin":           {"upload", "view", "delete", "edit_thesis", "invite"},
    "partner":         {"upload", "view", "delete", "edit_thesis"},
    "senior_analyst":  {"upload", "view", "delete"},
    "analyst":         {"upload", "view"},
}


def require_permission(payload: dict, permission: str) -> None:
    """
    Check whether the authenticated user's role includes `permission`.
    Raises HTTP 403 if not.
    """
    role = get_role(payload)
    if permission not in PERMISSIONS.get(role, set()):
        raise HTTPException(
            status_code=403,
            detail=f"Your role '{role}' does not have '{permission}' permission.",
        )
