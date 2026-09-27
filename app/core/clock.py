"""Clock abstraction for production and tests."""

from __future__ import annotations

from datetime import UTC, datetime


class Clock:
    """System clock abstraction."""

    def now_utc(self) -> datetime:
        """Return current UTC time."""
        return datetime.now(UTC)

    def now_local(self) -> datetime:
        """Return current local time."""
        return datetime.now().astimezone()


class FixedClock(Clock):
    """Clock that always returns a fixed datetime (for tests)."""

    def __init__(self, fixed: datetime) -> None:
        self._fixed = fixed

    def now_utc(self) -> datetime:
        """Return the fixed UTC time."""
        return self._fixed

    def now_local(self) -> datetime:
        """Return the fixed local time."""
        return self._fixed


system_clock = Clock()
