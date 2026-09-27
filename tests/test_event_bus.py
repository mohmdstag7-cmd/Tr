"""Standalone unit tests for EventBus (no Qt)."""

from __future__ import annotations

from typing import Any


def test_publish_calls_handlers_in_order() -> None:
    """Handlers are called in subscription order."""
    from app.core.event_bus import EventBus

    bus = EventBus()
    order: list[int] = []

    def handler1(payload: Any) -> None:
        order.append(1)

    def handler2(payload: Any) -> None:
        order.append(2)

    bus.subscribe("test.order", handler1)
    bus.subscribe("test.order", handler2)
    bus.publish("test.order", None)
    assert order == [1, 2]


def test_handler_exception_does_not_break_others() -> None:
    """Exception in one handler does not prevent others from running."""
    from app.core.event_bus import EventBus

    bus = EventBus()
    calls: list[str] = []

    def bad_handler(payload: Any) -> None:
        raise RuntimeError("boom")

    def good_handler(payload: Any) -> None:
        calls.append("good")

    bus.subscribe("test.exc", bad_handler)
    bus.subscribe("test.exc", good_handler)
    bus.publish("test.exc", None)
    assert calls == ["good"]


def test_clear_resets_handlers() -> None:
    """clear() removes all handlers."""
    from app.core.event_bus import EventBus

    bus = EventBus()
    calls: list[int] = []

    def handler(payload: Any) -> None:
        calls.append(1)

    bus.subscribe("test.clear", handler)
    bus.clear()
    bus.publish("test.clear", None)
    assert len(calls) == 0
