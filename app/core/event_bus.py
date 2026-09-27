"""Thread-safe event bus for inter-module communication."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

from loguru import logger


class EventBus:
    """Synchronous, thread-safe publish/subscribe bus."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable[[Any], None]]] = {}
        self._lock = threading.RLock()

    def subscribe(self, event_type: str, handler: Callable[[Any], None]) -> Callable[[], None]:
        """Subscribe to an event type. Returns an unsubscribe callable."""
        with self._lock:
            self._handlers.setdefault(event_type, []).append(handler)

        def unsubscribe() -> None:
            with self._lock:
                handlers = self._handlers.get(event_type, [])
                if handler in handlers:
                    handlers.remove(handler)

        return unsubscribe

    def publish(self, event_type: str, payload: Any = None) -> None:
        """Publish an event to all subscribers synchronously."""
        with self._lock:
            handlers = list(self._handlers.get(event_type, []))
        for h in handlers:
            try:
                h(payload)
            except Exception:
                logger.exception(f"Event handler failed for event_type={event_type}")

    def clear(self) -> None:
        """Remove all subscriptions."""
        with self._lock:
            self._handlers.clear()


event_bus = EventBus()
