"""User action audit log."""

from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from app.observability.context import current_context

AuditSource = Literal["user", "system", "ai_suggestion", "telegram"]


@dataclass
class AuditEntry:
    timestamp: datetime
    source: AuditSource
    action: str
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None
    context: dict[str, Any] = field(default_factory=dict)


class AuditLog:
    def __init__(self, base_dir: Path | None = None, max_buffer: int = 1000) -> None:
        self.base_dir = base_dir or Path("logs/audit")
        self._buffer: deque[AuditEntry] = deque(maxlen=max_buffer)

    def log(
        self,
        source: AuditSource,
        action: str,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
    ) -> AuditEntry:
        entry = AuditEntry(
            timestamp=datetime.now(UTC),
            source=source,
            action=action,
            before=before,
            after=after,
            context=current_context(),
        )
        self._buffer.append(entry)
        # Write to file
        try:
            # Resolve log dir dynamically if base_dir is default
            base = self.base_dir
            # If base_dir is default logs/audit but logger has custom dir, use logger's dir
            try:
                from app.observability.logger import get_log_dir

                log_dir = get_log_dir()
                # If base_dir is Path("logs/audit"), replace with log_dir / "audit"
                if str(self.base_dir) == "logs/audit":
                    base = log_dir / "audit"
            except Exception:
                pass
            base.mkdir(parents=True, exist_ok=True)
            date_str = entry.timestamp.date().isoformat()
            file_path = base / f"{date_str}.jsonl"
            # Redact secrets before serializing — secrets in `before`/`after`
            # would otherwise land on disk in plaintext. See SPEC Part D5 and
            # the Phase 1-3 audit (M3).
            from app.observability.masking import redact_dict

            data = {
                "timestamp": entry.timestamp.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
                "source": entry.source,
                "action": entry.action,
                "before": redact_dict(entry.before) if entry.before else None,
                "after": redact_dict(entry.after) if entry.after else None,
                "context": redact_dict(entry.context) if entry.context else {},
            }
            with file_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(data, ensure_ascii=False) + "\n")
            # Also log via loguru audit category
            try:
                from loguru import logger

                logger.bind(category="audit").info(f"Audit {source}:{action}")
            except Exception:
                pass
        except Exception:
            pass
        return entry

    def recent(self, limit: int = 100) -> list[AuditEntry]:
        return list(self._buffer)[-limit:]

    def clear(self) -> None:
        self._buffer.clear()


audit_log = AuditLog()
