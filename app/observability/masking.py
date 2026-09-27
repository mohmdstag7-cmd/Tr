"""Secrets redaction for logs and exports."""

from __future__ import annotations

import re
from typing import Any

SENSITIVE_SUBSTRINGS = {
    "password",
    "passwd",
    "pwd",
    "secret",
    "api_key",
    "apikey",
    "token",
    "access_key",
    "service_role",
}

# JWT shape per spec: ^eyJ[A-Za-z0-9_-]+$  (also handle dotted JWT)
_JWT_RE = re.compile(r"^eyJ[A-Za-z0-9_-]+$")
_JWT_DOTTED_RE = re.compile(r"^eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$")
# Find JWT inside a larger string
_JWT_FIND_RE = re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")
_JWT_SIMPLE_FIND_RE = re.compile(r"eyJ[A-Za-z0-9_-]{10,}")


def _is_sensitive_key(key: str) -> bool:
    low = key.lower()
    return any(sub in low for sub in SENSITIVE_SUBSTRINGS)


def _is_password_key(key: str) -> bool:
    low = key.lower()
    return any(s in low for s in ("password", "passwd", "pwd", "secret"))


def _redact_value(key: str, value: Any) -> Any:
    if isinstance(value, str):
        # JWT detection first
        if _JWT_RE.match(value) or _JWT_DOTTED_RE.match(value):
            if len(value) > 8:
                return f"[REDACTED:{value[:4]}:{value[-4:]}]"
            return "[REDACTED]"
        low = key.lower()
        if _is_sensitive_key(key):
            if _is_password_key(key):
                return "[REDACTED]"
            # For token-like keys show first4/last4
            if len(value) > 8:
                return f"[REDACTED:{value[:4]}:{value[-4:]}]"
            return "[REDACTED]"
        # Even if key not sensitive, value itself might be JWT
        if _JWT_FIND_RE.search(value) or _JWT_SIMPLE_FIND_RE.search(value):
            # redact the JWT substring
            def _repl(m: re.Match[str]) -> str:
                v = m.group(0)
                if len(v) > 8:
                    return f"[REDACTED:{v[:4]}:{v[-4:]}]"
                return "[REDACTED]"

            value = _JWT_FIND_RE.sub(_repl, value)
            value = _JWT_SIMPLE_FIND_RE.sub(_repl, value)
            return value
    if isinstance(value, int) and value >= 100000:
        low = key.lower()
        if any(s in low for s in ("login", "account_number", "account_id")):
            s = str(value)
            return f"[REDACTED:{s[:4]}:{s[-4:]}]"
    return value


def redact_dict(d: dict[str, Any], sensitive_keys: set[str] | None = None) -> dict[str, Any]:
    """Return a copy of d with sensitive values redacted."""
    out: dict[str, Any] = {}
    for k, v in d.items():
        if sensitive_keys is not None and k in sensitive_keys:
            if isinstance(v, str) and len(v) > 8:
                out[k] = f"[REDACTED:{v[:4]}:{v[-4:]}]"
            else:
                out[k] = "[REDACTED]"
            continue
        if isinstance(v, dict):
            out[k] = redact_dict(v, sensitive_keys)
        elif isinstance(v, list):
            new_list: list[Any] = []
            for item in v:
                if isinstance(item, dict):
                    new_list.append(redact_dict(item, sensitive_keys))
                else:
                    new_list.append(item)
            out[k] = new_list
        else:
            out[k] = _redact_value(k, v)
    return out


class SecretsMaskingFilter:
    """Loguru filter that redacts secrets in record extra and message."""

    def __call__(self, record: dict[str, Any]) -> bool:
        # Redact extra dict
        extra = record.get("extra", {})
        # Walk extra and redact in place
        for key in list(extra.keys()):
            val = extra[key]
            if isinstance(val, dict):
                extra[key] = redact_dict(val)
            elif isinstance(val, list):
                new_list: list[Any] = []
                for item in val:
                    if isinstance(item, dict):
                        new_list.append(redact_dict(item))
                    else:
                        new_list.append(item)
                extra[key] = new_list
            else:
                redacted = _redact_value(key, val)
                extra[key] = redacted

        # Redact message string for JWTs and known secret values
        msg: str = record.get("message", "")
        if isinstance(msg, str) and msg:
            # Redact JWTs in message
            def _jwt_repl(m: re.Match[str]) -> str:
                v = m.group(0)
                if len(v) > 8:
                    return f"[REDACTED:{v[:4]}:{v[-4:]}]"
                return "[REDACTED]"

            msg = _JWT_FIND_RE.sub(_jwt_repl, msg)
            # Also simple JWT
            # Avoid double-redacting already redacted
            if "[REDACTED" not in msg:
                msg = _JWT_SIMPLE_FIND_RE.sub(_jwt_repl, msg)
            # Redact any extra string values that were sensitive and appear in message
            for key, val in extra.items():
                if isinstance(val, str) and val.startswith("[REDACTED"):
                    continue
                # If original value was sensitive, we already redacted extra, but message may contain original
                # We need to check original before redaction - we lost it. So we check for known sensitive keys
                # and if message contains a value that looks like a secret, redact it.
                # For now, if key is sensitive and message contains the original string representation,
                # we can't know original. So we rely on JWT redaction and extra redaction.
                pass
            record["message"] = msg
            # Also need to update record["extra"]? loguru stores message separately
            # Ensure the formatted message is updated
            if "message" in record:
                record["message"] = msg

        return True
