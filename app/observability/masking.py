"""Secrets masking for loguru records and exports."""

from __future__ import annotations

import re
from typing import Any

# Substrings (case-insensitive) that mark a key as sensitive. Extended per
# SPEC Part D5 + the Phase 1-3 audit (C5/M4): supabase_url, authorization,
# bearer, private_key, cookie, client_id, session, credentials.
SENSITIVE_SUBSTRINGS: frozenset[str] = frozenset(
    {
        "password",
        "passwd",
        "pwd",
        "secret",
        "api_key",
        "apikey",
        "token",
        "access_key",
        "service_role",
        "authorization",
        "bearer",
        "private_key",
        "cookie",
        "supabase_key",
        "supabase_url",
        "supabase_anon_key",
        "client_id",
        "client_secret",
        "session",
        "credentials",
        "mt5_password",
    }
)

# JWT-shaped strings (header.payload.signature, base64-url segments).
# A JWT has 3 parts separated by dots, each part is base64url chars.
_JWT_FIND_RE = re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b")
# Also catch simple JWT-like prefixes (some services use a 'jwt:' prefix).
_JWT_SIMPLE_FIND_RE = re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\b")

# Inline ``key=value`` style secrets that may appear inside f-string-formatted
# log messages (e.g. ``logger.info(f"connecting as user={u} pwd={pwd}")``).
# Matches both ``key=value`` and ``key: value`` patterns. The match captures
# the key in group 1 and the separator in group 2; we replace everything
# after the separator with ``***``.
_SENSITIVE_KV_RE = re.compile(
    r"(?i)\b(pwd|password|passwd|secret|token|bearer|authorization|cookie|api_key|apikey|supabase_key|supabase_anon_key|client_secret|private_key)\b(\s*[:=]\s*)(\S+)"
)


def _looks_sensitive(key: str) -> bool:
    """Return True if ``key`` matches any sensitive substring (case-insensitive)."""
    if not isinstance(key, str):
        return False
    lowered = key.lower()
    return any(sub in lowered for sub in SENSITIVE_SUBSTRINGS)


def _redact_value(value: Any) -> Any:
    """Return a redacted form of ``value`` for inclusion in logs/exports.

    Strings longer than 8 chars are shown as ``[REDACTED:first4:last4]`` so
    the user can confirm they're using the right key without seeing it.
    Short strings are fully replaced with ``[REDACTED]``.
    """
    if isinstance(value, str):
        if len(value) <= 8:
            return "[REDACTED]"
        return f"[REDACTED:{value[:4]}:{value[-4:]}]"
    if isinstance(value, dict):
        return redact_dict(value)
    if isinstance(value, list):
        return [_redact_value(v) for v in value]
    if isinstance(value, tuple):
        return tuple(_redact_value(v) for v in value)
    # Numbers (account login, etc.) — keep them; they aren't secrets.
    return value


def redact_dict(d: dict[str, Any] | None) -> dict[str, Any]:
    """Return a copy of ``d`` with sensitive values redacted.

    Walks nested dicts/lists. Keys are matched case-insensitively against
    :data:`SENSITIVE_SUBSTRINGS`.
    """
    if d is None:
        return {}
    if not isinstance(d, dict):
        return d  # type: ignore[unreachable]
    out: dict[str, Any] = {}
    for key, value in d.items():
        if _looks_sensitive(key) if isinstance(key, str) else False:
            out[key] = _redact_value(value)
        elif isinstance(value, dict):
            out[key] = redact_dict(value)
        elif isinstance(value, list):
            out[key] = [redact_dict(v) if isinstance(v, dict) else _redact_value(v) if isinstance(v, str) else v for v in value]
        else:
            out[key] = value
    return out


def _scrub_message(msg: str) -> str:
    """Redact inline ``key=value`` style secrets in a log message string.

    Also redacts JWT-shaped substrings.
    """
    if not isinstance(msg, str):
        return msg

    # 1. key=value / key: value patterns
    msg = _SENSITIVE_KV_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}***", msg)

    # 2. JWT tokens (full 3-part form first, then simple prefix)
    msg = _JWT_FIND_RE.sub("[REDACTED:JWT]", msg)
    msg = _JWT_SIMPLE_FIND_RE.sub("[REDACTED:JWT]", msg)

    return msg


class SecretsMaskingFilter:
    """Loguru filter that redacts secrets from record extras and message.

    The filter is registered with ``logger.add(filter=SecretsMaskingFilter())``
    or via :func:`app.observability.logger.configure_logging`. It walks:

    * ``record["extra"]``: any key matching :data:`SENSITIVE_SUBSTRINGS`
      has its value replaced with ``[REDACTED:...]``.
    * ``record["message"]``: inline ``key=value`` patterns and JWT-shaped
      substrings are scrubbed.
    """

    def __init__(self, sensitive_keys: set[str] | None = None) -> None:
        # Allow tests to pass a custom set; defaults to the module-level set.
        self._sensitive_keys = sensitive_keys or set(SENSITIVE_SUBSTRINGS)

    def _is_sensitive_key(self, key: str) -> bool:
        if not isinstance(key, str):
            return False
        lowered = key.lower()
        return any(sub in lowered for sub in self._sensitive_keys)

    def __call__(self, record: dict[str, Any]) -> bool:  # noqa: D401
        """Filter callback: mutate ``record`` in place; always return True."""
        # Walk extra and redact sensitive values.
        extra = record.get("extra")
        if isinstance(extra, dict):
            for key in list(extra.keys()):
                if self._is_sensitive_key(key):
                    extra[key] = _redact_value(extra[key])
        # Scrub the message string.
        msg = record.get("message")
        if isinstance(msg, str):
            record["message"] = _scrub_message(msg)
        return True
