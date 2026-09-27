"""MT5 Trading Workstation package."""

from __future__ import annotations

from typing import Literal

MT5ConnectionState = Literal["disconnected", "connecting", "connected", "reconnecting", "error"]

__all__ = ["MT5ConnectionState"]
