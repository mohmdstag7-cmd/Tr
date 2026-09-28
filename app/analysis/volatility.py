"""
Volatility Analysis
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .indicators import atr, atr_percentile, average_daily_range


@dataclass
class VolatilityResult:
    atr: float
    atr_percentile: float
    adr: float
    pct_used_today: float
    regime: str  # low / normal / high


class VolatilityAnalysis:
    def analyze(self, bars) -> VolatilityResult:
        if isinstance(bars, dict):
            high = np.asarray(bars.get("high", []), dtype=float)
            low = np.asarray(bars.get("low", []), dtype=float)
            close = np.asarray(bars.get("close", []), dtype=float)
        elif hasattr(bars, "columns"):
            high = np.asarray(bars["high"], dtype=float)
            low = np.asarray(bars["low"], dtype=float)
            close = np.asarray(bars["close"], dtype=float)
        else:
            high = np.asarray([b["high"] for b in bars], dtype=float)
            low = np.asarray([b["low"] for b in bars], dtype=float)
            close = np.asarray([b["close"] for b in bars], dtype=float)

        if len(close) == 0:
            return VolatilityResult(atr=0, atr_percentile=50, adr=0, pct_used_today=0, regime="normal")

        atr_series = atr(high, low, close, 14)
        # last valid ATR
        valid_atr = atr_series[~np.isnan(atr_series)]
        last_atr = float(valid_atr[-1]) if len(valid_atr) else float(np.mean(high - low)) if len(high) else 0.0

        pct = atr_percentile(atr_series, 100)

        adr_val = average_daily_range(high, low, 20)

        # % used today: today's range / ADR
        today_range = float(high[-1] - low[-1]) if len(high) else 0.0
        pct_used = (today_range / adr_val * 100) if adr_val else 0.0

        if pct < 25:
            regime = "low"
        elif pct > 75:
            regime = "high"
        else:
            regime = "normal"

        return VolatilityResult(
            atr=last_atr,
            atr_percentile=float(pct),
            adr=float(adr_val),
            pct_used_today=float(pct_used),
            regime=regime,
        )
