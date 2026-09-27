"""Smoke tests for Phase 1 foundation."""

from __future__ import annotations

import re
from datetime import UTC
from typing import Any


def test_app_imports() -> None:
    """Verify core app modules are importable."""
    import app  # noqa: F401
    from app.__version__ import __version__  # noqa: F401
    from app.main import main  # noqa: F401

    assert app is not None
    assert __version__ is not None
    assert main is not None


def test_version_string() -> None:
    """Verify __version__ matches semantic version pattern."""
    from app.__version__ import __version__

    assert re.match(r"^\d+\.\d+\.\d+$", __version__) is not None


def test_event_bus_basic() -> None:
    """Subscribe, publish, handler called once with payload."""
    from app.core.event_bus import EventBus

    bus = EventBus()
    calls: list[Any] = []

    def handler(payload: Any) -> None:
        calls.append(payload)

    bus.subscribe("test.event", handler)
    bus.publish("test.event", {"value": 42})
    assert len(calls) == 1
    assert calls[0] == {"value": 42}


def test_event_bus_unsubscribe() -> None:
    """Unsubscribe stops further calls."""
    from app.core.event_bus import EventBus

    bus = EventBus()
    calls: list[int] = []

    def handler(payload: int) -> None:
        calls.append(payload)

    # subscribe() returns an unsubscribe callable.
    unsub = bus.subscribe("test.event", handler)
    assert callable(unsub)
    unsub()
    bus.publish("test.event", 123)
    assert len(calls) == 0


def test_clock_now_utc_is_utc() -> None:
    """system_clock.now_utc() returns UTC timezone."""

    from app.core.clock import system_clock

    now = system_clock.now_utc()
    assert now.tzinfo is UTC


def test_container_register_resolve() -> None:
    """Register a factory, resolve returns the same instance."""
    from app.core.di import Container

    class _Marker:
        pass

    container = Container()
    container.register(_Marker, lambda: _Marker())
    first = container.resolve(_Marker)
    second = container.resolve(_Marker)
    assert first is second


def test_tokens_dark_has_all_colors(tokens_dark: Any) -> None:
    """Every color attribute in dark tokens is a #RRGGBB string."""
    pattern = re.compile(r"^#[0-9A-Fa-f]{6}$")
    values = vars(tokens_dark).values() if hasattr(tokens_dark, "__dict__") else []
    # Also check dir-based attributes that look like colors
    candidates: list[str] = []
    for val in values:
        if isinstance(val, str) and val.startswith("#"):
            candidates.append(val)
    # Fallback: inspect all string attributes starting with #
    if not candidates:
        for name in dir(tokens_dark):
            if name.startswith("_"):
                continue
            val = getattr(tokens_dark, name)
            if isinstance(val, str) and val.startswith("#"):
                candidates.append(val)
    assert len(candidates) > 0
    for color in candidates:
        assert pattern.match(color) is not None, f"Invalid color: {color}"


def test_tokens_light_has_all_colors(tokens_light: Any) -> None:
    """Every color attribute in light tokens is a #RRGGBB string."""
    pattern = re.compile(r"^#[0-9A-Fa-f]{6}$")
    values = vars(tokens_light).values() if hasattr(tokens_light, "__dict__") else []
    candidates: list[str] = []
    for val in values:
        if isinstance(val, str) and val.startswith("#"):
            candidates.append(val)
    if not candidates:
        for name in dir(tokens_light):
            if name.startswith("_"):
                continue
            val = getattr(tokens_light, name)
            if isinstance(val, str) and val.startswith("#"):
                candidates.append(val)
    assert len(candidates) > 0
    for color in candidates:
        assert pattern.match(color) is not None, f"Invalid color: {color}"


def test_qss_generation_returns_nonempty_string(tokens_dark: Any) -> None:
    """build_qss returns a non-empty stylesheet string."""
    from app.ui.theme.qss import build_qss

    qss = build_qss("dark")
    assert isinstance(qss, str)
    assert len(qss) > 1000


def test_i18n_default_is_en() -> None:
    """Default language is English."""
    from app.ui.i18n import current_language

    assert current_language() == "en"


def test_i18n_set_language_fa() -> None:
    """After set_language('fa'), tr('approve') returns Persian."""
    from app.ui.i18n import current_language, set_language, tr

    original = current_language()
    try:
        set_language("fa")
        assert tr("approve") == "تأیید"
    finally:
        set_language(original)


def test_i18n_unknown_key_returns_key() -> None:
    """Unknown translation key returns the key itself."""
    from app.ui.i18n import tr

    assert tr("definitely_unknown_key_xyz") == "definitely_unknown_key_xyz"
