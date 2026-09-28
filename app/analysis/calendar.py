"""
Calendar Store — import CSV, query upcoming, manual add
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path


@dataclass
class CalendarEvent:
    time: datetime  # UTC
    currency: str
    impact: str  # high / medium / low
    event: str
    forecast: str = ""
    previous: str = ""
    actual: str = ""


class CalendarStore:
    def __init__(self):
        self.events: list[CalendarEvent] = []

    def import_csv(self, path: str | Path) -> list[CalendarEvent]:
        path = Path(path)
        imported: list[CalendarEvent] = []
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            # normalize fieldnames to lower
            if reader.fieldnames:
                reader.fieldnames = [h.strip().lower() for h in reader.fieldnames]
            for row in reader:
                # handle different column naming
                time_str = row.get("time") or row.get("datetime") or row.get("date") or ""
                currency = (row.get("currency") or row.get("curr") or "").strip().upper()
                impact = (row.get("impact") or row.get("importance") or "low").strip().lower()
                event = (row.get("event") or row.get("title") or "").strip()
                forecast = (row.get("forecast") or "").strip()
                previous = (row.get("previous") or "").strip()
                actual = (row.get("actual") or "").strip()

                # parse time
                dt = self._parse_time(time_str)
                if dt is None:
                    continue
                ev = CalendarEvent(
                    time=dt,
                    currency=currency,
                    impact=impact,
                    event=event,
                    forecast=forecast,
                    previous=previous,
                    actual=actual,
                )
                imported.append(ev)
        # sort by time
        imported.sort(key=lambda e: e.time)
        self.events.extend(imported)
        self.events.sort(key=lambda e: e.time)
        return imported

    def _parse_time(self, s: str) -> datetime | None:
        s = s.strip()
        if not s:
            return None
        # try multiple formats
        fmts = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y/%m/%d %H:%M",
            "%m/%d/%Y %H:%M",
            "%Y-%m-%d",
        ]
        for fmt in fmts:
            try:
                dt = datetime.strptime(s, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=UTC)
                else:
                    dt = dt.astimezone(UTC)
                return dt
            except ValueError:
                continue
        # try fromisoformat
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            else:
                dt = dt.astimezone(UTC)
            return dt
        except Exception:
            return None

    def upcoming(self, currency: str, minutes_ahead: int = 360) -> list[CalendarEvent]:
        now = datetime.now(UTC)
        cutoff = now + timedelta(minutes=minutes_ahead)
        currency = currency.upper().strip()
        result = []
        for ev in self.events:
            if ev.currency != currency:
                continue
            if now <= ev.time <= cutoff:
                result.append(ev)
        # also include events slightly in past? No, only future
        result.sort(key=lambda e: e.time)
        return result

    def add_event_manual(
        self,
        time: datetime,
        currency: str,
        impact: str,
        event: str,
        forecast: str = "",
        previous: str = "",
        actual: str = "",
    ) -> CalendarEvent:
        if time.tzinfo is None:
            time = time.replace(tzinfo=UTC)
        else:
            time = time.astimezone(UTC)
        ev = CalendarEvent(
            time=time,
            currency=currency.upper(),
            impact=impact.lower(),
            event=event,
            forecast=forecast,
            previous=previous,
            actual=actual,
        )
        self.events.append(ev)
        self.events.sort(key=lambda e: e.time)
        return ev
