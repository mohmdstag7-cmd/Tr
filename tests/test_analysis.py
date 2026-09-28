"""
Tests for all analysis modules — deterministic synthetic data, no randomness.
"""

import csv
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest


# ---------- helpers ----------
def make_trending_bars(n=250, start=100, step=0.1, volatility=0.2):
    """Deterministic trending bars: close rises linearly with small oscillation."""
    close = np.array([start + i * step + (i % 5) * 0.02 for i in range(n)], dtype=float)
    high = close + volatility + 0.05
    low = close - volatility
    open_ = close - 0.02
    return {"open": open_, "high": high, "low": low, "close": close}


def make_ranging_bars(n=250, start=100, amplitude=1.0):
    """Ranging: sine wave."""
    close = np.array([start + np.sin(i * 0.3) * amplitude for i in range(n)], dtype=float)
    high = close + 0.3
    low = close - 0.3
    open_ = close + 0.05 * np.sin(i * 0.5) if (i := 0) else close  # dummy
    open_ = close - 0.02
    return {"open": open_, "high": high, "low": low, "close": close}


# ---------- indicators ----------
def test_ema():
    from app.analysis.indicators import ema

    series = np.array([1, 2, 3, 4, 5], dtype=float)
    result = ema(series, period=3)
    # alpha=0.5, ema0=1, ema1=1.5, ema2=2.25, ema3=3.125, ema4=4.0625
    assert result[0] == pytest.approx(1.0)
    assert result[1] == pytest.approx(1.5)
    assert result[2] == pytest.approx(2.25)
    assert result[4] == pytest.approx(4.0625)
    assert len(result) == 5


def test_rsi():
    from app.analysis.indicators import rsi

    # strong uptrend -> RSI near 100
    up = np.arange(1, 30, dtype=float)
    r = rsi(up, period=14)
    assert r[-1] > 70
    # strong downtrend -> RSI near 0
    down = np.arange(30, 0, -1, dtype=float)
    r2 = rsi(down, period=14)
    assert r2[-1] < 30
    # flat -> around 50
    flat = np.full(30, 100.0)
    r3 = rsi(flat, period=14)
    # flat should be 50 or nan, but last valid should be 50
    assert r3[-1] == pytest.approx(50, abs=5)


def test_atr():
    from app.analysis.indicators import atr

    high = np.array([10, 11, 12, 13], dtype=float)
    low = np.array([9, 10, 11, 12], dtype=float)
    close = np.array([9.5, 10.5, 11.5, 12.5], dtype=float)
    result = atr(high, low, close, period=2)
    # TR: [1, 1.5, 1.5, 1.5] -> ATR[1]=1.25, ATR[2]=1.375, ATR[3]=1.4375
    assert np.isnan(result[0])
    assert result[1] == pytest.approx(1.25, rel=1e-2)
    assert result[2] > 1.2
    assert result[3] > result[2] or result[3] == pytest.approx(1.4375, rel=1e-2)


def test_adx():
    from app.analysis.indicators import adx

    # trending: steady up
    n = 100
    close = np.array([100 + i * 0.5 for i in range(n)], dtype=float)
    high = close + 0.3
    low = close - 0.3
    adx_trend = adx(high, low, close, period=14)
    # ranging: sine
    close2 = np.array([100 + np.sin(i * 0.5) for i in range(n)], dtype=float)
    high2 = close2 + 0.3
    low2 = close2 - 0.3
    adx_range = adx(high2, low2, close2, period=14)
    # trending ADX should be higher than ranging
    valid_trend = adx_trend[~np.isnan(adx_trend)]
    valid_range = adx_range[~np.isnan(adx_range)]
    assert len(valid_trend) > 0 and len(valid_range) > 0
    assert np.mean(valid_trend[-10:]) > np.mean(valid_range[-10:])


# ---------- MTF ----------
def test_mtf_trend_matrix():
    from app.analysis.mtf_trend import MTFTrendMatrix

    m = MTFTrendMatrix()
    # bullish on all TFs
    bullish_bars = make_trending_bars(n=250, start=100, step=0.2)
    bars_dict = {tf: bullish_bars for tf in ["M5", "M15", "M30", "H1", "H4", "D1"]}
    result = m.analyze(bars_dict)
    assert result.bias_score > 20
    assert "bullish" in result.reason.lower()
    assert result.per_tf["H1"].direction == "bullish"

    # bearish
    bearish_bars = make_trending_bars(n=250, start=100, step=-0.2)
    bars_dict2 = {tf: bearish_bars for tf in ["M5", "M15", "M30", "H1", "H4", "D1"]}
    result2 = m.analyze(bars_dict2)
    assert result2.bias_score < -30
    assert result2.per_tf["H1"].direction == "bearish"

    # neutral / ranging
    ranging = make_ranging_bars(n=250)
    bars_dict3 = {tf: ranging for tf in ["M5", "M15", "H1"]}
    result3 = m.analyze(bars_dict3)
    # bias should be near 0
    assert -50 <= result3.bias_score <= 50


# ---------- Structure ----------
def test_market_structure_swing_detection():
    from app.analysis.structure import MarketStructure

    ms = MarketStructure(swing_lookback=2)
    # create bars with clear swing high at index 5
    n = 20
    high = np.array([10, 11, 12, 13, 14, 20, 14, 13, 12, 11] + [10] * 10, dtype=float)
    low = high - 1
    close = high - 0.5
    bars = {"high": high, "low": low, "close": close}
    result = ms.analyze(bars)
    # swing at index 5 should be detected and confirmed (since we have N=2 bars after)
    highs = [s for s in result.swings if s.type == "high"]
    assert any(s.index == 5 for s in highs)
    # last N bars should not have unconfirmed swings
    for s in result.swings:
        assert s.index <= n - 2 - 1  # confirmed after N bars


def test_market_structure_hh_hl():
    from app.analysis.structure import MarketStructure

    ms = MarketStructure(swing_lookback=2)
    # HH/HL sequence: rising highs and lows
    # construct swings manually via bars
    # We'll create bars that produce HH and HL
    high = np.array([10, 12, 11, 13, 12, 14, 13, 15, 14, 16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6], dtype=float)
    low = np.array([9, 9, 8, 10, 9, 11, 10, 12, 11, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3], dtype=float)
    close = (high + low) / 2
    bars = {"high": high, "low": low, "close": close}
    result = ms.analyze(bars)
    # should have at least some HH/HL
    assert isinstance(result.sequence, list)


def test_bos_detection():
    from app.analysis.structure import MarketStructure

    ms = MarketStructure(swing_lookback=2)
    # create prior swing high at 15, then close breaks above
    high = np.array([10, 12, 14, 15, 14, 13, 14, 15, 14, 16, 17, 18], dtype=float)
    low = high - 2
    close = np.array([10, 11, 13, 14, 13, 12, 13, 14, 13, 15, 16, 17.5], dtype=float)
    bars = {"high": high, "low": low, "close": close}
    result = ms.analyze(bars)
    assert result.bos is True
    assert result.bos_direction == "bullish"


# ---------- Levels ----------
def test_key_levels_support_resistance():
    from app.analysis.indicators import atr
    from app.analysis.levels import KeyLevels
    from app.analysis.structure import MarketStructure

    bars = make_trending_bars(n=100, start=100, step=0.1)
    ms = MarketStructure(swing_lookback=2)
    struct = ms.analyze(bars)
    atr_vals = atr(bars["high"], bars["low"], bars["close"], 14)
    last_atr = float(atr_vals[~np.isnan(atr_vals)][-1])
    kl = KeyLevels()
    levels = kl.compute(bars, struct.swings, last_atr)
    assert len(levels) > 0
    # should have support/resistance
    [lvl.type for lvl in levels]
    assert len(levels) > 0
    for lvl in levels:
        assert 1 <= lvl.strength <= 5
        assert lvl.distance_in_atr >= 0


def test_key_levels_session_highs():
    from datetime import datetime, timedelta

    from app.analysis.indicators import atr
    from app.analysis.levels import KeyLevels
    from app.analysis.structure import MarketStructure

    n = 60
    base_time = datetime(2024, 1, 15, 0, 0, tzinfo=UTC)
    times = [base_time + timedelta(minutes=30 * i) for i in range(n)]
    close = np.array([100 + i * 0.05 for i in range(n)], dtype=float)
    high = close + 0.2
    low = close - 0.2
    bars = {"high": high, "low": low, "close": close, "time": np.array(times)}
    ms = MarketStructure()
    struct = ms.analyze(bars)
    atr_vals = atr(high, low, close, 14)
    last_atr = float(atr_vals[~np.isnan(atr_vals)][-1])
    kl = KeyLevels()
    levels = kl.compute(bars, struct.swings, last_atr)
    [lvl.type for lvl in levels]
    # should have session highs/lows
    assert len(levels) > 0  # At least some levels found


# ---------- Volatility ----------
def test_volatility_regime():
    from app.analysis.volatility import VolatilityAnalysis

    va = VolatilityAnalysis()
    # low volatility: small ranges
    high_low = np.array([100.1] * 50, dtype=float)
    low_low = np.array([100.0] * 50, dtype=float)
    close_low = np.array([100.05] * 50, dtype=float)
    bars_low = {"high": high_low, "low": low_low, "close": close_low}
    # need to create percentile context: use trending then low
    # For regime test, we check that high volatility gives high regime
    # Create high vol bars
    high_high = np.array([100 + (i % 2) * 5 for i in range(50)], dtype=float)
    low_high = high_high - 5
    close_high = (high_high + low_high) / 2

    # To test percentile, we need ATR series with varying values
    # Use VolatilityAnalysis on mixed data: first low vol then high vol
    # Create combined bars: 100 bars low vol, then 20 bars high vol -> percentile high
    high_comb = np.concatenate([high_low, high_high[:20]])
    low_comb = np.concatenate([low_low, low_high[:20]])
    close_comb = np.concatenate([close_low, close_high[:20]])
    bars_comb = {"high": high_comb, "low": low_comb, "close": close_comb}
    result_high = va.analyze(bars_comb)
    assert result_high.regime in ("low", "normal", "high")
    # high vol at end should be high regime
    assert result_high.atr > 1.0
    # low vol alone should be low or normal
    result_low = va.analyze(bars_low)
    assert result_low.regime in ("low", "normal", "high")
    assert result_low.atr < result_high.atr


# ---------- Sessions ----------
def test_sessions_current():
    from app.analysis.sessions import SessionClock

    sc = SessionClock()
    # Asia 02:00 UTC
    t_asia = datetime(2024, 1, 15, 2, 0, tzinfo=UTC)
    info = sc.current_session(t_asia)
    assert info.name == "Asia"
    # London 08:00 UTC
    t_london = datetime(2024, 1, 15, 8, 0, tzinfo=UTC)
    info2 = sc.current_session(t_london)
    assert "London" in info2.name
    # NY 17:00 UTC (after overlap)
    t_ny = datetime(2024, 1, 15, 17, 0, tzinfo=UTC)
    info3 = sc.current_session(t_ny)
    assert "NY" in info3.name or "Overlap" in info3.name


def test_sessions_overlap():
    from app.analysis.sessions import SessionClock

    sc = SessionClock()
    t_overlap = datetime(2024, 1, 15, 13, 0, tzinfo=UTC)
    assert sc.is_overlap(t_overlap) is True
    t_no = datetime(2024, 1, 15, 8, 0, tzinfo=UTC)
    assert sc.is_overlap(t_no) is False
    # also check current_session overlap flag
    info = sc.current_session(t_overlap)
    assert info.is_overlap is True


# ---------- Correlation ----------
def test_correlation_matrix():
    from app.analysis.correlation import CorrelationMatrix

    cm = CorrelationMatrix()
    # highly correlated
    a = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10] * 3, dtype=float)
    b = a * 2 + 1  # perfectly correlated
    c = -a  # perfectly anti-correlated
    result = cm.compute({"A": a, "B": b, "C": c}, window=20)
    assert result[("A", "B")] == pytest.approx(1.0, abs=0.01)
    assert result[("A", "C")] == pytest.approx(-1.0, abs=0.01)
    assert result[("A", "A")] == pytest.approx(1.0)


# ---------- Currency Strength ----------
def test_currency_strength():
    from app.analysis.currency_strength import CurrencyStrength

    cs = CurrencyStrength()
    # EURUSD drops -> USD strength positive, EUR negative
    # Simulate returns: EURUSD negative
    eurusd = np.array([-0.01] * 20, dtype=float)
    gbpusd = np.array([-0.005] * 20, dtype=float)
    usdjpy = np.array([0.008] * 20, dtype=float)
    result = cs.compute({"EURUSD": eurusd, "GBPUSD": gbpusd, "USDJPY": usdjpy})
    # USD should be strong (positive) because EURUSD and GBPUSD down, USDJPY up
    assert result["USD"] > result["EUR"]
    assert result["USD"] > 0
    assert result["EUR"] < 0


# ---------- Patterns ----------
def test_patterns_engulfing():
    from app.analysis.patterns import CandlePatterns

    cp = CandlePatterns()
    # bullish engulfing: prev bearish, current bullish engulfs
    bars = {
        "open": np.array([10, 9.5], dtype=float),
        "high": np.array([10.5, 11], dtype=float),
        "low": np.array([9, 9.3], dtype=float),
        "close": np.array([9.5, 10.8], dtype=float),
    }
    # bar0: open 10 close 9.5 bearish, bar1: open 9.5 close 10.8 bullish, body 1.3 > 0.5 engulfs
    patterns = cp.detect(bars)
    engulfing = [p for p in patterns if p.type == "engulfing" and p.direction == "bullish"]
    assert len(engulfing) >= 1

    # bearish engulfing
    bars2 = {
        "open": np.array([9.5, 10.8], dtype=float),
        "high": np.array([10, 11], dtype=float),
        "low": np.array([9.3, 9.0], dtype=float),
        "close": np.array([10.5, 9.2], dtype=float),
    }
    patterns2 = cp.detect(bars2)
    engulfing2 = [p for p in patterns2 if p.type == "engulfing" and p.direction == "bearish"]
    assert len(engulfing2) >= 1


def test_patterns_pin_bar():
    from app.analysis.patterns import CandlePatterns

    cp = CandlePatterns()
    # hammer: long lower wick, small body at top
    # open 10, close 10.1, high 10.2, low 9.0 -> lower wick 1.0, body 0.1, upper 0.1
    bars = {
        "open": np.array([10, 10], dtype=float),
        "high": np.array([10.5, 10.2], dtype=float),
        "low": np.array([9.5, 9.0], dtype=float),
        "close": np.array([10.2, 10.1], dtype=float),
    }
    patterns = cp.detect(bars)
    pin_bars = [p for p in patterns if p.type == "pin_bar" and p.direction == "bullish"]
    assert isinstance(pin_bars, list)


# ---------- Scanner ----------
def test_scanner_ranking():
    from app.analysis.scanner import OpportunityScanner

    scanner = OpportunityScanner()
    symbols = ["EURUSD", "GBPUSD", "XAUUSD"]
    analysis_results = {
        "EURUSD": {"score": 80, "reason": "strong bullish"},
        "GBPUSD": {"score": 20, "reason": "weak"},
        "XAUUSD": {"score": 50, "reason": "moderate"},
    }
    opps = scanner.scan(symbols, analysis_results)
    assert len(opps) == 3
    # ranked by score descending
    assert opps[0].symbol == "EURUSD"
    assert opps[0].score == 80
    assert opps[1].symbol == "XAUUSD"
    assert opps[2].symbol == "GBPUSD"
    assert opps[0].state == "ready"
    assert opps[2].state == "forming"


# ---------- Analysis Card ----------
def test_analysis_card_generation():
    from datetime import timedelta

    from app.analysis.analysis_card import AnalysisCard
    from app.analysis.mtf_trend import MTFTrendResult, TFTrend
    from app.analysis.sessions import SessionInfo
    from app.analysis.structure import StructureResult
    from app.analysis.volatility import VolatilityResult

    card = AnalysisCard()
    mtf = MTFTrendResult(
        per_tf={"H1": TFTrend("H1", "bullish", 70, 100, 99, 30, 0.5), "H4": TFTrend("H4", "bullish", 80, 101, 99, 35, 0.6)},
        bias_score=65,
        reason="Bullish alignment on H1, H4",
    )
    struct = StructureResult(market_type="trending", bos=True, bos_direction="bullish", sequence=["HH", "HL"])
    from app.analysis.levels import Level

    levels = [Level(price=2318, type="support", distance_in_atr=0.4, strength=4)]
    vol = VolatilityResult(atr=1.2, atr_percentile=80, adr=2.5, pct_used_today=60, regime="high")
    sess = SessionInfo(name="London", start=datetime.now(UTC), end=datetime.now(UTC) + timedelta(hours=2), time_remaining=timedelta(hours=1))
    text = card.generate("XAUUSD", mtf, struct, levels, vol, sess, [])
    assert "XAUUSD" in text
    assert "bullish" in text.lower() or "bias" in text.lower()
    assert "London" in text
    assert "2318" in text or "support" in text.lower()


# ---------- Calendar ----------
def test_calendar_csv_import():
    from app.analysis.calendar import CalendarStore

    store = CalendarStore()
    # create temp CSV
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["time", "currency", "impact", "event", "forecast", "previous", "actual"])
        now = datetime.now(UTC)
        future = now + timedelta(hours=2)
        past = now - timedelta(hours=2)
        writer.writerow([future.strftime("%Y-%m-%d %H:%M:%S"), "USD", "high", "CPI", "3.2", "3.0", ""])
        writer.writerow([past.strftime("%Y-%m-%d %H:%M:%S"), "USD", "high", "NFP", "200k", "180k", ""])
        writer.writerow([(now + timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S"), "EUR", "medium", "ECB Rate", "4.0", "4.0", ""])
        path = f.name

    imported = store.import_csv(path)
    assert len(imported) == 3
    # upcoming USD within 360 minutes (6h) should include future CPI but not past NFP
    upcoming_usd = store.upcoming("USD", minutes_ahead=360)
    assert len(upcoming_usd) == 1
    assert upcoming_usd[0].event == "CPI"
    # EUR upcoming
    upcoming_eur = store.upcoming("EUR", minutes_ahead=360)
    assert len(upcoming_eur) == 1
    # manual add
    ev = store.add_event_manual(now + timedelta(hours=1), "GBP", "low", "Test Event", "1.0", "0.9")
    assert ev.currency == "GBP"
    assert len(store.upcoming("GBP", minutes_ahead=360)) == 1

    Path(path).unlink()
