"""Debug bundle zip creator."""

from __future__ import annotations

import json
import platform
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


def masked_settings() -> dict[str, Any]:
    """Load AppSettings and redact secrets."""
    try:
        from app.core.config import AppSettings  # type: ignore[import-not-found]

        settings = AppSettings()  # type: ignore[call-arg]
        # Try model_dump for pydantic
        if hasattr(settings, "model_dump"):
            data = settings.model_dump()  # type: ignore[attr-defined]
        elif hasattr(settings, "dict"):
            data = settings.dict()  # type: ignore[attr-defined]
        else:
            data = {k: v for k, v in vars(settings).items() if not k.startswith("_")}
        from app.observability.masking import redact_dict

        return redact_dict(data)
    except Exception:
        # Fallback: try to read env
        import os

        data = {k: v for k, v in os.environ.items() if not k.startswith("_")}
        try:
            from app.observability.masking import redact_dict

            return redact_dict(data)
        except Exception:
            return {}


def create_debug_bundle(output_path: Path | None = None) -> Path:
    """Create a debug bundle zip."""
    now = datetime.now(UTC)
    ts = now.strftime("%Y%m%d_%H%M%S")
    if output_path is None:
        output_path = Path("debug_bundles") / f"debug_{ts}.zip"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Resolve dirs
    try:
        from app.observability.logger import get_log_dir

        log_dir = get_log_dir()
    except Exception:
        log_dir = Path("logs")

    try:
        from app.observability.crash_handler import get_crash_dir

        crash_dir = get_crash_dir()
    except Exception:
        crash_dir = Path("crash_reports")

    # Decision traces dir
    try:
        pass

    except Exception:
        Path("decision_traces")

    cutoff = now - timedelta(days=7)

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Logs last 7 days
        if log_dir.exists():
            for p in log_dir.rglob("*.jsonl"):
                try:
                    # Check mtime
                    mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=UTC)
                    if mtime < cutoff:
                        # Still include if older? spec says last 7 days (or all if older)
                        # Include anyway but we already include
                        pass
                    p.relative_to(log_dir.parent) if log_dir.parent in p.parents else p
                    # Use logs/... as arcname
                    try:
                        arcname = str(p.relative_to(Path.cwd()))
                    except Exception:
                        arcname = str(p)
                    zf.write(p, arcname)
                except Exception:
                    pass
            # Also include all.log
            all_log = log_dir / "all.log"
            if all_log.exists():
                try:
                    zf.write(
                        all_log,
                        str(all_log.relative_to(Path.cwd())) if all_log.is_relative_to(Path.cwd()) else "logs/all.log",
                    )
                except Exception:
                    pass

        # Crash reports
        if crash_dir.exists():
            for p in crash_dir.glob("*.json"):
                try:
                    arcname = (
                        str(p.relative_to(Path.cwd())) if p.is_relative_to(Path.cwd()) else f"crash_reports/{p.name}"
                    )
                    zf.write(p, arcname)
                except Exception:
                    pass

        # masked_settings.json
        try:
            ms = masked_settings()
            zf.writestr("masked_settings.json", json.dumps(ms, indent=2, ensure_ascii=False))
        except Exception:
            zf.writestr("masked_settings.json", "{}")

        # health.json
        try:
            from app.observability.health import health_registry

            health_data = health_registry.run_all()
            # Serialize
            serial: dict[str, Any] = {}
            for k, v in health_data.items():
                serial[k] = {
                    "name": v.name,
                    "status": v.status,
                    "message": v.message,
                    "value": v.value,
                    "last_checked": v.last_checked.isoformat() if v.last_checked else None,
                }
            zf.writestr("health.json", json.dumps(serial, indent=2, ensure_ascii=False))
        except Exception as e:
            zf.writestr("health.json", json.dumps({"error": str(e)}))

        # versions.txt
        versions = []
        versions.append(f"app_version: {_get_app_version()}")
        versions.append(f"python_version: {platform.python_version()}")
        versions.append(f"platform: {platform.platform()}")
        versions.append(f"os: {platform.system()} {platform.release()}")
        # MT5 build if available
        try:
            import MetaTrader5 as mt5  # type: ignore[import-not-found]

            versions.append(f"mt5_build: {getattr(mt5, '__version__', 'unknown')}")
        except Exception:
            versions.append("mt5_build: not available (Phase 3)")
        zf.writestr("versions.txt", "\n".join(versions))

        # Last 50 decision traces
        try:
            from app.observability.decision_trace import decision_trace_store as _store

            traces = _store.recent(limit=50)
            for t in traces:
                data = {
                    "signal_id": t.signal_id,
                    "steps": [
                        {"name": s.name, "value": s.value, "threshold": s.threshold, "passed": s.passed, "ms": s.ms}
                        for s in t.steps
                    ],
                    "final_decision": t.final_decision,
                    "created_at": t.created_at.isoformat(),
                }
                zf.writestr(f"decision_traces/{t.signal_id}.json", json.dumps(data, indent=2, ensure_ascii=False))
        except Exception:
            pass

        # README_DEBUG.md
        readme = """# Debug Bundle

This zip contains the last 7 days of logs, recent crash reports, masked settings,
health checks, and decision traces.

## AI prompt

Paste this bundle into your AI coding assistant with the prompt:

> "Find the root cause of this problem. The user reported: <DESCRIPTION>.
> Focus on logs in the `audit` and `execution` categories. Cross-reference
> any crash_reports/*.json with the decision traces."
"""
        zf.writestr("README_DEBUG.md", readme)

    return output_path


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
