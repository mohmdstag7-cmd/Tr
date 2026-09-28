"""
Market Data & Analysis package — Phase 5
Re-exports all public classes and functions per SPEC C3 + D2.
"""

from .analysis_card import AnalysisCard
from .calendar import CalendarEvent, CalendarStore
from .correlation import CorrelationMatrix
from .currency_strength import CurrencyStrength
from .indicators import (
    adx,
    atr,
    atr_percentile,
    average_daily_range,
    bollinger_bands,
    ema,
    rsi,
)
from .levels import KeyLevels, Level
from .mtf_trend import MTFTrendMatrix, MTFTrendResult, TFTrend
from .patterns import CandlePatterns, Pattern
from .scanner import Opportunity, OpportunityScanner
from .sessions import SessionClock, SessionInfo
from .structure import MarketStructure, StructureResult, Swing
from .volatility import VolatilityAnalysis, VolatilityResult

__all__ = [
    "ema",
    "rsi",
    "adx",
    "atr",
    "bollinger_bands",
    "atr_percentile",
    "average_daily_range",
    "MTFTrendMatrix",
    "MTFTrendResult",
    "TFTrend",
    "MarketStructure",
    "StructureResult",
    "Swing",
    "KeyLevels",
    "Level",
    "VolatilityAnalysis",
    "VolatilityResult",
    "SessionClock",
    "SessionInfo",
    "CorrelationMatrix",
    "CurrencyStrength",
    "CandlePatterns",
    "Pattern",
    "OpportunityScanner",
    "Opportunity",
    "AnalysisCard",
    "CalendarStore",
    "CalendarEvent",
]
