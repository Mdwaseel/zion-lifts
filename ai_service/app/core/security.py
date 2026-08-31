"""Authentication dependencies for public and internal routes."""

from __future__ import annotations

import hmac

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.core.config import Settings, get_settings

API_KEY_HEADER = "X-API-Key"
INTERNAL_TOKEN_HEADER = "X-Internal-Token"

_api_key_scheme = APIKeyHeader(name=API_KEY_HEADER, auto_error=False)
_internal_scheme = APIKeyHeader(name=INTERNAL_TOKEN_HEADER, auto_error=False)


def _matches_any(candidate: str, allowed: list[str]) -> bool:
    return any(hmac.compare_digest(candidate, valid) for valid in allowed)


async def require_api_key(
    api_key: str | None = Security(_api_key_scheme),
    settings: Settings = Depends(get_settings),
) -> str:
    """Guard public endpoints. Auth is skipped when no keys are configured."""
    if not settings.api_keys:
        return "anonymous"
    if not api_key or not _matches_any(api_key, settings.api_keys):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
            headers={"WWW-Authenticate": API_KEY_HEADER},
        )
    return api_key


async def require_internal_token(
    token: str | None = Security(_internal_scheme),
    settings: Settings = Depends(get_settings),
) -> None:
    """Guard operator-only endpoints; always enforced."""
    if not token or not hmac.compare_digest(token, settings.internal_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Internal access denied.",
        )
