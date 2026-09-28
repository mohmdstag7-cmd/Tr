"""
Analysis Card — plain-language analysis string
"""

from __future__ import annotations


class AnalysisCard:
    def generate(self, symbol, mtf_trend, structure, levels, volatility, session, patterns) -> str:
        """
        Returns a plain-language analysis string.
        Example: "XAUUSD — H4 uptrend, H1 pullback into support 2,318 (0.4 ATR), volatility high, London session, USD CPI in 3h → wait."
        """
        parts = [f"{symbol} —"]

        # MTF trend
        try:
            if hasattr(mtf_trend, "bias_score"):
                bias = mtf_trend.bias_score
                reason = getattr(mtf_trend, "reason", "")
                if bias > 30:
                    parts.append(f"bias bullish ({bias})")
                elif bias < -30:
                    parts.append(f"bias bearish ({bias})")
                else:
                    parts.append(f"bias neutral ({bias})")
                if reason:
                    parts.append(f"[{reason}]")
                # per-TF details
                per_tf = getattr(mtf_trend, "per_tf", {})
                if per_tf:
                    tf_str = ", ".join(f"{tf}:{v.direction[:4]}" for tf, v in per_tf.items())
                    parts.append(f"MTF:{tf_str}")
            elif isinstance(mtf_trend, dict):
                bias = mtf_trend.get("bias_score", mtf_trend.get("bias", 0))
                parts.append(f"bias {bias}")
            else:
                parts.append(str(mtf_trend))
        except Exception:
            parts.append("MTF n/a")

        # Structure
        try:
            if hasattr(structure, "market_type"):
                parts.append(f"{structure.market_type}")
                if getattr(structure, "bos", False):
                    direction = getattr(structure, "bos_direction", "")
                    parts.append(f"BOS {direction}")
                if getattr(structure, "choch", False):
                    parts.append("CHoCH")
                seq = getattr(structure, "sequence", [])
                if seq:
                    parts.append(f"seq:{','.join(seq[-3:])}")
            elif isinstance(structure, dict):
                parts.append(structure.get("market_type", "ranging"))
            elif structure:
                parts.append(str(structure))
        except Exception:
            pass

        # Levels
        try:
            if levels:
                # find nearest support/resistance
                nearest = None
                if isinstance(levels, list) and len(levels) > 0:
                    # levels sorted by distance
                    nearest = levels[0]
                    if hasattr(nearest, "price"):
                        parts.append(f"nearest {nearest.type} {nearest.price:.2f} ({nearest.distance_in_atr:.1f} ATR, str {nearest.strength})")
                    elif isinstance(nearest, dict):
                        parts.append(f"nearest {nearest.get('type')} {nearest.get('price')}")
                else:
                    parts.append(f"{len(levels)} levels")
        except Exception:
            pass

        # Volatility
        try:
            if hasattr(volatility, "regime"):
                parts.append(
                    f"volatility {volatility.regime} (ATR {volatility.atr:.4f}, {volatility.atr_percentile:.0f}th pct, ADR {volatility.adr:.4f} {volatility.pct_used_today:.0f}% used)"  # noqa: E501
                )
            elif isinstance(volatility, dict):
                parts.append(f"volatility {volatility.get('regime','n/a')}")
        except Exception:
            pass

        # Session
        try:
            if hasattr(session, "name"):
                parts.append(f"{session.name} session")
                if hasattr(session, "time_remaining"):
                    mins = int(session.time_remaining.total_seconds() // 60)
                    parts.append(f"{mins}m left")
            elif isinstance(session, dict):
                parts.append(f"{session.get('name','')} session")
            elif isinstance(session, str):
                parts.append(f"{session} session")
        except Exception:
            pass

        # Patterns
        try:
            if patterns:
                if isinstance(patterns, list):
                    pat_str = ", ".join(f"{p.type}:{p.direction}" for p in patterns[:3])
                    parts.append(f"patterns [{pat_str}]")
                else:
                    parts.append(f"patterns {patterns}")
        except Exception:
            pass

        # Action hint
        # Simple logic: if high volatility + strong bias + near support -> wait or ready
        try:
            bias = getattr(mtf_trend, "bias_score", 0) if hasattr(mtf_trend, "bias_score") else 0
            vol_regime = getattr(volatility, "regime", "normal") if hasattr(volatility, "regime") else "normal"
            if abs(bias) > 50 and vol_regime == "high":
                parts.append("→ caution: high volatility")
            elif abs(bias) > 50:
                parts.append("→ ready")
            elif abs(bias) < 20:
                parts.append("→ wait")
            else:
                parts.append("→ forming")
        except Exception:
            parts.append("→ wait")

        return ", ".join(parts)
