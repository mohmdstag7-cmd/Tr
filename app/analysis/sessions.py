"""
Session Clock — Asia, London, NY
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass
class SessionInfo:
    name: str
    start: datetime
    end: datetime
    time_remaining: timedelta
    is_overlap: bool = False


class SessionClock:
    """
    Sessions in UTC:
      Asia   00:00-07:00
      London 07:00-16:00
      NY     12:00-21:00
    Overlap London+NY 12:00-16:00
    """

    def current_session(self, time_utc: datetime) -> SessionInfo:
        if time_utc.tzinfo is None:
            time_utc = time_utc.replace(tzinfo=UTC)
        else:
            time_utc = time_utc.astimezone(UTC)

        hour = time_utc.hour + time_utc.minute / 60 + time_utc.second / 3600
        date = time_utc.date()

        # helper to make datetime for today
        def dt(h, m=0):
            return datetime(date.year, date.month, date.day, h, m, tzinfo=UTC)

        is_overlap = 12 <= hour < 16

        if is_overlap:
            name = "London/NY Overlap"
            start = dt(12)
            end = dt(16)
        elif 0 <= hour < 7:
            name = "Asia"
            start = dt(0)
            end = dt(7)
        elif 7 <= hour < 12:
            name = "London"
            start = dt(7)
            end = dt(16)
        elif 12 <= hour < 16:
            # already handled overlap, but keep
            name = "London/NY Overlap"
            start = dt(12)
            end = dt(16)
        elif 16 <= hour < 21:
            name = "NY"
            start = dt(12)
            end = dt(21)
        elif 21 <= hour < 24:
            name = "Post-NY"
            start = dt(21)
            end = dt(0) + timedelta(days=1)
        else:
            name = "Asia"
            start = dt(0)
            end = dt(7)

        # if after end (e.g., Post-NY), adjust
        if time_utc >= end:
            end += timedelta(days=1)

        remaining = end - time_utc
        if remaining.total_seconds() < 0:
            remaining = timedelta(0)

        return SessionInfo(name=name, start=start, end=end, time_remaining=remaining, is_overlap=is_overlap)

    def is_overlap(self, time_utc: datetime) -> bool:
        if time_utc.tzinfo is None:
            time_utc = time_utc.replace(tzinfo=UTC)
        else:
            time_utc = time_utc.astimezone(UTC)
        hour = time_utc.hour + time_utc.minute / 60
        return 12 <= hour < 16

    def is_weekend(self, time_utc: datetime) -> bool:
        if time_utc.tzinfo is None:
            time_utc = time_utc.replace(tzinfo=UTC)
        else:
            time_utc = time_utc.astimezone(UTC)
        # Forex weekend: Saturday and Sunday
        # Also Friday 22:00 UTC onwards is weekend, Sunday 22:00 onwards is open
        # For simplicity, use weekday 5,6
        return time_utc.weekday() in (5, 6)
