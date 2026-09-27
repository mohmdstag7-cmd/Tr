"""MT5 package — re-exports for public API."""

from __future__ import annotations

from app.mt5.connection import MT5Connection, detect_account_type, detect_broker_utc_offset
from app.mt5.exceptions import MT5ConnectionError
from app.mt5.gateway import MT5Command, MT5CommandResult, MT5ConnectionState, MT5Gateway
from app.mt5.types import account_info_summary, terminal_info_summary

__all__ = [
    "MT5Gateway",
    "MT5Connection",
    "MT5ConnectionError",
    "MT5ConnectionState",
    "MT5Command",
    "MT5CommandResult",
    "terminal_info_summary",
    "account_info_summary",
    "detect_account_type",
    "detect_broker_utc_offset",
]
