"""Observability package public API."""

from __future__ import annotations

from app.observability.audit import AuditEntry, AuditLog, audit_log
from app.observability.categories import LOG_CATEGORIES, Category, is_valid_category
from app.observability.context import (
    bind_context,
    current_context,
    get_session_id,
    get_trace_id,
    new_session_id,
    new_trace_id,
    set_session_id,
    set_trace_id,
)
from app.observability.crash_handler import (
    crash_occurred,
    get_crash_dir,
    install_crash_handler,
)
from app.observability.debug_bundle import create_debug_bundle, masked_settings
from app.observability.decision_trace import DecisionStep, DecisionTrace, DecisionTraceStore, render_decision_trace
from app.observability.health import HealthCheck, HealthRegistry, health_registry
from app.observability.logger import configure_logging, enable_debug_mode, get_log_dir, get_logger, set_level
from app.observability.masking import SecretsMaskingFilter, redact_dict
from app.observability.metrics import LatencyHistogram, PerformanceMetrics, metrics
from app.observability.watchdog import Watchdog, WorkerStatus, watchdog

__all__ = [
    "LOG_CATEGORIES",
    "Category",
    "is_valid_category",
    "get_logger",
    "set_session_id",
    "get_session_id",
    "new_session_id",
    "set_trace_id",
    "get_trace_id",
    "new_trace_id",
    "bind_context",
    "current_context",
    "SecretsMaskingFilter",
    "redact_dict",
    "configure_logging",
    "get_log_dir",
    "set_level",
    "enable_debug_mode",
    "DecisionStep",
    "DecisionTrace",
    "DecisionTraceStore",
    "render_decision_trace",
    "install_crash_handler",
    "get_crash_dir",
    "crash_occurred",
    "WorkerStatus",
    "Watchdog",
    "watchdog",
    "AuditEntry",
    "AuditLog",
    "audit_log",
    "HealthCheck",
    "HealthRegistry",
    "health_registry",
    "LatencyHistogram",
    "PerformanceMetrics",
    "metrics",
    "create_debug_bundle",
    "masked_settings",
]
