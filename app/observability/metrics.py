"""Performance metrics."""

from __future__ import annotations

import math
import time
from collections import deque
from dataclasses import dataclass, field
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


class LatencyHistogram:
    """Sliding-window histogram."""

    def __init__(self, max_samples: int = 1000) -> None:
        self.max_samples = max_samples
        self._samples: deque[float] = deque(maxlen=max_samples)

    def record(self, value: float) -> None:
        self._samples.append(value)

    @property
    def count(self) -> int:
        return len(self._samples)

    @property
    def max(self) -> float:
        return max(self._samples) if self._samples else 0.0

    def percentile(self, p: float) -> float:
        if not self._samples:
            return 0.0
        sorted_s = sorted(self._samples)
        k = (len(sorted_s) - 1) * (p / 100)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return sorted_s[int(k)]
        d0 = sorted_s[int(f)] * (c - k)
        d1 = sorted_s[int(c)] * (k - f)
        return d0 + d1

    @property
    def p50(self) -> float:
        return self.percentile(50)

    @property
    def p95(self) -> float:
        return self.percentile(95)

    @property
    def p99(self) -> float:
        return self.percentile(99)


@dataclass
class _QueueMetric:
    name: str
    size: int
    updated: float = field(default_factory=time.monotonic)


class PerformanceMetrics(QObject):
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.bar_latency = LatencyHistogram()
        self.mt5_latency: dict[str, LatencyHistogram] = {}
        self._queues: dict[str, int] = {}
        self._timer = QTimer(self)
        self._timer.setInterval(60000)
        try:
            self._timer.timeout.connect(self._tick)  # type: ignore[attr-defined]
        except Exception:
            pass
        try:
            self._timer.start()
        except Exception:
            pass

    def record_bar_processing_latency(self, seconds: float) -> None:
        self.bar_latency.record(seconds)

    def record_mt5_call_latency(self, action: str, seconds: float) -> None:
        hist = self.mt5_latency.get(action)
        if hist is None:
            hist = LatencyHistogram()
            self.mt5_latency[action] = hist
        hist.record(seconds)

    def record_queue_size(self, name: str, size: int) -> None:
        self._queues[name] = size

    def snapshot(self) -> dict[str, Any]:
        cpu_pct = 0.0
        ram_mb = 0.0
        try:
            import psutil

            cpu_pct = psutil.cpu_percent(interval=None)
            ram_mb = psutil.Process().memory_info().rss / (1024 * 1024)
        except Exception:
            pass
        mt5_data: dict[str, dict[str, float]] = {}
        for action, hist in self.mt5_latency.items():
            mt5_data[action] = {"p50": hist.p50, "p95": hist.p95, "count": float(hist.count), "max": hist.max}
        return {
            "cpu_pct": cpu_pct,
            "ram_mb": ram_mb,
            "bar_latency": {
                "p50": self.bar_latency.p50,
                "p95": self.bar_latency.p95,
                "p99": self.bar_latency.p99,
                "count": self.bar_latency.count,
                "max": self.bar_latency.max,
            },
            "mt5_latency": mt5_data,
            "queue_sizes": dict(self._queues),
        }

    def _tick(self) -> None:
        snap = self.snapshot()
        try:
            from loguru import logger

            logger.bind(category="perf").info(f"Metrics snapshot: {snap}")
            # Check budgets D4
            if snap["cpu_pct"] > 3:
                logger.bind(category="perf").warning(f"CPU budget exceeded: {snap['cpu_pct']:.1f}% > 3%")
            if snap["ram_mb"] > 500:
                logger.bind(category="perf").warning(f"RAM budget exceeded: {snap['ram_mb']:.0f}MB > 500MB")
            if snap["bar_latency"]["p95"] > 1:
                logger.bind(category="perf").warning(
                    f"bar_latency p95 exceeded: {snap['bar_latency']['p95']:.3f}s > 1s"
                )
            for qname, size in snap["queue_sizes"].items():
                if size > 100:
                    logger.bind(category="perf").warning(f"Queue {qname} size {size} > 100")
        except Exception:
            pass

    def stop(self) -> None:
        try:
            self._timer.stop()
        except Exception:
            pass


metrics = PerformanceMetrics()
