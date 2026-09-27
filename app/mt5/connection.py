"""Low-level MT5 connection wrapper — only called inside MT5Gateway thread."""

from __future__ import annotations

import datetime as dt
import sys
from typing import Any, Literal

from app.mt5.exceptions import (
    MT5ConnectionError,
    MT5LoginError,
    MT5TerminalNotFoundError,
)
from app.mt5.types import AccountInfo, TerminalInfo
from app.observability import get_logger

logger = get_logger("mt5.connection")


def _get_mt5() -> Any | None:
    """Resolve the MetaTrader5 module lazily, so monkeypatching sys.modules works.

    Tests inject a FakeMT5 instance into sys.modules['MetaTrader5']; we look it
    up here at call time rather than capturing it at import time.
    """
    return sys.modules.get("MetaTrader5")


def _require_mt5() -> Any:
    """Return the MetaTrader5 module or raise if not importable."""
    m = _get_mt5()
    if m is None:
        raise MT5TerminalNotFoundError("MetaTrader5 package not installed")
    return m


def detect_account_type(login: int, server: str = "") -> Literal["demo", "real", "contest"]:
    """Infer account type per MT5 convention.

    - server name contains 'contest' -> contest
    - login < 100000 -> demo
    - otherwise -> real
    """
    if "contest" in server.lower():
        return "contest"
    if login < 100000:
        return "demo"
    return "real"


def detect_broker_utc_offset() -> int:
    """Compare EURUSD tick time to UTC now and return offset in seconds."""
    if _get_mt5() is None:
        logger.warning("MetaTrader5 not available — cannot detect broker offset")
        return 0
    try:
        tick = _require_mt5().symbol_info_tick("EURUSD")
        if tick is None:
            # try any symbol
            syms = _require_mt5().symbols_get()
            if syms:
                tick = _require_mt5().symbol_info_tick(syms[0].name)
        if tick is None:
            return 0
        broker_time = dt.datetime.fromtimestamp(int(tick.time), tz=dt.UTC)
        now_utc = dt.datetime.now(tz=dt.UTC)
        # tick.time is broker server time as epoch; difference to UTC is offset
        # Actually mt5 returns broker time as seconds; we compare to UTC
        offset = int((broker_time - now_utc).total_seconds())
        # round to nearest hour (broker offsets are whole hours, sometimes 30min)
        # keep raw seconds but log
        logger.info(f"Broker UTC offset detected: {offset}s ({offset/3600:.1f}h)")
        return offset
    except Exception as exc:  # pragma: no cover
        logger.warning(f"Failed to detect broker offset: {exc}")
        return 0


class MT5Connection:
    """Direct MT5 calls — must only be used inside the gateway thread."""

    def __init__(self) -> None:
        self._broker_offset: int = 0

    @property
    def broker_offset(self) -> int:
        return self._broker_offset

    def initialize(
        self,
        path: str | None,
        login: int,
        password: str,
        server: str,
        timeout: int = 60000,
    ) -> bool:
        if _get_mt5() is None:
            raise MT5TerminalNotFoundError("MetaTrader5 package not installed")
        # friendly error mapping
        for attempt in range(3):
            try:
                ok = _require_mt5().initialize(
                    path=path or "", login=login, password=password, server=server, timeout=timeout
                )
            except Exception as exc:  # pragma: no cover
                msg = str(exc).lower()
                if "ipc timeout" in msg or "ipc initialize failed" in msg:
                    raise MT5ConnectionError(
                        "Terminal not ready, or running as a different user/privilege level",
                        last_error=msg,
                    ) from exc
                raise
            if ok:
                self._broker_offset = detect_broker_utc_offset()
                return True
            code, msg = _require_mt5().last_error()
            low = msg.lower() if isinstance(msg, str) else ""
            if "investor" in low:
                logger.warning("Investor password detected — Analysis-only mode")
                self._broker_offset = detect_broker_utc_offset()
                return True
            if "invalid account" in low or "wrong password" in low or "authorization failed" in low or code == -6:
                raise MT5LoginError(f"Login failed: {msg}", last_error=msg)
            if "server" in low and ("not found" in low or "wrong" in low):
                raise MT5ConnectionError(f"Check the server name: {msg}", last_error=msg)
            if "not found" in low or "terminal" in low:
                raise MT5TerminalNotFoundError(msg, last_error=msg)
            if "trade context is busy" in low:
                if attempt < 2:
                    import time

                    time.sleep(0.5)
                    continue
                raise MT5ConnectionError("Trade context busy", last_error=msg)
            if "ipc timeout" in low or "ipc initialize failed" in low:
                raise MT5ConnectionError(
                    "Terminal not ready, or running as a different user/privilege level",
                    last_error=msg,
                )
            # generic
            raise MT5ConnectionError(f"Initialize failed: {msg} (code {code})", last_error=msg)
        return False

    def shutdown(self) -> None:
        if _get_mt5() is None:
            return
        try:
            _require_mt5().shutdown()
        except Exception:  # pragma: no cover
            pass

    def is_connected(self) -> bool:
        if _get_mt5() is None:
            return False
        try:
            info = _require_mt5().terminal_info()
            return bool(info and getattr(info, "connected", False))
        except Exception:
            return False

    def terminal_info(self) -> TerminalInfo | None:
        if _get_mt5() is None:
            return None
        try:
            raw = _require_mt5().terminal_info()
            if raw is None:
                return None
            return TerminalInfo.from_mt5(raw, self._broker_offset)
        except Exception:
            return None

    def account_info(self) -> AccountInfo | None:
        if _get_mt5() is None:
            return None
        try:
            raw = _require_mt5().account_info()
            if raw is None:
                return None
            return AccountInfo.from_mt5(raw, self._broker_offset)
        except Exception:
            return None

    def last_error(self) -> tuple[int, str]:
        if _get_mt5() is None:
            return (-1, "MetaTrader5 not installed")
        try:
            return _require_mt5().last_error()  # type: ignore[no-any-return]
        except Exception:
            return (-1, "unknown")
