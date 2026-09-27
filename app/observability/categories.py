"""Log categories per SPEC Part E3."""

from __future__ import annotations

from typing import Literal

LOG_CATEGORIES: tuple[str, ...] = (
    "app",
    "mt5",
    "market_data",
    "analysis",
    "strategy",
    "ml",
    "risk",
    "execution",
    "position",
    "sync",
    "backtest",
    "ui",
    "notify",
    "llm",
    "audit",
    "perf",
    "update",
)

Category = Literal[
    "app",
    "mt5",
    "market_data",
    "analysis",
    "strategy",
    "ml",
    "risk",
    "execution",
    "position",
    "sync",
    "backtest",
    "ui",
    "notify",
    "llm",
    "audit",
    "perf",
    "update",
]


def is_valid_category(s: str) -> bool:
    """Return True if s is a known log category."""
    return s in LOG_CATEGORIES
