"""Tests for clock module."""

from __future__ import annotations

from datetime import UTC, datetime


def test_system_clock_utc_tz() -> None:
    """system_clock.now_utc() has UTC tzinfo."""
    from app.core.clock import system_clock

    now = system_clock.now_utc()
    assert now.tzinfo == UTC


def test_fixed_clock_returns_set_time() -> None:
    """FixedClock always returns the configured time."""
    from app.core.clock import FixedClock

    fixed_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
    clock = FixedClock(fixed_time)
    assert clock.now_utc() == fixed_time
    assert clock.now_utc() == fixed_time
