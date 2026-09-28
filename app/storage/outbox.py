"""Outbox pattern — local SQLite is source of truth."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from typing import Any

try:
    from app.observability.logger import get_logger

    _logger = get_logger(__name__)
except Exception:  # pragma: no cover
    import logging

    _logger = logging.getLogger(__name__)

from app.storage.database import Database, get_database


class Outbox:
    """Manage outbox table for Supabase sync."""

    def __init__(self, db: Database | None = None) -> None:
        self._db: Database = db or get_database()

    def enqueue(self, table_name: str, record_id: str, operation: str, payload: dict[str, Any] | str) -> str:
        """Insert an outbox entry. Returns outbox id."""
        outbox_id = str(uuid.uuid4())
        payload_str = json.dumps(payload, default=str) if isinstance(payload, dict) else str(payload)
        now = datetime.now(UTC).isoformat()
        with self._db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO outbox (id, table_name, record_id, operation, payload, created_at, status, attempts)
                VALUES (?, ?, ?, ?, ?, ?, 'pending', 0)
                """,
                (outbox_id, table_name, record_id, operation, payload_str, now),
            )
            conn.commit()
        _logger.info("outbox_enqueued", extra={"table": table_name, "record_id": record_id, "operation": operation})
        return outbox_id

    def pending(self, limit: int = 100) -> list[sqlite3.Row]:
        """Return pending outbox rows ordered by created_at."""
        with self._db.get_connection() as conn:
            cur = conn.execute("SELECT * FROM outbox WHERE status = 'pending' ORDER BY created_at ASC LIMIT ?", (limit,))
            return cur.fetchall()

    def mark_synced(self, outbox_id: str) -> None:
        now = datetime.now(UTC).isoformat()
        with self._db.get_connection() as conn:
            conn.execute("UPDATE outbox SET status='synced', synced_at=?, attempts=attempts+1 WHERE id=?", (now, outbox_id))
            conn.commit()
        _logger.info("outbox_synced", extra={"outbox_id": outbox_id})

    def mark_failed(self, outbox_id: str, error: str) -> None:
        with self._db.get_connection() as conn:
            conn.execute("UPDATE outbox SET status='failed', last_error=?, attempts=attempts+1 WHERE id=?", (error[:2000], outbox_id))
            conn.commit()
        _logger.warning("outbox_failed", extra={"outbox_id": outbox_id, "error": error})

    def retry_failed(self, outbox_id: str) -> None:
        with self._db.get_connection() as conn:
            conn.execute("UPDATE outbox SET status='pending', last_error=NULL WHERE id=?", (outbox_id,))
            conn.commit()

    def count_pending(self) -> int:
        with self._db.get_connection() as conn:
            cur = conn.execute("SELECT COUNT(*) as c FROM outbox WHERE status='pending'")
            row = cur.fetchone()
            return int(row["c"]) if row else 0
