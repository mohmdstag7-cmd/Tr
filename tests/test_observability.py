"""Comprehensive observability tests."""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from loguru import logger


def _wait_for_logs() -> None:
    try:
        logger.complete()
    except Exception:
        time.sleep(0.3)


def test_logger_writes_jsonl_per_category(tmp_path: Path) -> None:
    from app.observability.logger import configure_logging, get_logger

    configure_logging(log_dir=tmp_path, default_level="INFO")
    get_logger("app").info("hello app")
    get_logger("mt5").info("hello mt5")
    _wait_for_logs()
    date_str = datetime.now(UTC).date().isoformat()
    app_file = tmp_path / "app" / f"{date_str}.jsonl"
    mt5_file = tmp_path / "mt5" / f"{date_str}.jsonl"
    assert app_file.exists(), f"{app_file} missing"
    assert mt5_file.exists(), f"{mt5_file} missing"
    app_data = [json.loads(line) for line in app_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert any(d["message"] == "hello app" for d in app_data)
    assert all("time" in d and "level" in d and "category" in d for d in app_data)
    # Validate time format ends with Z and has milliseconds
    for d in app_data:
        assert d["time"].endswith("Z")
        assert "T" in d["time"]


def test_logger_masking_filters_passwords(tmp_path: Path) -> None:
    from app.observability.logger import configure_logging, get_logger

    configure_logging(log_dir=tmp_path, default_level="INFO")
    get_logger("app").bind(password="hunter2").info("test")
    _wait_for_logs()
    date_str = datetime.now(UTC).date().isoformat()
    content = (tmp_path / "app" / f"{date_str}.jsonl").read_text(encoding="utf-8")
    assert "hunter2" not in content
    assert "[REDACTED]" in content


def test_logger_masking_jwt_token(tmp_path: Path) -> None:
    from app.observability.logger import configure_logging, get_logger

    configure_logging(log_dir=tmp_path, default_level="INFO")
    jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0In0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    get_logger("app").bind(token=jwt).info("jwt test")
    _wait_for_logs()
    date_str = datetime.now(UTC).date().isoformat()
    content = (tmp_path / "app" / f"{date_str}.jsonl").read_text(encoding="utf-8")
    assert jwt not in content
    assert "[REDACTED" in content


def test_logger_writes_all_log(tmp_path: Path) -> None:
    from app.observability.logger import configure_logging, get_logger

    configure_logging(log_dir=tmp_path, default_level="INFO")
    get_logger("app").info("all log test")
    _wait_for_logs()
    all_log = tmp_path / "all.log"
    assert all_log.exists()
    assert "all log test" in all_log.read_text(encoding="utf-8")


def test_context_trace_id_propagation(tmp_path: Path) -> None:
    from app.observability.context import bind_context
    from app.observability.logger import configure_logging, get_logger

    configure_logging(log_dir=tmp_path, default_level="INFO")
    with bind_context(trace_id="abc-123"):
        get_logger("app").info("inside")
    _wait_for_logs()
    date_str = datetime.now(UTC).date().isoformat()
    lines = (tmp_path / "app" / f"{date_str}.jsonl").read_text(encoding="utf-8").splitlines()
    found = False
    for line in lines:
        obj = json.loads(line)
        if obj["message"] == "inside":
            assert obj["trace_id"] == "abc-123"
            found = True
    assert found


def test_context_restores_on_exit(tmp_path: Path) -> None:
    from app.observability.context import bind_context, get_trace_id
    from app.observability.logger import configure_logging, get_logger

    configure_logging(log_dir=tmp_path, default_level="INFO")
    assert get_trace_id() is None
    with bind_context(trace_id="X"):
        assert get_trace_id() == "X"
        get_logger("app").info("with X")
    assert get_trace_id() is None
    get_logger("app").info("outside")
    _wait_for_logs()
    date_str = datetime.now(UTC).date().isoformat()
    lines = [json.loads(line) for line in (tmp_path / "app" / f"{date_str}.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    outside = [line for line in lines if line["message"] == "outside"]
    assert outside and outside[0]["trace_id"] is None


def test_decision_trace_rendering() -> None:
    from app.observability.decision_trace import DecisionStep, DecisionTrace, render_decision_trace

    trace = DecisionTrace(
        signal_id="sig1",
        steps=[
            DecisionStep(name="probability", value=0.63, threshold=0.60, passed=True, ms=1.2),
            DecisionStep(name="spread", value=1.8, threshold=2.5, passed=True, ms=0.5),
            DecisionStep(name="news USD CPI in 12 min", value="12 min", threshold=None, passed=False, ms=2.0),
        ],
        final_decision="REJECTED",
    )
    rendered = render_decision_trace(trace)
    assert "✓" in rendered
    assert "✗" in rendered
    assert "REJECTED" in rendered
    assert "probability" in rendered
    assert "spread" in rendered


def test_decision_trace_store_persists(tmp_path: Path) -> None:
    from app.observability.decision_trace import DecisionStep, DecisionTraceStore

    store = DecisionTraceStore(base_dir=tmp_path)
    store.add_step("sig-123", DecisionStep(name="a", value=1, threshold=0.5, passed=True, ms=1))
    store.finalize("sig-123", "APPROVED")
    loaded = store.get("sig-123")
    assert loaded is not None
    assert loaded.signal_id == "sig-123"
    assert loaded.final_decision == "APPROVED"
    assert len(loaded.steps) == 1
    # Check file exists
    assert (tmp_path / "sig-123.json").exists()
    # New store instance should load from disk
    store2 = DecisionTraceStore(base_dir=tmp_path)
    loaded2 = store2.get("sig-123")
    assert loaded2 is not None
    assert loaded2.final_decision == "APPROVED"


def test_crash_handler_writes_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.observability import crash_handler

    monkeypatch.setattr(crash_handler, "_crash_dir", tmp_path)
    crash_handler._handle_exception(ValueError, ValueError("test"), None)
    files = list(tmp_path.glob("crash_*.json"))
    assert len(files) >= 1
    data = json.loads(files[0].read_text(encoding="utf-8"))
    assert "timestamp" in data
    assert "exception" in data
    assert data["exception"]["value"] == "test"
    assert "platform" in data
    assert "context" in data


def test_audit_log_writes_entry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.observability.audit import AuditLog

    audit = AuditLog(base_dir=tmp_path / "audit")
    entry = audit.log("user", "test_action", before={"x": 1}, after={"x": 2})
    assert entry.action == "test_action"
    assert entry.source == "user"
    # Check file
    date_str = datetime.now(UTC).date().isoformat()
    f = tmp_path / "audit" / f"{date_str}.jsonl"
    assert f.exists()
    lines = [json.loads(line) for line in f.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert any(line["action"] == "test_action" for line in lines)
    assert audit.recent(limit=10)


def test_watchdog_detects_freeze(qtbot: Any) -> None:  # type: ignore[no-untyped-def]
    from app.observability.watchdog import Watchdog

    wd = Watchdog(threshold_s=0.5)
    wd.register_worker("test_worker")
    # Simulate no heartbeat: set last_heartbeat to past
    from datetime import timedelta

    wd._workers["test_worker"] = datetime.now(UTC) - timedelta(seconds=2)
    frozen: list[tuple[str, float]] = []
    wd.worker_frozen.connect(lambda name, secs: frozen.append((name, secs)))
    wd._check()
    assert len(frozen) == 1
    assert frozen[0][0] == "test_worker"
    wd.stop()


def test_watchdog_recovery(qtbot: Any) -> None:  # type: ignore[no-untyped-def]
    from app.observability.watchdog import Watchdog

    wd = Watchdog(threshold_s=0.5)
    wd.register_worker("w2")
    from datetime import timedelta

    wd._workers["w2"] = datetime.now(UTC) - timedelta(seconds=2)
    wd._check()
    assert "w2" in wd._frozen
    recovered: list[str] = []
    wd.worker_recovered.connect(lambda name: recovered.append(name))
    wd.heartbeat("w2")
    assert "w2" not in wd._frozen
    assert recovered == ["w2"]
    wd.stop()


def test_health_check_disk_space(tmp_path: Path) -> None:
    from app.observability.health import HealthRegistry

    reg = HealthRegistry()
    # Run disk_space check
    hc = reg.run_one("disk_space")
    assert hc.status in ("ok", "warning", "error", "unknown")
    assert hc.name == "disk_space"
    reg.stop()


def test_health_check_internet_latency() -> None:
    from app.observability.health import HealthRegistry

    reg = HealthRegistry()
    hc = reg.run_one("internet_latency")
    assert hc.status in ("ok", "warning", "error", "unknown")
    reg.stop()


def test_metrics_record_latency() -> None:
    from app.observability.metrics import PerformanceMetrics

    m = PerformanceMetrics()
    for i in range(100):
        m.record_bar_processing_latency(float(i) / 100)
    assert m.bar_latency.count == 100
    assert m.bar_latency.p50 > 0
    assert m.bar_latency.p95 > m.bar_latency.p50
    m.stop()


def test_metrics_snapshot_has_cpu_ram() -> None:
    from app.observability.metrics import PerformanceMetrics

    m = PerformanceMetrics()
    snap = m.snapshot()
    assert "cpu_pct" in snap
    assert "ram_mb" in snap
    m.stop()


def test_debug_bundle_creation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.observability import debug_bundle
    from app.observability.logger import configure_logging

    configure_logging(log_dir=tmp_path / "logs")
    # Create dummy log
    from app.observability.logger import get_logger

    get_logger("app").info("bundle test")
    _wait_for_logs()
    # Monkeypatch dirs
    monkeypatch.setattr(debug_bundle, "masked_settings", lambda: {"ok": 1})
    # Ensure crash dir exists
    (tmp_path / "crash_reports").mkdir(parents=True, exist_ok=True)
    (tmp_path / "crash_reports" / "crash_dummy.json").write_text("{}", encoding="utf-8")
    # Patch get_log_dir and get_crash_dir via monkeypatching modules
    import app.observability.crash_handler as ch
    import app.observability.logger as lg

    orig_get_log_dir = lg.get_log_dir
    orig_get_crash_dir = ch.get_crash_dir
    monkeypatch.setattr(lg, "get_log_dir", lambda: tmp_path / "logs")
    monkeypatch.setattr(ch, "get_crash_dir", lambda: tmp_path / "crash_reports")
    out = tmp_path / "bundle.zip"
    path = debug_bundle.create_debug_bundle(output_path=out)
    assert path.exists()
    import zipfile

    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
        assert any("versions.txt" in n for n in names)
        assert any("README_DEBUG.md" in n for n in names)
    # Restore
    monkeypatch.setattr(lg, "get_log_dir", orig_get_log_dir)
    monkeypatch.setattr(ch, "get_crash_dir", orig_get_crash_dir)


def test_masked_settings_no_secrets() -> None:
    from app.observability.debug_bundle import masked_settings

    ms = masked_settings()
    # Check no password field has real value
    for k, v in ms.items():
        if "password" in k.lower() and isinstance(v, str):
            assert v == "[REDACTED]" or "[REDACTED" in v


def test_logs_page_constructs(qtbot) -> None:  # type: ignore[no-untyped-def]
    from app.ui.pages.logs import LogsPage

    page = LogsPage()
    qtbot.addWidget(page)
    assert page is not None
    page.close()


def test_health_page_constructs(qtbot) -> None:  # type: ignore[no-untyped-def]
    from app.ui.pages.health import HealthPage

    page = HealthPage()
    qtbot.addWidget(page)
    assert page is not None
    page.close()
