"""Worker heartbeat watchdog."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

try:
    from PySide6.QtCore import QObject, QTimer, Signal
except Exception:
    # Fallback for environments without Qt
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
class WorkerStatus:
    name: str
    last_heartbeat: datetime
    is_alive: bool
    freeze_seconds: float


class Watchdog(QObject):
    worker_frozen = Signal(str, float)  # type: ignore[assignment]
    worker_recovered = Signal(str)  # type: ignore[assignment]

    def __init__(self, threshold_s: float = 30.0, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.threshold_s = threshold_s
        self._workers: dict[str, datetime] = {}
        self._frozen: set[str] = set()
        # Don't start the QTimer in __init__ — it runs at module import
        # time, before QApplication exists (Phase 1-3 audit C9). Callers
        # must call :meth:`start` after the QApplication is created.
        self._timer = QTimer(self)
        self._timer.setInterval(5000)
        try:
            self._timer.timeout.connect(self._check)  # type: ignore[attr-defined]
        except Exception:
            pass

    def start(self) -> None:
        """Start the periodic 5s heartbeat-check timer. Idempotent."""
        try:
            if not self._timer.isActive():
                self._timer.start()
        except Exception:
            pass

    def register_worker(self, name: str) -> None:
        self._workers[name] = datetime.now(UTC)
        self._frozen.discard(name)

    def heartbeat(self, name: str) -> None:
        now = datetime.now(UTC)
        was_frozen = name in self._frozen
        self._workers[name] = now
        if was_frozen:
            self._frozen.discard(name)
            try:
                self.worker_recovered.emit(name)  # type: ignore[attr-defined]
            except Exception:
                pass
            try:
                from loguru import logger

                logger.bind(category="perf").info(f"Worker {name} recovered")
            except Exception:
                pass

    def unregister_worker(self, name: str) -> None:
        self._workers.pop(name, None)
        self._frozen.discard(name)

    def get_status(self, name: str) -> WorkerStatus | None:
        last = self._workers.get(name)
        if last is None:
            return None
        now = datetime.now(UTC)
        freeze = (now - last).total_seconds()
        return WorkerStatus(
            name=name,
            last_heartbeat=last,
            is_alive=freeze <= self.threshold_s,
            freeze_seconds=freeze,
        )

    def all_statuses(self) -> list[WorkerStatus]:
        return [s for n in list(self._workers.keys()) if (s := self.get_status(n)) is not None]

    def _check(self) -> None:
        now = datetime.now(UTC)
        for name, last in list(self._workers.items()):
            freeze = (now - last).total_seconds()
            if freeze > self.threshold_s and name not in self._frozen:
                self._frozen.add(name)
                try:
                    self.worker_frozen.emit(name, freeze)  # type: ignore[attr-defined]
                except Exception:
                    pass
                try:
                    from loguru import logger

                    logger.bind(category="perf").critical(f"Worker {name} frozen for {freeze:.1f}s")
                except Exception:
                    pass

    def stop(self) -> None:
        try:
            self._timer.stop()
        except Exception:
            pass


watchdog = Watchdog()
