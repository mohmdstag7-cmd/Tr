"""Background Supabase sync via outbox pattern — QObject with Qt signals."""

from __future__ import annotations

import json
from typing import Any

try:
    from PyQt6.QtCore import QObject, QTimer, pyqtSignal  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - fallback for headless tests
    try:
        from PySide6.QtCore import QObject, QTimer  # type: ignore[import-not-found]
        from PySide6.QtCore import Signal as pyqtSignal
    except Exception:

        class _FakeSignal:  # type: ignore[no-redef]
            def __init__(self, *a: Any, **kw: Any) -> None:
                pass

            def emit(self, *a: Any, **kw: Any) -> None:
                pass

            def connect(self, *a: Any, **kw: Any) -> None:
                pass

        def pyqtSignal(*a: Any, **kw: Any) -> Any:  # type: ignore[no-redef]
            return _FakeSignal()

        class QObject:  # type: ignore[no-redef]
            def __init__(self, parent: Any | None = None) -> None:
                self._parent = parent

        class QTimer:  # type: ignore[no-redef]
            def __init__(self, parent: Any | None = None) -> None:
                self._interval = 0

            def setInterval(self, ms: int) -> None:
                self._interval = ms

            def timeout(self) -> Any:
                return _FakeSignal()

            def start(self) -> None:
                pass

            def stop(self) -> None:
                pass


from app.storage.database import Database, get_database
from app.storage.outbox import Outbox
from app.storage.supabase_client import SupabaseClient

try:
    from app.observability.logger import get_logger

    _logger = get_logger(__name__)
except Exception:  # pragma: no cover
    import logging

    _logger = logging.getLogger(__name__)


class SupabaseSync(QObject):
    """Background sync: reads outbox pending rows and upserts to Supabase.

    Qt signals allow UI to reflect sync state without polling.
    """

    sync_started = pyqtSignal()
    sync_finished = pyqtSignal(int)  # count synced
    sync_error = pyqtSignal(str)
    item_synced = pyqtSignal(str, str)  # table, record_id

    def __init__(
        self,
        db: Database | None = None,
        client: SupabaseClient | None = None,
        interval_ms: int = 30_000,
        parent: Any | None = None,
    ) -> None:
        super().__init__(parent)
        self._db: Database = db or get_database()
        self._outbox = Outbox(self._db)
        self._client = client or SupabaseClient()
        self._interval_ms = interval_ms
        self._timer: QTimer | None = None
        self._running = False

    def start(self) -> None:
        """Start background timer."""
        if self._timer is not None:
            return
        self._timer = QTimer(self)
        self._timer.setInterval(self._interval_ms)
        # connect timeout to process_outbox
        try:
            self._timer.timeout.connect(self.process_outbox)  # type: ignore[attr-defined]
        except Exception:
            pass
        self._timer.start()
        _logger.info("supabase_sync_started", extra={"interval_ms": self._interval_ms})

    def stop(self) -> None:
        if self._timer is not None:
            try:
                self._timer.stop()
            except Exception:
                pass
            self._timer = None
        _logger.info("supabase_sync_stopped")

    def process_outbox(self, batch_size: int = 50) -> int:
        """Process pending outbox entries. Returns number synced.

        Called by timer and can be invoked manually (e.g., tests).
        """
        if self._running:
            return 0
        self._running = True
        synced = 0
        try:
            self.sync_started.emit()
        except Exception:
            pass

        if not self._client.is_configured:
            _logger.info("supabase_sync_skipped_not_configured")
            self._running = False
            return 0

        pending = self._outbox.pending(limit=batch_size)
        for row in pending:
            outbox_id = str(row["id"])
            table = str(row["table_name"])
            record_id = str(row["record_id"])
            operation = str(row["operation"])
            payload_raw = str(row["payload"])
            try:
                payload: dict[str, Any] = json.loads(payload_raw) if payload_raw else {}
            except json.JSONDecodeError:
                payload = {"id": record_id, "raw": payload_raw}

            try:
                if operation == "delete":
                    self._client.delete(table, record_id)
                else:
                    # insert/update/upsert all map to upsert for idempotency
                    self._client.upsert(table, payload)
                self._outbox.mark_synced(outbox_id)
                synced += 1
                try:
                    self.item_synced.emit(table, record_id)
                except Exception:
                    pass
            except Exception as exc:
                err = str(exc)[:2000]
                self._outbox.mark_failed(outbox_id, err)
                _logger.warning("supabase_sync_item_failed", extra={"table": table, "record_id": record_id, "error": err})
                try:
                    self.sync_error.emit(err)
                except Exception:
                    pass

        self._running = False
        try:
            self.sync_finished.emit(synced)
        except Exception:
            pass
        if synced:
            _logger.info("supabase_sync_batch_done", extra={"synced": synced})
        return synced
