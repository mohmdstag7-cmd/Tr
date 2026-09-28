"""
Vectorized indicators using numpy/pandas.
All functions take numpy arrays, return numpy arrays. No look-ahead bias.
"""

from __future__ import annotations

import numpy as np


def ema(series, period: int) -> np.ndarray:
    """Exponential Moving Average. No look-ahead. First value = series[0]."""
    series = np.asarray(series, dtype=float)
    if series.size == 0:
        return np.array([], dtype=float)
    if period <= 1:
        return series.copy()
    alpha = 2.0 / (period + 1)
    out = np.empty_like(series, dtype=float)
    out[0] = series[0]
    for i in range(1, len(series)):
        out[i] = alpha * series[i] + (1 - alpha) * out[i - 1]
    return out


def rsi(series, period: int = 14) -> np.ndarray:
    """Wilder's RSI. Returns NaN for first `period` bars."""
    series = np.asarray(series, dtype=float)
    n = len(series)
    out = np.full(n, np.nan, dtype=float)
    if n <= period:
        return out
    deltas = np.diff(series)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    avg_gain = np.empty(n, dtype=float)
    avg_loss = np.empty(n, dtype=float)
    avg_gain[:] = np.nan
    avg_loss[:] = np.nan

    # initial Wilder average
    avg_gain[period] = np.mean(gains[:period])
    avg_loss[period] = np.mean(losses[:period])

    for i in range(period + 1, n):
        avg_gain[i] = (avg_gain[i - 1] * (period - 1) + gains[i - 1]) / period
        avg_loss[i] = (avg_loss[i - 1] * (period - 1) + losses[i - 1]) / period

    for i in range(period, n):
        if avg_loss[i] == 0:
            out[i] = 100.0 if avg_gain[i] != 0 else 50.0
        else:
            rs = avg_gain[i] / avg_loss[i]
            out[i] = 100.0 - (100.0 / (1.0 + rs))
    return out


def atr(high, low, close, period: int = 14) -> np.ndarray:
    """Average True Range with Wilder smoothing."""
    high = np.asarray(high, dtype=float)
    low = np.asarray(low, dtype=float)
    close = np.asarray(close, dtype=float)
    n = len(close)
    if n == 0:
        return np.array([], dtype=float)
    tr = np.empty(n, dtype=float)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        tr[i] = max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1]),
        )
    out = np.full(n, np.nan, dtype=float)
    if n >= period:
        out[period - 1] = np.mean(tr[:period])
        for i in range(period, n):
            out[i] = (out[i - 1] * (period - 1) + tr[i]) / period
    return out


def adx(high, low, close, period: int = 14) -> np.ndarray:
    """Average Directional Index (Wilder). Returns NaN for first 2*period bars."""
    high = np.asarray(high, dtype=float)
    low = np.asarray(low, dtype=float)
    close = np.asarray(close, dtype=float)
    n = len(close)
    out = np.full(n, np.nan, dtype=float)
    if n <= 2 * period:
        return out

    tr = np.empty(n, dtype=float)
    plus_dm = np.empty(n, dtype=float)
    minus_dm = np.empty(n, dtype=float)
    tr[0] = high[0] - low[0]
    plus_dm[0] = 0.0
    minus_dm[0] = 0.0
    for i in range(1, n):
        tr[i] = max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1]),
        )
        up_move = high[i] - high[i - 1]
        down_move = low[i - 1] - low[i]
        plus_dm[i] = up_move if (up_move > down_move and up_move > 0) else 0.0
        minus_dm[i] = down_move if (down_move > up_move and down_move > 0) else 0.0

    # Wilder smoothing
    atr_s = np.full(n, np.nan, dtype=float)
    plus_s = np.full(n, np.nan, dtype=float)
    minus_s = np.full(n, np.nan, dtype=float)

    atr_s[period] = np.sum(tr[1 : period + 1])
    plus_s[period] = np.sum(plus_dm[1 : period + 1])
    minus_s[period] = np.sum(minus_dm[1 : period + 1])

    for i in range(period + 1, n):
        atr_s[i] = atr_s[i - 1] - atr_s[i - 1] / period + tr[i]
        plus_s[i] = plus_s[i - 1] - plus_s[i - 1] / period + plus_dm[i]
        minus_s[i] = minus_s[i - 1] - minus_s[i - 1] / period + minus_dm[i]

    plus_di = 100.0 * plus_s / atr_s
    minus_di = 100.0 * minus_s / atr_s

    dx = np.full(n, np.nan, dtype=float)
    denom = plus_di + minus_di
    valid = denom != 0
    dx[valid] = 100.0 * np.abs(plus_di[valid] - minus_di[valid]) / denom[valid]
    dx[~valid] = 0.0

    # ADX is Wilder-smoothed DX
    # first ADX at 2*period
    if n > 2 * period:
        # average of DX over period
        start = period + 1
        end = 2 * period + 1
        out[2 * period - 1] = np.nanmean(dx[start:end])
        for i in range(2 * period, n):
            if np.isnan(out[i - 1]):
                out[i] = dx[i]
            else:
                out[i] = (out[i - 1] * (period - 1) + dx[i]) / period
    return out


def bollinger_bands(close, period: int = 20, std: float = 2) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Returns (middle, upper, lower) bands."""
    close = np.asarray(close, dtype=float)
    n = len(close)
    middle = np.full(n, np.nan, dtype=float)
    upper = np.full(n, np.nan, dtype=float)
    lower = np.full(n, np.nan, dtype=float)
    if n < period:
        return middle, upper, lower
    for i in range(period - 1, n):
        window = close[i - period + 1 : i + 1]
        m = np.mean(window)
        s = np.std(window, ddof=0)
        middle[i] = m
        upper[i] = m + std * s
        lower[i] = m - std * s
    return middle, upper, lower


def atr_percentile(atr_series, lookback: int = 100) -> float:
    """Percentile rank (0-100) of last ATR value within lookback window."""
    atr_series = np.asarray(atr_series, dtype=float)
    # remove NaN
    atr_series = atr_series[~np.isnan(atr_series)]
    if atr_series.size == 0:
        return 50.0
    window = atr_series[-lookback:] if len(atr_series) > lookback else atr_series
    last = window[-1]
    # percentile: proportion <= last
    count = np.sum(window <= last)
    pct = (count / len(window)) * 100.0
    return float(pct)


def average_daily_range(high, low, period: int = 20) -> float:
    """Mean of daily ranges over period."""
    high = np.asarray(high, dtype=float)
    low = np.asarray(low, dtype=float)
    if high.size == 0:
        return 0.0
    ranges = high - low
    if len(ranges) < period:
        return float(np.mean(ranges))
    return float(np.mean(ranges[-period:]))
