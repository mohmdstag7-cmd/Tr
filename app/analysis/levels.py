"""
Key Levels — S/R, session highs/lows, round numbers, previous day/week
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import numpy as np


@dataclass
class Level:
    price: float
    type: str  # support, resistance, session_high, session_low, round_number, prev_day_high, etc.
    distance_in_atr: float
    strength: int  # 1-5


class KeyLevels:
    def compute(self, bars, swings, atr_value: float) -> list[Level]:
        """
        bars: dict with high, low, close, time (optional)
        swings: list[Swing] or list[dict]
        atr_value: float (current ATR)
        """
        if isinstance(bars, dict):
            high = np.asarray(bars.get("high", []), dtype=float)
            low = np.asarray(bars.get("low", []), dtype=float)
            close = np.asarray(bars.get("close", []), dtype=float)
            times = bars.get("time", None)
        elif hasattr(bars, "columns"):
            high = np.asarray(bars["high"], dtype=float)
            low = np.asarray(bars["low"], dtype=float)
            close = np.asarray(bars["close"], dtype=float)
            times = bars["time"] if "time" in bars else None
        else:
            high = np.asarray([b["high"] for b in bars], dtype=float)
            low = np.asarray([b["low"] for b in bars], dtype=float)
            close = np.asarray([b["close"] for b in bars], dtype=float)
            times = None

        if close.size == 0:
            return []

        last_close = float(close[-1])
        if atr_value is None or atr_value == 0 or np.isnan(atr_value):
            atr_value = float(np.mean(high - low)) if len(high) else 1.0
            if atr_value == 0:
                atr_value = 1.0

        levels: list[Level] = []

        # 1. S/R from swing clustering
        if swings:
            # extract prices
            swing_prices = []
            for s in swings:
                if isinstance(s, dict):
                    swing_prices.append(float(s["price"]))
                else:
                    swing_prices.append(float(s.price))
            # cluster within 0.5 ATR
            clustered = []
            sorted_prices = sorted(swing_prices)
            cluster = [sorted_prices[0]]
            for p in sorted_prices[1:]:
                if abs(p - np.mean(cluster)) < 0.5 * atr_value:
                    cluster.append(p)
                else:
                    clustered.append(cluster)
                    cluster = [p]
            clustered.append(cluster)

            for cl in clustered:
                price = float(np.mean(cl))
                count = len(cl)
                # determine support vs resistance
                lvl_type = "resistance" if price > last_close else "support"
                strength = min(5, max(1, count + 1))  # 1-5
                dist = abs(price - last_close) / atr_value
                levels.append(Level(price=price, type=lvl_type, distance_in_atr=float(dist), strength=strength))

        # 2. Previous day/week high/low/close — if times available, else use rolling window
        if times is not None:
            try:
                # times may be datetime objects or timestamps
                # For simplicity, if we have at least 24*12 M5 bars, approximate day
                # Use last 288 M5 bars as a day, 1440 as week
                if len(close) >= 288:
                    day_high = float(np.max(high[-288:]))
                    day_low = float(np.min(low[-288:]))
                    day_close = float(close[-288])
                    for price, t in [(day_high, "prev_day_high"), (day_low, "prev_day_low"), (day_close, "prev_day_close")]:
                        dist = abs(price - last_close) / atr_value
                        if dist < 5:  # only nearby levels
                            lvl_type = "resistance" if price > last_close else "support"
                            levels.append(Level(price=price, type=t, distance_in_atr=float(dist), strength=3))
                if len(close) >= 1440:
                    week_high = float(np.max(high[-1440:]))
                    week_low = float(np.min(low[-1440:]))
                    for price, t in [(week_high, "prev_week_high"), (week_low, "prev_week_low")]:
                        dist = abs(price - last_close) / atr_value
                        if dist < 8:
                            levels.append(Level(price=price, type=t, distance_in_atr=float(dist), strength=4))
            except Exception:
                pass
        else:
            # fallback: use recent highs/lows as proxy for prev day/week
            if len(high) >= 20:
                recent_high = float(np.max(high[-20:]))
                recent_low = float(np.min(low[-20:]))
                for price, t in [(recent_high, "prev_day_high"), (recent_low, "prev_day_low")]:
                    dist = abs(price - last_close) / atr_value
                    levels.append(Level(price=price, type=t, distance_in_atr=float(dist), strength=2))

        # 3. Session highs/lows (Asia 00-07, London 07-16, NY 12-21 UTC)
        if times is not None:
            try:
                # times is array of datetime
                session_defs = {
                    "asia": (0, 7),
                    "london": (7, 16),
                    "ny": (12, 21),
                }
                for sess_name, (start_h, end_h) in session_defs.items():
                    sess_high = None
                    sess_low = None
                    for i, t in enumerate(times):
                        if isinstance(t, int | float):
                            dt = datetime.fromtimestamp(t, tz=UTC)
                        elif isinstance(t, datetime):
                            dt = t if t.tzinfo else t.replace(tzinfo=UTC)
                        else:
                            continue
                        hour = dt.hour + dt.minute / 60
                        if start_h <= hour < end_h:
                            if sess_high is None or high[i] > sess_high:
                                sess_high = float(high[i])
                            if sess_low is None or low[i] < sess_low:
                                sess_low = float(low[i])
                    if sess_high is not None:
                        dist = abs(sess_high - last_close) / atr_value
                        levels.append(Level(price=sess_high, type=f"{sess_name}_high", distance_in_atr=float(dist), strength=2))
                    if sess_low is not None:
                        dist = abs(sess_low - last_close) / atr_value
                        levels.append(Level(price=sess_low, type=f"{sess_name}_low", distance_in_atr=float(dist), strength=2))
            except Exception:
                pass
        else:
            # synthetic session levels: split bars into 3 equal parts
            if len(high) >= 30:
                n = len(high)
                for sess_name, sl in [("asia", slice(0, n // 3)), ("london", slice(n // 3, 2 * n // 3)), ("ny", slice(2 * n // 3, n))]:
                    sess_high = float(np.max(high[sl]))
                    sess_low = float(np.min(low[sl]))
                    for price, t in [(sess_high, f"{sess_name}_high"), (sess_low, f"{sess_name}_low")]:
                        dist = abs(price - last_close) / atr_value
                        levels.append(Level(price=price, type=t, distance_in_atr=float(dist), strength=2))

        # 4. Round numbers
        # For FX: nearest 100 pips = 0.01 (or 1.00 for JPY), for gold: nearest $10
        candidates = []
        # nearest 1.00 (100 pips for most FX)
        candidates.append(float(round(last_close)))
        candidates.append(round(last_close * 100) / 100)  # 0.01
        # nearest 10 for gold
        candidates.append(round(last_close / 10) * 10)
        # nearest 50 for gold
        candidates.append(round(last_close / 50) * 50)
        # deduplicate
        seen = set()
        for price in candidates:
            if price == 0 or price in seen:
                continue
            seen.add(price)
            # only if within 3 ATR
            dist = abs(price - last_close) / atr_value
            if dist < 3 and dist > 0.05:
                levels.append(Level(price=float(price), type="round_number", distance_in_atr=float(dist), strength=2))

        # sort by distance
        levels.sort(key=lambda level: level.distance_in_atr)
        return levels
