"""Generic BaseRepository + concrete repositories with outbox integration."""

from __future__ import annotations

import json
import uuid
from typing import Any, Generic, TypeVar

from app.storage.database import Database, get_database
from app.storage.models import (
    Account,
    AccountSnapshot,
    AppLog,
    AuditLog,
    BacktestRun,
    BaseRowModel,
    CalendarEvent,
    DailyReport,
    DecisionTrace,
    HealthCheck,
    Journal,
    ModelVersion,
    Mt5Request,
    PerformanceMetric,
    RiskEvent,
    Session,
    Signal,
    StrategyConfig,
    Trade,
    TradeEvent,
)
from app.storage.outbox import Outbox

try:
    from app.observability.logger import get_logger

    _logger = get_logger(__name__)
except Exception:  # pragma: no cover
    import logging

    _logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseRowModel)


class BaseRepository(Generic[T]):
    """Generic CRUD repository that writes to outbox on mutations."""

    def __init__(self, db: Database | None, table: str, model_cls: type[T]) -> None:
        self._db: Database = db or get_database()
        self._table = table
        self._model_cls = model_cls
        self._outbox = Outbox(self._db)

    def insert(self, data: dict[str, Any] | T) -> str:
        """Insert a row and enqueue outbox. Returns record id."""
        if isinstance(data, BaseRowModel):
            payload = data.to_dict()
        else:
            payload = dict(data)
        if "id" not in payload or not payload["id"]:
            payload["id"] = str(uuid.uuid4())
        # Ensure JSON fields are stored as TEXT
        cols = ", ".join(payload.keys())
        placeholders = ", ".join(["?"] * len(payload))
        values = [json.dumps(v, default=str) if isinstance(v, dict | list) else v for v in payload.values()]
        with self._db.get_connection() as conn:
            conn.execute(f"INSERT INTO {self._table} ({cols}) VALUES ({placeholders})", values)
            conn.commit()
        self._outbox.enqueue(self._table, str(payload["id"]), "insert", payload)
        _logger.info("repo_insert", extra={"table": self._table, "id": payload["id"]})
        return str(payload["id"])

    def upsert(self, data: dict[str, Any] | T) -> str:
        """Insert or replace (SQLite INSERT OR REPLACE)."""
        if isinstance(data, BaseRowModel):
            payload = data.to_dict()
        else:
            payload = dict(data)
        if "id" not in payload or not payload["id"]:
            payload["id"] = str(uuid.uuid4())
        cols = ", ".join(payload.keys())
        placeholders = ", ".join(["?"] * len(payload))
        values = [json.dumps(v, default=str) if isinstance(v, dict | list) else v for v in payload.values()]
        with self._db.get_connection() as conn:
            conn.execute(f"INSERT OR REPLACE INTO {self._table} ({cols}) VALUES ({placeholders})", values)
            conn.commit()
        self._outbox.enqueue(self._table, str(payload["id"]), "upsert", payload)
        return str(payload["id"])

    def get_by_id(self, record_id: str) -> T | None:
        with self._db.get_connection() as conn:
            cur = conn.execute(f"SELECT * FROM {self._table} WHERE id = ?", (record_id,))
            row = cur.fetchone()
            if row is None:
                return None
            return self._model_cls.from_row(row)  # type: ignore[return-value]

    def list(self, limit: int = 100, offset: int = 0, where: str | None = None, params: tuple[Any, ...] = ()) -> list[T]:
        query = f"SELECT * FROM {self._table}"
        if where:
            query += f" WHERE {where}"
        query += " ORDER BY rowid DESC LIMIT ? OFFSET ?"
        with self._db.get_connection() as conn:
            cur = conn.execute(query, (*params, limit, offset))
            return [self._model_cls.from_row(r) for r in cur.fetchall()]  # type: ignore[misc]

    def update(self, record_id: str, patch: dict[str, Any]) -> None:
        if not patch:
            return
        sets = ", ".join([f"{k}=?" for k in patch.keys()])
        values = [json.dumps(v, default=str) if isinstance(v, dict | list) else v for v in patch.values()]
        with self._db.get_connection() as conn:
            conn.execute(f"UPDATE {self._table} SET {sets} WHERE id=?", (*values, record_id))
            conn.commit()
        self._outbox.enqueue(self._table, record_id, "update", patch)

    def delete(self, record_id: str) -> None:
        with self._db.get_connection() as conn:
            conn.execute(f"DELETE FROM {self._table} WHERE id=?", (record_id,))
            conn.commit()
        self._outbox.enqueue(self._table, record_id, "delete", {"id": record_id})

    def count(self, where: str | None = None, params: tuple[Any, ...] = ()) -> int:
        query = f"SELECT COUNT(*) as c FROM {self._table}"
        if where:
            query += f" WHERE {where}"
        with self._db.get_connection() as conn:
            cur = conn.execute(query, params)
            row = cur.fetchone()
            return int(row["c"]) if row else 0


# Concrete repositories — one per table for type-safe access


class AccountRepository(BaseRepository[Account]):
    def __init__(self, db: Database | None = None) -> None:
        super().__init__(db, "accounts", Account)


class SessionRepository(BaseRepository[Session]):
    def __init__(self, db: Database | None = None) -> None:
        super().__init__(db, "sessions", Session)


class StrategyConfigRepository(BaseRepository[StrategyConfig]):
    def __init__(self, db: Database | None = None) -> None:
        super().__init__(db, "strategy_configs", StrategyConfig)


class SignalRepository(BaseRepository[Signal]):
    def __init__(self, db: Database | None = None) -> None:
        super().__init__(db, "signals", Signal)


class DecisionTraceRepository(BaseRepository[DecisionTrace]):
    def __init__(self, db: Database | None = None) -> None:
        super().__init__(db, "decision_traces", DecisionTrace)


class TradeRepository(BaseRepository[Trade]):
    def __init__(self, db: Database | None = None) -> None:
        super().__init__(db, "trades", Trade)


class TradeEventRepository(BaseRepository[TradeEvent]):
    def __init__(self, db: Database | None = None) -> None:
        super().__init__(db, "trade_events", TradeEvent)


class Mt5RequestRepository(BaseRepository[Mt5Request]):
    def __init__(self, db: Database | None = None) -> None:
        super().__init__(db, "mt5_requests", Mt5Request)


class AccountSnapshotRepository(BaseRepository[AccountSnapshot]):
    def __init__(self, db: Database | None = None) -> None:
        super().__init__(db, "account_snapshots", AccountSnapshot)


class RiskEventRepository(BaseRepository[RiskEvent]):
    def __init__(self, db: Database | None = None) -> None:
        super().__init__(db, "risk_events", RiskEvent)


class ModelVersionRepository(BaseRepository[ModelVersion]):
    def __init__(self, db: Database | None = None) -> None:
        super().__init__(db, "model_versions", ModelVersion)


class BacktestRunRepository(BaseRepository[BacktestRun]):
    def __init__(self, db: Database | None = None) -> None:
        super().__init__(db, "backtest_runs", BacktestRun)


class JournalRepository(BaseRepository[Journal]):
    def __init__(self, db: Database | None = None) -> None:
        super().__init__(db, "journal", Journal)


class AuditLogRepository(BaseRepository[AuditLog]):
    def __init__(self, db: Database | None = None) -> None:
        super().__init__(db, "audit_log", AuditLog)


class AppLogRepository(BaseRepository[AppLog]):
    def __init__(self, db: Database | None = None) -> None:
        super().__init__(db, "app_logs", AppLog)


class HealthCheckRepository(BaseRepository[HealthCheck]):
    def __init__(self, db: Database | None = None) -> None:
        super().__init__(db, "health_checks", HealthCheck)


class PerformanceMetricRepository(BaseRepository[PerformanceMetric]):
    def __init__(self, db: Database | None = None) -> None:
        super().__init__(db, "performance_metrics", PerformanceMetric)


class DailyReportRepository(BaseRepository[DailyReport]):
    def __init__(self, db: Database | None = None) -> None:
        super().__init__(db, "daily_reports", DailyReport)


class CalendarEventRepository(BaseRepository[CalendarEvent]):
    def __init__(self, db: Database | None = None) -> None:
        super().__init__(db, "calendar_events", CalendarEvent)
