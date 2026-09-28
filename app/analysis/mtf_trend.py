"""
Multi-Timeframe Trend Matrix
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .indicators import adx, ema


@dataclass
class TFTrend:
    timeframe: str
    direction: str  # bullish / bearish / neutral
    strength: int  # 0-100
    ema50: float
    ema200: float
    adx: float
    slope_pct: float


@dataclass
class MTFTrendResult:
    per_tf: dict[str, TFTrend] = field(default_factory=dict)
    bias_score: int = 0  # -100 to +100
    reason: str = ""


class MTFTrendMatrix:
    """
    Takes bars for timeframes M5, M15, M30, H1, H4, D1.
    For each TF: computes EMA50/EMA200 alignment, slope, ADX strength.
    """

    TF_ORDER = ["M5", "M15", "M30", "H1", "H4", "D1"]
    TF_WEIGHTS = {"M5": 1, "M15": 1, "M30": 2, "H1": 3, "H4": 4, "D1": 5}

    def analyze(self, bars_by_tf: dict[str, dict]) -> MTFTrendResult:
        per_tf: dict[str, TFTrend] = {}
        scores = []

        for tf in self.TF_ORDER:
            if tf not in bars_by_tf:
                continue
            bars = bars_by_tf[tf]
            # support both dict with arrays and DataFrame-like
            if isinstance(bars, dict):
                close = np.asarray(bars.get("close", []), dtype=float)
                high = np.asarray(bars.get("high", close), dtype=float)
                low = np.asarray(bars.get("low", close), dtype=float)
            else:
                # assume DataFrame
                close = np.asarray(bars["close"], dtype=float)
                high = np.asarray(bars["high"], dtype=float)
                low = np.asarray(bars["low"], dtype=float)

            if len(close) < 200:
                # not enough data -> neutral
                per_tf[tf] = TFTrend(
                    timeframe=tf,
                    direction="neutral",
                    strength=0,
                    ema50=float(close[-1]) if len(close) else 0,
                    ema200=float(close[-1]) if len(close) else 0,
                    adx=0.0,
                    slope_pct=0.0,
                )
                scores.append(0)
                continue

            e50 = ema(close, 50)
            e200 = ema(close, 200)
            adx_vals = adx(high, low, close, 14)

            last_e50 = float(e50[-1])
            last_e200 = float(e200[-1])
            last_adx = float(adx_vals[-1]) if not np.isnan(adx_vals[-1]) else 0.0
            last_close = float(close[-1])

            # slope over last 5 bars
            if len(e50) >= 6 and e50[-6] != 0:
                slope = (last_e50 - float(e50[-6])) / float(e50[-6]) * 100
            else:
                slope = 0.0

            # direction logic
            if last_e50 > last_e200 and last_close > last_e50 and slope > 0:
                direction = "bullish"
            elif last_e50 < last_e200 and last_close < last_e50 and slope < 0:
                direction = "bearish"
            else:
                # check alignment without slope
                if last_e50 > last_e200 and last_close > last_e200:
                    direction = "bullish"
                elif last_e50 < last_e200 and last_close < last_e200:
                    direction = "bearish"
                else:
                    direction = "neutral"

            # strength 0-100 based on ADX and EMA distance
            ema_dist_pct = abs(last_e50 - last_e200) / last_close * 100 if last_close != 0 else 0
            # ADX contributes 0-70, distance 0-30
            adx_component = min(last_adx / 50 * 70, 70) if last_adx else 0
            dist_component = min(ema_dist_pct * 10, 30)
            strength = int(min(adx_component + dist_component, 100))
            if direction == "neutral":
                strength = int(min(last_adx / 50 * 50, 50))

            per_tf[tf] = TFTrend(
                timeframe=tf,
                direction=direction,
                strength=strength,
                ema50=last_e50,
                ema200=last_e200,
                adx=last_adx,
                slope_pct=float(slope),
            )

            # score per TF: +strength if bullish, -strength if bearish
            if direction == "bullish":
                scores.append(strength * self.TF_WEIGHTS[tf])
            elif direction == "bearish":
                scores.append(-strength * self.TF_WEIGHTS[tf])
            else:
                scores.append(0)

        # overall bias -100 to +100
        if scores:
            total_weight = sum(self.TF_WEIGHTS[tf] for tf in per_tf.keys())
            # normalize: max possible is 100*weight per TF
            max_score = 100 * total_weight
            raw = sum(scores)
            bias = int(max(-100, min(100, (raw / max_score * 100) if max_score else 0)))
        else:
            bias = 0

        # reason string
        bullish_tfs = [tf for tf, v in per_tf.items() if v.direction == "bullish"]
        bearish_tfs = [tf for tf, v in per_tf.items() if v.direction == "bearish"]
        if bias > 30:
            reason = f"Bullish alignment on {', '.join(bullish_tfs) or 'higher TFs'} (bias {bias})"
        elif bias < -30:
            reason = f"Bearish alignment on {', '.join(bearish_tfs) or 'higher TFs'} (bias {bias})"
        elif bullish_tfs and bearish_tfs:
            reason = f"Mixed: bullish {','.join(bullish_tfs)} vs bearish {','.join(bearish_tfs)} (bias {bias})"
        else:
            reason = f"Neutral / ranging (bias {bias})"

        return MTFTrendResult(per_tf=per_tf, bias_score=bias, reason=reason)
