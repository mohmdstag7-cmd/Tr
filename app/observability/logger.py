"""Structured logging pipeline wrapping loguru."""

from __future__ import annotations

import json
import threading
import time
from datetime import UTC
from pathlib import Path
from typing import Any

from loguru import logger

from app.observability.categories import LOG_CATEGORIES
from app.observability.context import current_context
from app.observability.masking import SecretsMaskingFilter

_log_dir: Path | None = None
_sink_ids: list[int] = []
_patcher_id: int | None = None
_level_per_category: dict[str, str] = {}
_default_level: str = "INFO"
_masking_filter = SecretsMaskingFilter()


def _inject_context(record: dict[str, Any]) -> None:
    ctx = current_context()
    for k, v in ctx.items():
        # Only set if not already present in extra
        if k not in record["extra"]:
            record["extra"][k] = v
    # Ensure category exists
    if "category" not in record["extra"]:
        record["extra"]["category"] = "app"
    # Ensure all context keys exist even if None
    for k in ("session_id", "trace_id", "signal_id", "trade_id", "ticket", "symbol"):
        if k not in record["extra"]:
            record["extra"][k] = None


def _make_json_sink(log_dir: Path, category: str):  # type: ignore[no-untyped-def]
    def _sink(message: Any) -> None:
        record = message.record
        # Apply masking (also done via filter, but ensure)
        # Build JSON record
        dt = record["time"]
        if dt.tzinfo is not None:
            dt_utc = dt.astimezone(UTC)
        else:
            dt_utc = dt.replace(tzinfo=UTC)
        time_str = dt_utc.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        thread_name = threading.current_thread().name
        thread_id = threading.get_ident()
        # Exception handling
        exc_str: str | None = None
        exc = record.get("exception")
        if exc is not None:
            try:
                exc_type, exc_val, exc_tb = exc
                if exc_type is not None:
                    import traceback

                    exc_str = "".join(traceback.format_exception(exc_type, exc_val, exc_tb))
            except Exception:
                exc_str = str(exc)

        # Build extra without context keys
        extra_filtered = {
            k: v
            for k, v in record["extra"].items()
            if k not in {"category", "session_id", "trace_id", "signal_id", "trade_id", "ticket", "symbol"}
        }

        json_record: dict[str, Any] = {
            "time": time_str,
            "level": record["level"].name,
            "category": record["extra"].get("category", category),
            "module": record["name"],
            "function": record["function"],
            "line": record["line"],
            "thread": f"{thread_name}:{thread_id}",
            "session_id": record["extra"].get("session_id"),
            "trace_id": record["extra"].get("trace_id"),
            "signal_id": record["extra"].get("signal_id"),
            "trade_id": record["extra"].get("trade_id"),
            "ticket": record["extra"].get("ticket"),
            "symbol": record["extra"].get("symbol"),
            "message": record["message"],
            "exception": exc_str,
            "extra": extra_filtered,
        }
        date_str = dt_utc.date().isoformat()
        file_path = log_dir / category / f"{date_str}.jsonl"
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with file_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(json_record, ensure_ascii=False) + "\n")
        except Exception:
            # Never crash on logging
            pass

    return _sink


def _make_all_sink(log_dir: Path):  # type: ignore[no-untyped-def]
    def _sink(message: Any) -> None:
        record = message.record
        dt = record["time"]
        if dt.tzinfo is not None:
            dt_utc = dt.astimezone(UTC)
        else:
            dt_utc = dt.replace(tzinfo=UTC)
        time_str = dt_utc.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        level = record["level"].name
        category = record["extra"].get("category", "app")
        msg = record["message"]
        line = (
            f"{time_str} | {level:<8} | {category:<12} | "
            f"{record['name']}:{record['function']}:{record['line']} - {msg}\n"
        )
        if record.get("exception") is not None:
            try:
                exc_type, exc_val, exc_tb = record["exception"]
                if exc_type is not None:
                    import traceback

                    line += "".join(traceback.format_exception(exc_type, exc_val, exc_tb))
            except Exception:
                line += str(record["exception"]) + "\n"
        file_path = log_dir / "all.log"
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with file_path.open("a", encoding="utf-8") as f:
                f.write(line)
            # Simple rotation check 50MB
            try:
                if file_path.stat().st_size > 50 * 1024 * 1024:
                    # Rotate by renaming
                    rotated = log_dir / f"all.{time.strftime('%Y%m%d%H%M%S')}.log"
                    try:
                        file_path.rename(rotated)
                    except Exception:
                        pass
            except Exception:
                pass
        except Exception:
            pass

    return _sink


def configure_logging(log_dir: Path | None = None, default_level: str = "INFO") -> None:
    """Configure loguru sinks for all categories."""
    global _log_dir, _sink_ids, _patcher_id, _default_level, _level_per_category
    if log_dir is None:
        log_dir = Path("logs")
    _log_dir = log_dir
    _default_level = default_level
    _level_per_category = {cat: default_level for cat in LOG_CATEGORIES}

    log_dir.mkdir(parents=True, exist_ok=True)
    for cat in LOG_CATEGORIES:
        (log_dir / cat).mkdir(parents=True, exist_ok=True)

    # Remove existing sinks
    try:
        logger.remove()
    except Exception:
        pass
    _sink_ids = []

    # Install patcher for context injection
    # loguru patcher is set via logger.configure
    def _patcher(record: dict[str, Any]) -> None:
        _inject_context(record)
        # Also apply masking filter logic to extra/message before sink
        # We do masking here so it applies to all sinks
        _masking_filter(record)

    logger.configure(patcher=_patcher)  # type: ignore[arg-type,call-arg]

    # Add per-category JSON sinks
    for category in LOG_CATEGORIES:
        sink = _make_json_sink(log_dir, category)

        def _filter(record: dict[str, Any], cat: str = category) -> bool:
            return record["extra"].get("category") == cat

        sid = logger.add(
            sink,
            level=default_level,
            filter=_filter,  # type: ignore[arg-type]
            enqueue=True,
            backtrace=True,
            diagnose=False,
        )
        _sink_ids.append(sid)

    # Add readable all.log sink
    all_sink = _make_all_sink(log_dir)
    sid_all = logger.add(
        all_sink,
        level=default_level,
        enqueue=True,
        backtrace=True,
        diagnose=False,
    )
    _sink_ids.append(sid_all)


def get_logger(category: str) -> Any:
    """Return a logger bound to a category."""
    if category not in LOG_CATEGORIES:
        # Still allow but log warning
        pass
    return logger.bind(category=category)


def set_level(category: str, level: str) -> None:
    """Change a category's sink level at runtime."""
    global _level_per_category
    if _log_dir is None:
        raise RuntimeError("Logging not configured. Call configure_logging() first.")
    # Validate level
    level = level.upper()
    _level_per_category[category] = level
    # Reconfigure: remove all sinks and re-add with new levels
    # Simpler: remove and re-add
    try:
        logger.remove()
    except Exception:
        pass
    _sink_ids.clear()

    def _patcher(record: dict[str, Any]) -> None:
        _inject_context(record)
        _masking_filter(record)

    logger.configure(patcher=_patcher)  # type: ignore[arg-type,call-arg]

    for cat in LOG_CATEGORIES:
        lvl = _level_per_category.get(cat, _default_level)
        sink = _make_json_sink(_log_dir, cat)

        def _filter(record: dict[str, Any], c: str = cat) -> bool:
            return record["extra"].get("category") == c

        sid = logger.add(
            sink,
            level=lvl,
            filter=_filter,  # type: ignore[arg-type]
            enqueue=True,
            backtrace=True,
            diagnose=False,
        )
        _sink_ids.append(sid)

    all_sink = _make_all_sink(_log_dir)
    # all.log uses the lowest level among categories (DEBUG if any DEBUG)
    all_level = "DEBUG" if "DEBUG" in _level_per_category.values() else _default_level
    # If any category is DEBUG, all.log should also be DEBUG to capture everything
    # Use min level
    sid_all = logger.add(all_sink, level=all_level, enqueue=True, backtrace=True, diagnose=False)
    _sink_ids.append(sid_all)


def enable_debug_mode(duration_minutes: int = 30) -> None:
    """Set all categories to DEBUG for duration_minutes, then auto-revert."""
    if _log_dir is None:
        raise RuntimeError("Logging not configured")
    previous = dict(_level_per_category)
    for cat in LOG_CATEGORIES:
        set_level(cat, "DEBUG")
    get_logger("app").info(f"Debug mode enabled for {duration_minutes} minutes")

    def _revert() -> None:
        for cat, lvl in previous.items():
            try:
                set_level(cat, lvl)
            except Exception:
                pass
        try:
            get_logger("app").info("Debug mode auto-reverted")
        except Exception:
            pass

    # Use threading.Timer for revert
    t = threading.Timer(duration_minutes * 60, _revert)
    t.daemon = True
    t.start()


def get_log_dir() -> Path:
    if _log_dir is None:
        raise RuntimeError("Logging not configured. Call configure_logging() first.")
    return _log_dir
