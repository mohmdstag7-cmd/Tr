"""Symbol mapping and caching."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.observability import get_logger

if TYPE_CHECKING:
    from app.mt5.gateway import MT5Gateway
    from app.mt5.types import SymbolInfo

logger = get_logger("mt5.symbols")


def map_symbol(user_symbol: str, available_symbols: list[str]) -> str | None:
    """Map user symbol to broker symbol handling suffixes.

    e.g. user 'EURUSD' matches 'EURUSD.m' or 'EURUSDm'.
    Exact match preferred, then prefix match.
    """
    if user_symbol in available_symbols:
        return user_symbol
    # prefix match: broker symbol starts with user symbol
    candidates = [s for s in available_symbols if s.startswith(user_symbol)]
    if candidates:
        # prefer shortest (least suffix)
        candidates.sort(key=len)
        return candidates[0]
    # case-insensitive fallback
    lower = user_symbol.lower()
    for s in available_symbols:
        if s.lower().startswith(lower):
            return s
    return None


def ensure_in_market_watch(gateway: MT5Gateway, symbol: str) -> bool:
    """Ensure symbol is visible in Market Watch."""
    try:
        fut = gateway.symbol_select(symbol, True)
        return bool(fut.result(timeout=5))
    except Exception as exc:
        logger.warning(f"symbol_select failed for {symbol}: {exc}")
        return False


class SymbolCache:
    """In-memory cache of SymbolInfo."""

    def __init__(self, gateway: MT5Gateway) -> None:
        self._gateway = gateway
        self._cache: dict[str, SymbolInfo] = {}

    def get(self, name: str) -> SymbolInfo | None:
        if name in self._cache:
            return self._cache[name]
        try:
            fut = self._gateway.symbol_info(name)
            info = fut.result(timeout=5)
            if info:
                self._cache[name] = info
            return info
        except Exception as exc:
            logger.warning(f"SymbolCache.get failed for {name}: {exc}")
            return None

    def refresh(self, name: str) -> SymbolInfo | None:
        self._cache.pop(name, None)
        return self.get(name)

    def clear(self) -> None:
        self._cache.clear()

    def bulk_load(self, names: list[str]) -> None:
        for n in names:
            self.get(n)
