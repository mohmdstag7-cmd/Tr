"""
Candle Patterns — informational only, never standalone signals
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class Pattern:
    type: str  # engulfing, pin_bar, inside_bar, doji
    bar_index: int
    direction: str  # bullish / bearish / neutral
    confidence: float  # 0-1


class CandlePatterns:
    def detect(self, bars) -> list[Pattern]:
        if isinstance(bars, dict):
            open_ = np.asarray(bars.get("open", bars.get("close", [])), dtype=float)
            high = np.asarray(bars.get("high", []), dtype=float)
            low = np.asarray(bars.get("low", []), dtype=float)
            close = np.asarray(bars.get("close", []), dtype=float)
        elif hasattr(bars, "columns"):
            open_ = np.asarray(bars["open"] if "open" in bars else bars["close"], dtype=float)
            high = np.asarray(bars["high"], dtype=float)
            low = np.asarray(bars["low"], dtype=float)
            close = np.asarray(bars["close"], dtype=float)
        else:
            open_ = np.asarray([b.get("open", b["close"]) for b in bars], dtype=float)
            high = np.asarray([b["high"] for b in bars], dtype=float)
            low = np.asarray([b["low"] for b in bars], dtype=float)
            close = np.asarray([b["close"] for b in bars], dtype=float)

        n = len(close)
        patterns: list[Pattern] = []
        if n < 2:
            return patterns

        for i in range(1, n):
            o = open_[i]
            h = high[i]
            lo = low[i]
            c = close[i]
            po = open_[i - 1]
            ph = high[i - 1]
            pl = low[i - 1]
            pc = close[i - 1]

            body = abs(c - o)
            prev_body = abs(pc - po)
            candle_range = h - lo if h != lo else 1e-9
            ph - pl if ph != pl else 1e-9

            # Doji: body < 10% of range
            if body / candle_range < 0.1 and candle_range > 0:
                patterns.append(Pattern(type="doji", bar_index=i, direction="neutral", confidence=0.8))

            # Inside bar: current high < prev high and low > prev low
            if h < ph and lo > pl:
                patterns.append(Pattern(type="inside_bar", bar_index=i, direction="neutral", confidence=0.7))

            # Engulfing
            # bullish engulfing: prev bearish (pc < po), current bullish (c > o), current body engulfs prev body
            is_prev_bearish = pc < po
            is_prev_bullish = pc > po
            is_curr_bullish = c > o
            is_curr_bearish = c < o

            if is_prev_bearish and is_curr_bullish:
                # body engulfs: open <= prev close and close >= prev open
                if o <= pc and c >= po and body > prev_body:
                    patterns.append(Pattern(type="engulfing", bar_index=i, direction="bullish", confidence=0.85))
            if is_prev_bullish and is_curr_bearish:
                if o >= pc and c <= po and body > prev_body:
                    patterns.append(Pattern(type="engulfing", bar_index=i, direction="bearish", confidence=0.85))

            # Pin bar / hammer / shooting star
            # long wick > 2*body, small body near one end
            upper_wick = h - max(o, c)
            lower_wick = min(o, c) - lo
            if body > 0 and candle_range > 0:
                # hammer: long lower wick, small upper wick, bullish
                if lower_wick > 2 * body and upper_wick < 0.3 * body:
                    # hammer is bullish if near low
                    patterns.append(Pattern(type="pin_bar", bar_index=i, direction="bullish", confidence=0.75))
                # shooting star: long upper wick
                elif upper_wick > 2 * body and lower_wick < 0.3 * body:
                    patterns.append(Pattern(type="pin_bar", bar_index=i, direction="bearish", confidence=0.75))
                # also detect pin_bar with wick > 1.5*body and body in top/bottom 1/3
                elif lower_wick > 1.5 * body and (max(o, c) - lo) / candle_range > 0.7:
                    # body near top, long lower wick
                    if upper_wick < body:
                        patterns.append(Pattern(type="pin_bar", bar_index=i, direction="bullish", confidence=0.6))
                elif upper_wick > 1.5 * body and (h - min(o, c)) / candle_range > 0.7:
                    if lower_wick < body:
                        patterns.append(Pattern(type="pin_bar", bar_index=i, direction="bearish", confidence=0.6))

        return patterns
