"""Crash handler for unhandled exceptions."""

from __future__ import annotations

import platform
import sys
import threading
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from PySide6.QtCore import QObject, Signal, qInstallMessageHandler  # noqa: F401

    _HAS_QT = True
except Exception:
    _HAS_QT = False
    QObject = object  # type: ignore[assignment,misc]

    def Signal(*a, **k):  # type: ignore[no-untyped-def,no-redef]
        return None  # type: ignore[assignment]


from app.observability.context import current_context

_crash_dir: Path | None = None

if _HAS_QT:

    class _CrashEmitter(QObject):
        crash_occurred = Signal(str)

    _emitter = _CrashEmitter()
    crash_occurred = _emitter.crash_occurred
else:
    # Dummy signal
    class _DummySignal:
        def connect(self, *a: Any, **k: Any) -> None:
            pass

        def emit(self, *a: Any, **k: Any) -> None:
            pass

    crash_occurred = _DummySignal()  # type: ignore[assignment]


def get_crash_dir() -> Path:
    if _crash_dir is None:
        return Path("crash_reports")
    return _crash_dir


def _get_app_version() -> str:
    try:
        from importlib.metadata import version

        return version("mt5-trading-workstation")
    except Exception:
        try:
            import tomllib

            p = Path("pyproject.toml")
            if p.exists():
                data = tomllib.loads(p.read_text(encoding="utf-8"))
                return str(data.get("project", {}).get("version", "0.1.0"))
        except Exception:
            pass
    return "0.1.0"


def _read_last_logs(n: int = 200) -> list[str]:
    try:
        from app.observability.logger import get_log_dir

        log_dir = get_log_dir()
        all_log = log_dir / "all.log"
        if not all_log.exists():
            # Try default
            all_log = Path("logs/all.log")
        if not all_log.exists():
            return []
        lines = all_log.read_text(encoding="utf-8", errors="ignore").splitlines()
        return lines[-n:]
    except Exception:
        return []


def _write_crash_report(
    exc_type: type[BaseException] | None,
    exc_value: BaseException | None,
    exc_tb: Any,
) -> Path:
    crash_dir = get_crash_dir()
    crash_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC)
    ts = now.strftime("%Y-%m-%dT%H-%M-%S.%f")[:-3] + "Z"
    iso = now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    # Stack trace
    stack: list[str] = []
    if exc_tb is not None:
        try:
            stack = traceback.format_exception(exc_type, exc_value, exc_tb)  # type: ignore[arg-type]
        except Exception:
            stack = [str(exc_value)]
    elif exc_value is not None:
        stack = [f"{type(exc_value).__name__}: {exc_value}"]

    report: dict[str, Any] = {
        "timestamp": iso,
        "app_version": _get_app_version(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "exception": {
            "type": exc_type.__name__ if exc_type else type(exc_value).__name__ if exc_value else "Unknown",
            "value": str(exc_value) if exc_value else "",
            "stack_trace": stack,
        },
        "last_logs": _read_last_logs(200),
        "context": current_context(),
    }
    path = crash_dir / f"crash_{ts}.json"
    try:
        import json

        path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    # Emit signal
    try:
        crash_occurred.emit(str(path))  # type: ignore[attr-defined]
    except Exception:
        pass
    # Also log
    try:
        from loguru import logger

        logger.bind(category="app").critical(f"Crash report written to {path}: {exc_value}")
    except Exception:
        pass
    return path


def _handle_exception(exc_type: type[BaseException], exc_value: BaseException, exc_tb: Any) -> None:
    _write_crash_report(exc_type, exc_value, exc_tb)
    # Call original excepthook
    try:
        sys.__excepthook__(exc_type, exc_value, exc_tb)
    except Exception:
        pass


def _handle_thread_exception(args: threading.ExceptHookArgs) -> None:
    _write_crash_report(args.exc_type, args.exc_value, args.exc_traceback)


def _qt_message_handler(mode: Any, context: Any, message: str) -> None:
    try:
        from loguru import logger

        # Map QtMsgType to log level
        # 0 Debug, 1 Warning, 2 Critical, 3 Fatal, 4 Info
        level = "INFO"
        try:
            mode_val = int(mode)
            if mode_val == 1:
                level = "WARNING"
            elif mode_val in (2, 3):
                level = "ERROR"
            elif mode_val == 0:
                level = "DEBUG"
        except Exception:
            pass
        logger.bind(category="ui").log(level, f"Qt: {message}")
    except Exception:
        pass


def install_crash_handler(crash_dir: Path | None = None) -> None:
    global _crash_dir
    _crash_dir = crash_dir or Path("crash_reports")
    _crash_dir.mkdir(parents=True, exist_ok=True)
    sys.excepthook = _handle_exception  # type: ignore[assignment]
    threading.excepthook = _handle_thread_exception  # type: ignore[assignment]
    if _HAS_QT:
        try:
            qInstallMessageHandler(_qt_message_handler)  # type: ignore[arg-type]
        except Exception:
            pass
