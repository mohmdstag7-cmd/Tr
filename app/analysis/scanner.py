"""
Opportunity Scanner — ranks symbols by setup state and probability × EV
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Opportunity:
    symbol: str
    state: str  # forming / ready
    score: float
    reason: str


class OpportunityScanner:
    def scan(self, symbols: list[str], analysis_results: dict) -> list[Opportunity]:
        """
        analysis_results: dict symbol -> dict or object with fields like
          bias, strength, structure, volatility, patterns, etc.
        For flexibility, supports:
          - dict with keys: score, bias, mtf_bias, structure, volatility_regime
          - object with attributes
        """
        opportunities: list[Opportunity] = []

        for sym in symbols:
            info = analysis_results.get(sym, {})

            # extract score
            score = 0.0
            reason_parts = []

            if isinstance(info, dict):
                # try multiple keys
                if "score" in info:
                    score = float(info["score"])
                elif "bias" in info:
                    score = float(info["bias"])
                elif "mtf_bias" in info:
                    score = float(info["mtf_bias"])
                elif "bias_score" in info:
                    score = float(info["bias_score"])
                else:
                    # compute from components
                    bias = info.get("bias_score", info.get("bias", 0))
                    strength = info.get("strength", 0)
                    score = float(bias) * 0.7 + float(strength) * 0.3

                # build reason
                if "reason" in info:
                    reason_parts.append(str(info["reason"]))
                if "structure" in info:
                    reason_parts.append(f"structure:{info['structure']}")
                if "volatility" in info:
                    reason_parts.append(f"vol:{info['volatility']}")
                if not reason_parts:
                    reason_parts.append(f"bias {score:.0f}")
            else:
                # object
                score = float(getattr(info, "bias_score", getattr(info, "score", 0)))
                reason_parts.append(getattr(info, "reason", f"bias {score:.0f}"))

            # determine state
            # ready if score magnitude > 50 or explicitly marked
            state = "ready" if abs(score) > 50 else "forming"
            # allow override
            if isinstance(info, dict) and "state" in info:
                state = info["state"]

            reason = "; ".join(reason_parts) if reason_parts else f"score {score:.1f}"

            opportunities.append(Opportunity(symbol=sym, state=state, score=float(score), reason=reason))

        # rank by score descending (higher score = better opportunity)
        # For bearish opportunities, we rank by absolute score? Spec says probability × EV, so higher is better.
        # We'll sort by score descending, but also consider absolute for ranking? Use score descending.
        opportunities.sort(key=lambda o: o.score, reverse=True)

        return opportunities
