"""
Currency Strength — decomposes symbol returns into currency components
"""

from __future__ import annotations

import numpy as np


class CurrencyStrength:
    def compute(self, symbol_returns: dict[str, np.ndarray]) -> dict[str, float]:
        """
        Decomposes symbol returns into currency components.
        Symbol format: EURUSD, GBPJPY, XAUUSD etc. First 3 = base, last 3 = quote.
        Returns strength score (-100 to +100) per currency.
        """
        # collect currencies
        currencies = set()
        parsed = {}
        for sym, arr in symbol_returns.items():
            arr = np.asarray(arr, dtype=float)
            # use mean of last window or last value
            # remove NaN
            arr = arr[~np.isnan(arr)]
            if len(arr) == 0:
                val = 0.0
            else:
                # use mean of last 20 or last value
                window = arr[-20:] if len(arr) >= 20 else arr
                val = float(np.mean(window))
            # parse currencies
            sym_clean = sym.replace("/", "").replace("-", "").upper()
            if len(sym_clean) >= 6:
                base = sym_clean[:3]
                quote = sym_clean[3:6]
                # handle XAU, XAG etc. treat as currency
                parsed[sym] = (base, quote, val)
                currencies.add(base)
                currencies.add(quote)
            else:
                # fallback: treat whole as currency
                currencies.add(sym_clean)
                parsed[sym] = (sym_clean, "", val)

        # accumulate
        scores: dict[str, float] = {c: 0.0 for c in currencies}
        counts: dict[str, int] = {c: 0 for c in currencies}

        for sym, (base, quote, val) in parsed.items():
            if base:
                scores[base] += val
                counts[base] += 1
            if quote:
                scores[quote] -= val
                counts[quote] += 1

        # average
        for c in scores:
            if counts[c] > 0:
                scores[c] /= counts[c]

        # normalize to -100..+100
        if scores:
            max_abs = max(abs(v) for v in scores.values())
            if max_abs > 0:
                for c in scores:
                    scores[c] = float(np.clip(scores[c] / max_abs * 100, -100, 100))
            else:
                for c in scores:
                    scores[c] = 0.0

        return scores
