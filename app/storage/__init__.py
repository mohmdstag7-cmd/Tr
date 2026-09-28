"""Storage package — SQLite + Outbox + Supabase sync.

Re-exports public API for Phase 4.
"""

from __future__ import annotations

from app.storage.database import Database, get_database
from app.storage.outbox import Outbox
from app.storage.repositories import (
    AccountRepository,
    AccountSnapshotRepository,
    AppLogRepository,
    AuditLogRepository,
    BacktestRunRepository,
    BaseRepository,
    CalendarEventRepository,
    DailyReportRepository,
    DecisionTraceRepository,
    HealthCheckRepository,
    JournalRepository,
    ModelVersionRepository,
    Mt5RequestRepository,
    PerformanceMetricRepository,
    RiskEventRepository,
    SessionRepository,
    SignalRepository,
    StrategyConfigRepository,
    TradeEventRepository,
    TradeRepository,
)
from app.storage.supabase_sync import SupabaseSync

__all__ = [
    "Database",
    "get_database",
    "Outbox",
    "SupabaseSync",
    "BaseRepository",
    "AccountRepository",
    "SessionRepository",
    "StrategyConfigRepository",
    "SignalRepository",
    "DecisionTraceRepository",
    "TradeRepository",
    "TradeEventRepository",
    "Mt5RequestRepository",
    "AccountSnapshotRepository",
    "RiskEventRepository",
    "ModelVersionRepository",
    "BacktestRunRepository",
    "JournalRepository",
    "AuditLogRepository",
    "AppLogRepository",
    "HealthCheckRepository",
    "PerformanceMetricRepository",
    "DailyReportRepository",
    "CalendarEventRepository",
]
