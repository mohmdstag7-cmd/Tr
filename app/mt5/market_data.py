"""Bar fetching and sanity checks."""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

from app.observability import get_logger

if TYPE_CHECKING:
    from app.mt5.gateway import MT5Gateway
    from app.mt5.types import Bar

logger = get_logger("market_data")

_TF_SECONDS: dict[str, int] = {
    "M1": 60,
    "M5": 300,
    "M15": 900,
    "M30": 1800,
    "H1": 3600,
    "H4": 14400,
    "D1": 86400,
    "W1": 604800,
    "MN1": 2592000,
}


class MarketDataStore:
    """Per-symbol/timeframe cache of bars."""

    def __init__(self) -> None:
        self._cache: dict[tuple[str, str], list[Bar]] = {}
        self._last_fetch: dict[tuple[str, str], dt.datetime] = {}

    def get_bars(self, gateway: MT5Gateway, symbol: str, timeframe: str, count: int) -> list[Bar]:
        fut = gateway.copy_rates_from_pos(symbol, timeframe, 0, count)
        bars = fut.result(timeout=65)
        key = (symbol, timeframe)
        self._cache[key] = bars
        self._last_fetch[key] = dt.datetime.now(tz=dt.UTC)
        issues = check_bar_sanity(bars)
        for iss in issues:
            logger.warning(f"Bar sanity {symbol} {timeframe}: {iss}")
        return bars

    def append_incremental(self, gateway: MT5Gateway, symbol: str, timeframe: str) -> list[Bar]:
        key = (symbol, timeframe)
        existing = self._cache.get(key, [])
        # fetch last 10 bars and merge new ones
        fut = gateway.copy_rates_from_pos(symbol, timeframe, 0, 10)
        new_bars = fut.result(timeout=65)
        if not existing:
            self._cache[key] = new_bars
            return new_bars
        # merge by time
        existing_times = {b.time for b in existing}
        added = [b for b in new_bars if b.time not in existing_times]
        if added:
            merged = sorted(existing + added, key=lambda b: b.time)
            self._cache[key] = merged
        return added


def check_bar_sanity(bars: list[Bar], atr: float | None = None) -> list[str]:
    """Return list of sanity issues."""
    issues: list[str] = []
    if not bars:
        return ["no_bars"]
    # zero-volume
    for b in bars:
        if b.tick_volume == 0:
            issues.append(f"zero_volume:{b.time.isoformat()}")
            break
    # missing bars / gaps
    if len(bars) >= 2:
        tf = bars[0].timeframe
        expected = _TF_SECONDS.get(tf, 900)
        for i in range(1, len(bars)):
            delta = (bars[i].time - bars[i - 1].time).total_seconds()
            if delta > expected * 1.5:
                # weekend gap?
                if delta > 48 * 3600:
                    issues.append(f"weekend_gap:{bars[i-1].time.isoformat()}->{bars[i].time.isoformat()} gap={delta}s")
                else:
                    issues.append(f"missing_bars:gap {delta}s at {bars[i].time.isoformat()}")
            if delta < 0:
                issues.append(f"time_jump:{bars[i].time.isoformat()}")
    # spike detection
    if atr is not None and atr > 0:
        for i in range(1, len(bars)):
            prev_close = bars[i - 1].close
            spike = abs(bars[i].high - prev_close)
            if spike > 5 * atr:
                issues.append(f"spike:{bars[i].time.isoformat()} high={bars[i].high} prev_close={prev_close} atr={atr}")
                break
    else:
        # without ATR, use simple heuristic: high > 2% away from close
        for i in range(1, len(bars)):
            if bars[i - 1].close != 0:
                pct = abs(bars[i].high - bars[i - 1].close) / bars[i - 1].close
                if pct > 0.05:  # 5% spike
                    issues.append(f"spike:{bars[i].time.isoformat()} pct={pct:.2%}")
                    break
    return issues
