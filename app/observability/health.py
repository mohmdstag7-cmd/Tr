"""Health checks registry."""

from __future__ import annotations

import socket
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from PySide6.QtCore import QObject, QTimer, Signal
except Exception:

    class QObject:  # type: ignore[no-redef]
        def __init__(self, *a: object, **k: object) -> None:
            pass

    class Signal:  # type: ignore[no-redef]
        def __init__(self, *a: object, **k: object) -> None:
            pass

        def emit(self, *a: object, **k: object) -> None:
            pass

        def connect(self, *a: object, **k: object) -> None:
            pass

    class QTimer:  # type: ignore[no-redef]
        def __init__(self, *a: object, **k: object) -> None:
            pass

        def setInterval(self, *a: object, **k: object) -> None:
            pass

        def start(self, *a: object, **k: object) -> None:
            pass

        def stop(self) -> None:
            pass

        timeout = Signal()


@dataclass
class HealthCheck:
    name: str
    status: str  # ok, warning, error, unknown
    message: str
    value: Any | None = None
    last_checked: datetime | None = None


HealthChecker = Callable[[], HealthCheck]


class HealthRegistry(QObject):
    health_changed = Signal(dict)  # type: ignore[assignment]

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._checkers: dict[str, HealthChecker] = {}
        self._latest: dict[str, HealthCheck] = {}
        # Construct the QTimer but DON'T start it here. ``__init__`` runs at
        # module import time (the singleton is created at
        # ``app/observability/__init__.py`` import), which is BEFORE
        # ``QApplication`` exists. Starting a QTimer without a QApplication
        # silently fails (Phase 1-3 audit C9). Callers must call
        # :meth:`start` after the QApplication is created (typically in
        # ``app/main.py`` after ``app = QApplication([])``).
        self._timer = QTimer(self)
        self._timer.setInterval(60000)
        try:
            self._timer.timeout.connect(self._run_all)  # type: ignore[attr-defined]
        except Exception:
            pass
        self._register_builtin()

    def start(self) -> None:
        """Start the periodic 60s health-check timer.

        Must be called after :class:`QApplication` is created. Idempotent —
        safe to call multiple times.
        """
        try:
            if not self._timer.isActive():
                self._timer.start()
        except Exception:
            pass

    def stop(self) -> None:
        """Stop the periodic health-check timer."""
        try:
            self._timer.stop()
        except Exception:
            pass

    def register(self, name: str, checker: HealthChecker) -> None:
        self._checkers[name] = checker

    def run_all(self) -> dict[str, HealthCheck]:
        results: dict[str, HealthCheck] = {}
        for name, checker in self._checkers.items():
            try:
                hc = checker()
                if hc.last_checked is None:
                    hc.last_checked = datetime.now(UTC)
                results[name] = hc
            except Exception as e:
                results[name] = HealthCheck(
                    name=name,
                    status="error",
                    message=f"Checker failed: {e}",
                    last_checked=datetime.now(UTC),
                )
        self._latest = results
        try:
            self.health_changed.emit(results)  # type: ignore[attr-defined]
        except Exception:
            pass
        return results

    def run_one(self, name: str) -> HealthCheck:
        checker = self._checkers.get(name)
        if checker is None:
            return HealthCheck(name=name, status="unknown", message="No such check", last_checked=datetime.now(UTC))
        try:
            hc = checker()
            if hc.last_checked is None:
                hc.last_checked = datetime.now(UTC)
            self._latest[name] = hc
            return hc
        except Exception as e:
            hc = HealthCheck(name=name, status="error", message=str(e), last_checked=datetime.now(UTC))
            self._latest[name] = hc
            return hc

    def set_gateway(self, gateway: object) -> None:
        """Wire up a real MT5Gateway so the MT5-related checks return real values.

        Without this, the MT5 checks return UNKNOWN. Called by MainWindow at
        startup once the gateway is constructed.
        """
        self._gateway = gateway

    @property
    def gateway(self) -> object | None:
        return getattr(self, "_gateway", None)

    def _run_all(self) -> None:
        self.run_all()

    def _register_builtin(self) -> None:
        self.register("mt5_connected", _check_mt5_connected)
        self.register("algo_trading_enabled", _check_algo_trading)
        self.register("quotes_fresh", _check_quotes_fresh)
        self.register("broker_offset_stable", _check_broker_offset)
        self.register("supabase_reachable", _check_supabase)
        self.register("sync_queue_size", _check_sync_queue)
        self.register("disk_space", _check_disk_space)
        self.register("log_size", _check_log_size)
        self.register("internet_latency", _check_internet_latency)
        self.register("pc_clock_drift", _check_clock_drift)


def _check_mt5_connected() -> HealthCheck:
    gw = health_registry.gateway
    if gw is None:
        return HealthCheck(
            name="mt5_connected",
            status="unknown",
            message="MT5Gateway not wired up yet (Phase 3+)",
            last_checked=datetime.now(UTC),
        )
    try:
        # The gateway exposes is_connected() which returns True/False.
        is_conn = bool(gw.is_connected())  # type: ignore[attr-defined]
        if is_conn:
            return HealthCheck(
                name="mt5_connected",
                status="ok",
                message="MT5 terminal connected",
                value=is_conn,
                last_checked=datetime.now(UTC),
            )
        return HealthCheck(
            name="mt5_connected",
            status="error",
            message="MT5 terminal disconnected",
            value=is_conn,
            last_checked=datetime.now(UTC),
        )
    except Exception as exc:
        return HealthCheck(
            name="mt5_connected",
            status="error",
            message=f"Health check failed: {exc}",
            last_checked=datetime.now(UTC),
        )


def _check_algo_trading() -> HealthCheck:
    gw = health_registry.gateway
    if gw is None:
        return HealthCheck(
            name="algo_trading_enabled",
            status="unknown",
            message="MT5Gateway not wired up yet (Phase 3+)",
            last_checked=datetime.now(UTC),
        )
    try:
        # terminal_info() returns a Future; resolve with a 5s timeout.
        fut = gw.terminal_info()  # type: ignore[attr-defined]
        term = fut.result(timeout=5)
        if term is None:
            return HealthCheck(
                name="algo_trading_enabled",
                status="error",
                message="terminal_info() returned None",
                last_checked=datetime.now(UTC),
            )
        if getattr(term, "trade_allowed", False):
            return HealthCheck(
                name="algo_trading_enabled",
                status="ok",
                message="Algo Trading is ON",
                value=True,
                last_checked=datetime.now(UTC),
            )
        return HealthCheck(
            name="algo_trading_enabled",
            status="warning",
            message="Algo Trading is OFF — press the Algo Trading button in the MT5 toolbar",
            value=False,
            last_checked=datetime.now(UTC),
        )
    except Exception as exc:
        return HealthCheck(
            name="algo_trading_enabled",
            status="error",
            message=f"Health check failed: {exc}",
            last_checked=datetime.now(UTC),
        )


def _check_quotes_fresh() -> HealthCheck:
    gw = health_registry.gateway
    if gw is None:
        return HealthCheck(
            name="quotes_fresh",
            status="unknown",
            message="MT5Gateway not wired up yet (Phase 3+)",
            last_checked=datetime.now(UTC),
        )
    try:
        fut = gw.symbol_info_tick("EURUSD")  # type: ignore[attr-defined]
        tick = fut.result(timeout=5)
        if tick is None:
            return HealthCheck(
                name="quotes_fresh",
                status="error",
                message="EURUSD tick is None",
                last_checked=datetime.now(UTC),
            )
        age = (datetime.now(UTC) - tick.time).total_seconds()
        if age < 5:
            status = "ok"
            msg = f"EURUSD tick is {age:.1f}s old"
        elif age < 60:
            status = "warning"
            msg = f"EURUSD tick is {age:.1f}s old (>5s)"
        else:
            status = "error"
            msg = f"EURUSD tick is {age:.1f}s old (>60s)"
        return HealthCheck(
            name="quotes_fresh",
            status=status,  # type: ignore[arg-type]
            message=msg,
            value=age,
            last_checked=datetime.now(UTC),
        )
    except Exception as exc:
        return HealthCheck(
            name="quotes_fresh",
            status="error",
            message=f"Health check failed: {exc}",
            last_checked=datetime.now(UTC),
        )


def _check_broker_offset() -> HealthCheck:
    gw = health_registry.gateway
    if gw is None:
        return HealthCheck(
            name="broker_offset_stable",
            status="unknown",
            message="MT5Gateway not wired up yet (Phase 3+)",
            last_checked=datetime.now(UTC),
        )
    try:
        # Read the cached offset via the gateway worker thread — never call
        # ``detect_broker_utc_offset()`` directly from the main thread (that
        # would violate ADR-002: MT5 calls are owned by the gateway worker).
        # Phase 1-3 audit (C3) flagged the previous direct call.
        cached_offset: int | None
        try:
            fut = gw.broker_offset()  # type: ignore[attr-defined]
            cached_offset = fut.result(timeout=2)
        except Exception:
            cached_offset = None

        if cached_offset is None:
            return HealthCheck(
                name="broker_offset_stable",
                status="unknown",
                message="Broker offset not yet cached (gateway not initialized?)",
                value=None,
                last_checked=datetime.now(UTC),
            )
        # We don't recompute the current offset here (would require an MT5
        # call outside the gateway). The cached value is the source of truth;
        # if it's stable across heartbeats, we're OK.
        return HealthCheck(
            name="broker_offset_stable",
            status="ok",
            message=f"Broker UTC offset: {cached_offset}s",
            value=cached_offset,
            last_checked=datetime.now(UTC),
        )
    except Exception as exc:
        return HealthCheck(
            name="broker_offset_stable",
            status="error",
            message=f"Health check failed: {exc}",
            last_checked=datetime.now(UTC),
        )


def _check_sync_queue() -> HealthCheck:
    return HealthCheck(
        name="sync_queue_size",
        status="unknown",
        message="Phase 4 will provide the real queue",
        last_checked=datetime.now(UTC),
    )


def _check_supabase() -> HealthCheck:
    now = datetime.now(UTC)
    # Try to get Supabase URL from settings
    url: str | None = None
    try:
        from app.core.config import AppSettings  # type: ignore[import-not-found]

        settings = AppSettings()  # type: ignore[call-arg]
        url = getattr(settings, "supabase_url", None) or getattr(settings, "supabaseUrl", None)
    except Exception:
        try:
            import os

            url = os.getenv("SUPABASE_URL")
        except Exception:
            url = None
    if not url:
        return HealthCheck(
            name="supabase_reachable", status="unknown", message="No Supabase URL configured", last_checked=now
        )
    try:
        import urllib.request

        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            code = resp.getcode()
            if 200 <= code < 400:
                return HealthCheck(
                    name="supabase_reachable", status="ok", message=f"Reachable ({code})", value=code, last_checked=now
                )
            return HealthCheck(
                name="supabase_reachable", status="error", message=f"HTTP {code}", value=code, last_checked=now
            )
    except Exception as e:
        return HealthCheck(name="supabase_reachable", status="error", message=f"Unreachable: {e}", last_checked=now)


def _check_disk_space() -> HealthCheck:
    now = datetime.now(UTC)
    try:
        import psutil

        # Use log_dir partition
        try:
            from app.observability.logger import get_log_dir

            path = str(get_log_dir())
        except Exception:
            path = "."
        usage = psutil.disk_usage(path)
        free_mb = usage.free / (1024 * 1024)
        free_gb = free_mb / 1024
        if free_mb < 100:
            return HealthCheck(
                name="disk_space",
                status="error",
                message=f"Low disk: {free_mb:.0f}MB free",
                value=free_mb,
                last_checked=now,
            )
        if free_gb < 1:
            return HealthCheck(
                name="disk_space",
                status="warning",
                message=f"Low disk: {free_gb:.2f}GB free",
                value=free_mb,
                last_checked=now,
            )
        return HealthCheck(
            name="disk_space", status="ok", message=f"{free_gb:.2f}GB free", value=free_mb, last_checked=now
        )
    except ImportError:
        return HealthCheck(name="disk_space", status="unknown", message="psutil not installed", last_checked=now)
    except Exception as e:
        return HealthCheck(name="disk_space", status="error", message=str(e), last_checked=now)


def _check_log_size() -> HealthCheck:
    now = datetime.now(UTC)
    try:
        try:
            from app.observability.logger import get_log_dir

            log_dir = get_log_dir()
        except Exception:
            log_dir = Path("logs")
        total = 0
        if log_dir.exists():
            for p in log_dir.rglob("*"):
                if p.is_file():
                    try:
                        total += p.stat().st_size
                    except Exception:
                        pass
        total_mb = total / (1024 * 1024)
        if total_mb > 2048:
            return HealthCheck(
                name="log_size",
                status="error",
                message=f"Logs too large: {total_mb:.0f}MB",
                value=total_mb,
                last_checked=now,
            )
        if total_mb > 500:
            return HealthCheck(
                name="log_size",
                status="warning",
                message=f"Logs large: {total_mb:.0f}MB",
                value=total_mb,
                last_checked=now,
            )
        return HealthCheck(name="log_size", status="ok", message=f"{total_mb:.1f}MB", value=total_mb, last_checked=now)
    except Exception as e:
        return HealthCheck(name="log_size", status="error", message=str(e), last_checked=now)


def _check_internet_latency() -> HealthCheck:
    now = datetime.now(UTC)
    host = "8.8.8.8"
    port = 53
    start = time.monotonic()
    try:
        sock = socket.create_connection((host, port), timeout=5)
        sock.close()
        rtt_ms = (time.monotonic() - start) * 1000
        if rtt_ms > 2000:
            return HealthCheck(
                name="internet_latency",
                status="error",
                message=f"High latency: {rtt_ms:.0f}ms",
                value=rtt_ms,
                last_checked=now,
            )
        if rtt_ms > 500:
            return HealthCheck(
                name="internet_latency",
                status="warning",
                message=f"Latency {rtt_ms:.0f}ms",
                value=rtt_ms,
                last_checked=now,
            )
        return HealthCheck(
            name="internet_latency", status="ok", message=f"{rtt_ms:.0f}ms", value=rtt_ms, last_checked=now
        )
    except Exception as e:
        return HealthCheck(name="internet_latency", status="error", message=f"Failed: {e}", last_checked=now)


def _check_clock_drift() -> HealthCheck:
    now = datetime.now(UTC)
    try:
        import json as _json
        import urllib.request

        url = "http://worldtimeapi.org/api/ip"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = _json.loads(resp.read().decode("utf-8"))
            remote_str = data.get("utc_datetime") or data.get("datetime")
            if not remote_str:
                return HealthCheck(
                    name="pc_clock_drift", status="unknown", message="No time in response", last_checked=now
                )
            try:
                remote = datetime.fromisoformat(remote_str.replace("Z", "+00:00"))
                if remote.tzinfo is None:
                    remote = remote.replace(tzinfo=UTC)
                drift = abs((now - remote).total_seconds())
                if drift > 30:
                    return HealthCheck(
                        name="pc_clock_drift",
                        status="error",
                        message=f"Drift {drift:.1f}s",
                        value=drift,
                        last_checked=now,
                    )
                if drift > 5:
                    return HealthCheck(
                        name="pc_clock_drift",
                        status="warning",
                        message=f"Drift {drift:.1f}s",
                        value=drift,
                        last_checked=now,
                    )
                return HealthCheck(
                    name="pc_clock_drift", status="ok", message=f"Drift {drift:.1f}s", value=drift, last_checked=now
                )
            except Exception as e:
                return HealthCheck(name="pc_clock_drift", status="unknown", message=str(e), last_checked=now)
    except Exception as e:
        return HealthCheck(name="pc_clock_drift", status="unknown", message=f"Check failed: {e}", last_checked=now)


health_registry = HealthRegistry()


def get_health_registry() -> HealthRegistry:
    """Return the singleton HealthRegistry instance."""
    return health_registry
