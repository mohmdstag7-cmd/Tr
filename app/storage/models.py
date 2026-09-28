"""Pydantic v2 models for every storage table.

Each model provides to_dict() and from_row() helpers.
"""

from __future__ import annotations

import sqlite3
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field


class BaseRowModel(BaseModel):
    """Base with helpers."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore", populate_by_name=True)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict suitable for SQLite / Supabase payload."""
        return self.model_dump(mode="json", exclude_none=False)

    @classmethod
    def from_row(cls, row: sqlite3.Row | dict[str, Any]):  # type: ignore[override]
        """Create instance from sqlite3.Row or dict."""
        if isinstance(row, sqlite3.Row):
            data = dict(row)
        else:
            data = dict(row)
        # JSON fields that may be stored as TEXT need not be parsed here; keep as string if needed
        return cls.model_validate(data)


# --- Table models ---


class Account(BaseRowModel):
    id: str
    login: int
    server: str
    name: str | None = None
    currency: str | None = None
    balance: float = 0
    equity: float = 0
    leverage: int | None = None
    created_at: str | None = None
    updated_at: str | None = None


class Session(BaseRowModel):
    id: str
    account_id: str
    started_at: str
    ended_at: str | None = None
    status: str = "active"
    terminal_info: str | None = None
    created_at: str | None = None


class StrategyConfig(BaseRowModel):
    id: str
    name: str
    version: str = "1.0.0"
    params: str = Field(default="{}")
    description: str | None = None
    is_active: int = 1
    created_at: str | None = None
    updated_at: str | None = None


class Signal(BaseRowModel):
    id: str
    time: str
    symbol: str
    strategy: str
    strategy_config_id: str | None = None
    direction: str
    price: float
    sl: float | None = None
    tp: float | None = None
    confidence: float | None = None
    meta: str = Field(default="{}")
    created_at: str | None = None


class DecisionTrace(BaseRowModel):
    id: str
    signal_id: str
    decision: str
    reason: str | None = None
    risk_check: str | None = None
    trace: str = Field(default="{}")
    created_at: str | None = None


class Trade(BaseRowModel):
    id: str
    ticket: int | None = None
    symbol: str
    mode: str
    side: str
    volume: float
    open_price: float | None = None
    close_price: float | None = None
    sl: float | None = None
    tp: float | None = None
    open_time: str | None = None
    close_time: str | None = None
    profit: float = 0
    swap: float = 0
    commission: float = 0
    strategy: str | None = None
    strategy_config_id: str | None = None
    signal_id: str | None = None
    status: str = "open"
    magic: int | None = None
    comment: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class TradeEvent(BaseRowModel):
    id: str
    trade_id: str
    event_type: str
    price: float | None = None
    volume: float | None = None
    time: str
    meta: str = Field(default="{}")


class Mt5Request(BaseRowModel):
    id: str
    method: str
    params: str = Field(default="{}")
    response: str | None = None
    duration_ms: int | None = None
    status: str = "ok"
    error: str | None = None
    created_at: str | None = None


class AccountSnapshot(BaseRowModel):
    id: str
    account_id: str
    time: str
    balance: float
    equity: float
    margin: float | None = None
    free_margin: float | None = None
    margin_level: float | None = None
    profit: float = 0
    created_at: str | None = None


class RiskEvent(BaseRowModel):
    id: str
    time: str
    account_id: str | None = None
    type: str
    severity: str
    message: str
    meta: str = Field(default="{}")
    created_at: str | None = None


class ModelVersion(BaseRowModel):
    id: str
    name: str
    version: str
    path: str | None = None
    metrics: str = Field(default="{}")
    stage: str = "dev"
    created_at: str | None = None


class BacktestRun(BaseRowModel):
    id: str
    strategy_config_id: str | None = None
    model_version_id: str | None = None
    started_at: str
    ended_at: str | None = None
    params: str = Field(default="{}")
    results: str = Field(default="{}")
    status: str = "running"
    created_at: str | None = None


class Journal(BaseRowModel):
    id: str
    time: str
    title: str
    content: str | None = None
    tags: str = Field(default="[]")
    trade_id: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class AuditLog(BaseRowModel):
    id: str
    time: str
    user: str | None = None
    action: str
    entity: str
    entity_id: str | None = None
    details: str = Field(default="{}")
    created_at: str | None = None


class AppLog(BaseRowModel):
    id: str
    time: str
    level: str
    category: str
    message: str
    meta: str = Field(default="{}")
    created_at: str | None = None


class HealthCheck(BaseRowModel):
    id: str
    time: str
    component: str
    status: str
    latency_ms: int | None = None
    details: str = Field(default="{}")
    created_at: str | None = None


class PerformanceMetric(BaseRowModel):
    id: str
    time: str
    metric: str
    value: float
    bucket: str | None = None
    meta: str = Field(default="{}")
    created_at: str | None = None


class DailyReport(BaseRowModel):
    id: str
    date: str
    content: str | None = None
    metrics: str = Field(default="{}")
    created_at: str | None = None


class CalendarEvent(BaseRowModel):
    id: str
    time: str
    title: str
    importance: str | None = None
    currency: str | None = None
    forecast: str | None = None
    previous: str | None = None
    actual: str | None = None
    meta: str = Field(default="{}")
    created_at: str | None = None


class OutboxRecord(BaseRowModel):
    id: str
    table_name: str
    record_id: str
    operation: str
    payload: str = Field(default="{}")
    created_at: str | None = None
    synced_at: str | None = None
    attempts: int = 0
    last_error: str | None = None
    status: str = "pending"


# Helper to map table names to models (used by repositories)
TABLE_MODEL_MAP: dict[str, type[BaseRowModel]] = {
    "accounts": Account,
    "sessions": Session,
    "strategy_configs": StrategyConfig,
    "signals": Signal,
    "decision_traces": DecisionTrace,
    "trades": Trade,
    "trade_events": TradeEvent,
    "mt5_requests": Mt5Request,
    "account_snapshots": AccountSnapshot,
    "risk_events": RiskEvent,
    "model_versions": ModelVersion,
    "backtest_runs": BacktestRun,
    "journal": Journal,
    "audit_log": AuditLog,
    "app_logs": AppLog,
    "health_checks": HealthCheck,
    "performance_metrics": PerformanceMetric,
    "daily_reports": DailyReport,
    "calendar_events": CalendarEvent,
    "outbox": OutboxRecord,
}
