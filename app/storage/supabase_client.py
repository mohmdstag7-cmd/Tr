"""Supabase client wrapper — secrets via keyring, never in code/logs."""

from __future__ import annotations

from typing import Any

try:
    import keyring  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    keyring = None  # type: ignore[assignment]

try:
    from supabase import Client, create_client  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    Client = Any  # type: ignore[assignment,misc]
    create_client = None  # type: ignore[assignment]

try:
    from app.observability.logger import get_logger

    _logger = get_logger(__name__)
except Exception:  # pragma: no cover
    import logging

    _logger = logging.getLogger(__name__)


class SupabaseClient:
    """Thin wrapper around supabase-py with keyring secret handling."""

    def __init__(self, url: str | None = None, anon_key: str | None = None, client: Any | None = None) -> None:
        # Allow injection for tests
        if client is not None:
            self._client = client
            self.url = url or "injected"
            return

        resolved_url = url
        resolved_key = anon_key

        # Try keyring / env fallback
        if resolved_key is None and keyring is not None:
            try:
                resolved_key = keyring.get_password("mt5tw", "supabase_anon_key")
            except Exception:
                resolved_key = None

        if resolved_url is None:
            # Try keyring for url as well
            if keyring is not None:
                try:
                    resolved_url = keyring.get_password("mt5tw", "supabase_url")
                except Exception:
                    resolved_url = None

        # Env fallback
        import os

        resolved_url = resolved_url or os.environ.get("SUPABASE_URL", "")
        resolved_key = resolved_key or os.environ.get("SUPABASE_ANON_KEY", "")

        self.url = resolved_url or ""  # type: ignore[no-redef]
        self._anon_key = resolved_key or ""  # type: ignore[no-redef]

        if resolved_url and resolved_key and create_client is not None:
            try:
                self._client = create_client(resolved_url, resolved_key)
                _logger.info("supabase_client_created", extra={"url": resolved_url})
            except Exception as exc:  # pragma: no cover
                _logger.warning("supabase_client_failed", extra={"error": str(exc)})
                self._client = None
        else:
            _logger.info("supabase_client_not_configured")

    @property
    def is_configured(self) -> bool:
        return self._client is not None

    def upsert(self, table: str, data: dict[str, Any], on_conflict: str = "id") -> dict[str, Any]:
        """Upsert a record. Returns response data or raises."""
        if self._client is None:
            raise RuntimeError("Supabase client not configured — missing URL or anon key in keyring/env")
        # Never log payload containing secrets; payload here is safe but we avoid logging full data
        _logger.info("supabase_upsert", extra={"table": table})
        # supabase-py API: table(...).upsert(...).execute()
        result = self._client.table(table).upsert(data, on_conflict=on_conflict).execute()
        return {"data": getattr(result, "data", None)}

    def delete(self, table: str, record_id: str) -> dict[str, Any]:
        if self._client is None:
            raise RuntimeError("Supabase client not configured")
        result = self._client.table(table).delete().eq("id", record_id).execute()
        return {"data": getattr(result, "data", None)}

    def health_check(self) -> bool:
        if self._client is None:
            return False
        try:
            # Lightweight query
            self._client.table("accounts").select("id").limit(1).execute()
            return True
        except Exception:
            return False
