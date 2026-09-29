"""Fail-closed destination policy for credential-bearing qualification calls."""
from __future__ import annotations

import os
import urllib.parse


def _normalize_custom_url(value: str) -> str:
    value = (value or "").strip()
    try:
        parsed = urllib.parse.urlsplit(value)
        loopback = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
        if not parsed.hostname or (parsed.scheme != "https" and not (parsed.scheme == "http" and loopback)):
            raise ValueError
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError
        if any(ord(ch) < 33 for ch in value):
            raise ValueError
    except (ValueError, TypeError, AttributeError):
        raise ValueError("custom qualification base URL must be credential-free HTTPS or loopback HTTP") from None
    return value.rstrip("/")


def allowed_custom_base_urls(raw: str | None = None) -> frozenset[str]:
    raw = os.environ.get("RESIDUAL_QUALIFICATION_ALLOWED_BASE_URLS", "") if raw is None else raw
    values = [item.strip() for item in raw.replace("\n", ",").split(",") if item.strip()]
    return frozenset(_normalize_custom_url(value) for value in values)


def require_allowed_credential_destination(provider: str, base_url: str | None, *, allowlist: str | None = None) -> str | None:
    """Return a normalized custom URL or fail before any credential-bearing request.

    Built-in provider defaults are selected only when base_url is absent.
    Every explicit override, including openai_compatible, must be present in the
    operator-controlled allowlist. Ollama is credential-free in qualification
    and is therefore outside this guard.
    """
    if provider == "ollama" or not base_url:
        return base_url.rstrip("/") if base_url else None
    normalized = _normalize_custom_url(base_url)
    parsed = urllib.parse.urlsplit(normalized)
    loopback = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    # Loopback HTTP is an explicit same-host qualification exception. Remote
    # overrides remain HTTPS + operator allowlist only.
    if loopback and parsed.scheme == "http":
        return normalized
    allowed = allowed_custom_base_urls(allowlist)
    if normalized not in allowed:
        raise ValueError(
            "custom qualification base URL is not in RESIDUAL_QUALIFICATION_ALLOWED_BASE_URLS"
        )
    return normalized
