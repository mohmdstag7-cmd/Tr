"""MT5 exception hierarchy."""

from __future__ import annotations


class MT5Error(RuntimeError):
    """Base MT5 error."""

    def __init__(
        self,
        message: str,
        *,
        retcode: int | None = None,
        last_error: str | None = None,
    ) -> None:
        super().__init__(message)
        self.retcode = retcode
        self.message = message
        self.last_error = last_error


class MT5ConnectionError(MT5Error):
    """Connection-level failure."""


class MT5NotInitializedError(MT5Error):
    """MT5 not initialized."""


class MT5TerminalNotFoundError(MT5Error):
    """Terminal executable not found."""


class MT5LoginError(MT5Error):
    """Authentication failure."""


class MT5AlgoTradingDisabledError(MT5Error):
    """Algo trading disabled in terminal."""


class MT5SymbolError(MT5Error):
    """Symbol-related error."""


class MT5TimeoutError(MT5Error):
    """MT5 call timed out."""


class MT5RetcodeError(MT5Error):
    """Trade request returned non-retryable retcode."""
