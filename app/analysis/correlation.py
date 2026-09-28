"""
Correlation Matrix
"""

from __future__ import annotations

import numpy as np


class CorrelationMatrix:
    def compute(self, returns_dict: dict[str, np.ndarray], window: int = 20) -> dict[tuple[str, str], float]:
        """
        Rolling correlation between all symbol pairs over `window` bars.
        Returns dict of (symbol_a, symbol_b) -> correlation coefficient.
        """
        symbols = list(returns_dict.keys())
        result: dict[tuple[str, str], float] = {}

        # prepare windowed arrays
        windowed = {}
        for sym, arr in returns_dict.items():
            arr = np.asarray(arr, dtype=float)
            # remove NaN
            arr = arr[~np.isnan(arr)]
            if len(arr) >= window:
                windowed[sym] = arr[-window:]
            elif len(arr) > 1:
                windowed[sym] = arr
            else:
                windowed[sym] = arr

        for i, a in enumerate(symbols):
            for b in symbols[i + 1 :]:
                arr_a = windowed.get(a, np.array([]))
                arr_b = windowed.get(b, np.array([]))
                # align lengths
                n = min(len(arr_a), len(arr_b))
                if n < 2:
                    corr = 0.0
                else:
                    a_w = arr_a[-n:]
                    b_w = arr_b[-n:]
                    # handle constant series
                    if np.std(a_w) == 0 or np.std(b_w) == 0:
                        corr = 0.0
                    else:
                        corr = float(np.corrcoef(a_w, b_w)[0, 1])
                        if np.isnan(corr):
                            corr = 0.0
                result[(a, b)] = corr
                result[(b, a)] = corr

        # self-correlation
        for s in symbols:
            result[(s, s)] = 1.0

        return result
