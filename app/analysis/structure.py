"""
Market Structure — swing detection, HH/HL/LH/LL, BOS/CHoCH
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class Swing:
    index: int
    price: float
    type: str  # high / low
    confirmed: bool = True


@dataclass
class StructureResult:
    swings: list[Swing] = field(default_factory=list)
    sequence: list[str] = field(default_factory=list)  # HH, HL, LH, LL
    bos: bool = False
    choch: bool = False
    market_type: str = "ranging"  # trending / ranging
    last_swing_high: float | None = None
    last_swing_low: float | None = None
    bos_direction: str | None = None


class MarketStructure:
    """
    Finds confirmed swing highs/lows (confirmed after N bars, no look-ahead).
    Classifies HH/HL/LH/LL, detects BOS and CHoCH.
    """

    def __init__(self, swing_lookback: int = 2):
        self.swing_lookback = swing_lookback

    def analyze(self, bars) -> StructureResult:
        # normalize bars
        if isinstance(bars, dict):
            high = np.asarray(bars.get("high", []), dtype=float)
            low = np.asarray(bars.get("low", []), dtype=float)
            close = np.asarray(bars.get("close", []), dtype=float)
        elif hasattr(bars, "columns"):
            high = np.asarray(bars["high"], dtype=float)
            low = np.asarray(bars["low"], dtype=float)
            close = np.asarray(bars["close"], dtype=float)
        else:
            # list of dicts
            high = np.asarray([b["high"] for b in bars], dtype=float)
            low = np.asarray([b["low"] for b in bars], dtype=float)
            close = np.asarray([b["close"] for b in bars], dtype=float)

        n = len(close)
        N = self.swing_lookback
        swings: list[Swing] = []

        # swing detection: point is max/min in window [i-N, i+N]
        # confirmed only if i <= n - N -1 (no look-ahead for last N bars)
        for i in range(N, n - N):
            # swing high
            window_high = high[i - N : i + N + 1]
            if high[i] == np.max(window_high) and np.sum(window_high == high[i]) == 1:
                # ensure it's strictly greater than neighbors
                swings.append(Swing(index=i, price=float(high[i]), type="high", confirmed=True))
            # swing low
            window_low = low[i - N : i + N + 1]
            if low[i] == np.min(window_low) and np.sum(window_low == low[i]) == 1:
                swings.append(Swing(index=i, price=float(low[i]), type="low", confirmed=True))

        # sort by index
        swings.sort(key=lambda s: s.index)

        # classify HH/HL/LH/LL
        sequence: list[str] = []
        last_high = None
        last_low = None
        for s in swings:
            if s.type == "high":
                if last_high is not None:
                    if s.price > last_high:
                        sequence.append("HH")
                    else:
                        sequence.append("LH")
                last_high = s.price
            else:
                if last_low is not None:
                    if s.price > last_low:
                        sequence.append("HL")
                    else:
                        sequence.append("LL")
                last_low = s.price

        # BOS and CHoCH detection
        bos = False
        choch = False
        bos_direction = None

        # BOS: close breaks prior swing high/low
        if len(swings) >= 2 and n > 0:
            # last confirmed swing high/low before last bars
            swing_highs = [s for s in swings if s.type == "high"]
            swing_lows = [s for s in swings if s.type == "low"]
            last_close = float(close[-1])
            if swing_highs:
                prior_high = swing_highs[-1].price
                # if there are at least 2 highs, check break of previous high
                if len(swing_highs) >= 2:
                    prior_high = swing_highs[-2].price
                    if last_close > prior_high:
                        bos = True
                        bos_direction = "bullish"
                elif last_close > prior_high:
                    bos = True
                    bos_direction = "bullish"
            if not bos and swing_lows:
                prior_low = swing_lows[-1].price
                if len(swing_lows) >= 2:
                    prior_low = swing_lows[-2].price
                    if last_close < prior_low:
                        bos = True
                        bos_direction = "bearish"
                elif last_close < prior_low:
                    bos = True
                    bos_direction = "bearish"

        # CHoCH: change of character — sequence flips from bullish (HH/HL) to bearish (LH/LL) or vice versa
        if len(sequence) >= 3:
            # look at last 3 sequence markers
            recent = sequence[-3:]
            bullish_count = sum(1 for x in recent if x in ("HH", "HL"))
            bearish_count = sum(1 for x in recent if x in ("LH", "LL"))
            # if earlier trend was bullish and recent is bearish -> CHoCH
            earlier = sequence[:-3] if len(sequence) > 3 else sequence[:2]
            if earlier:
                earlier_bull = sum(1 for x in earlier if x in ("HH", "HL"))
                earlier_bear = sum(1 for x in earlier if x in ("LH", "LL"))
                if earlier_bull > earlier_bear and bearish_count > bullish_count:
                    choch = True
                elif earlier_bear > earlier_bull and bullish_count > bearish_count:
                    choch = True
            # also simple: last two are opposite of prior
            if not choch and len(sequence) >= 4:
                if sequence[-1] in ("LH", "LL") and sequence[-3] in ("HH", "HL"):
                    choch = True
                elif sequence[-1] in ("HH", "HL") and sequence[-3] in ("LH", "LL"):
                    choch = True

        # market type
        if bos and sequence.count("HH") + sequence.count("HL") >= 2:
            market_type = "trending"
        elif bos and sequence.count("LL") + sequence.count("LH") >= 2:
            market_type = "trending"
        elif len(sequence) >= 4 and sequence.count("HH") >= 2 and sequence.count("HL") >= 1:
            market_type = "trending"
        elif len(sequence) >= 4 and sequence.count("LL") >= 2 and sequence.count("LH") >= 1:
            market_type = "trending"
        else:
            market_type = "ranging"

        last_swing_high = swing_highs[-1].price if "swing_highs" in locals() and swing_highs else None
        last_swing_low = swing_lows[-1].price if "swing_lows" in locals() and swing_lows else None

        return StructureResult(
            swings=swings,
            sequence=sequence,
            bos=bos,
            choch=choch,
            market_type=market_type,
            last_swing_high=last_swing_high,
            last_swing_low=last_swing_low,
            bos_direction=bos_direction,
        )
