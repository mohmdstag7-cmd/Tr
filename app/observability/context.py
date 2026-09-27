"""ContextVars for trace propagation."""

from __future__ import annotations

import contextlib
import uuid
from collections.abc import Generator
from contextvars import ContextVar
from typing import Any

_session_id: ContextVar[str | None] = ContextVar("_session_id", default=None)
_trace_id: ContextVar[str | None] = ContextVar("_trace_id", default=None)
_signal_id: ContextVar[str | None] = ContextVar("_signal_id", default=None)
_trade_id: ContextVar[str | None] = ContextVar("_trade_id", default=None)
_ticket: ContextVar[int | None] = ContextVar("_ticket", default=None)
_symbol: ContextVar[str | None] = ContextVar("_symbol", default=None)


def set_session_id(sid: str | None) -> None:
    _session_id.set(sid)


def get_session_id() -> str | None:
    return _session_id.get()


def new_session_id() -> str:
    return uuid.uuid4().hex


def set_trace_id(tid: str | None) -> None:
    _trace_id.set(tid)


def get_trace_id() -> str | None:
    return _trace_id.get()


def new_trace_id() -> str:
    return uuid.uuid4().hex


@contextlib.contextmanager
def bind_context(**kwargs: Any) -> Generator[None, None, None]:
    """Temporarily bind context vars. Restores on exit."""
    tokens: dict[str, Any] = {}
    for key, value in kwargs.items():
        if key == "session_id":
            tokens[key] = _session_id.set(value)
        elif key == "trace_id":
            tokens[key] = _trace_id.set(value)
        elif key == "signal_id":
            tokens[key] = _signal_id.set(value)
        elif key == "trade_id":
            tokens[key] = _trade_id.set(value)
        elif key == "ticket":
            tokens[key] = _ticket.set(value)
        elif key == "symbol":
            tokens[key] = _symbol.set(value)
        else:
            # Unknown keys are ignored but we keep API flexible
            continue
    try:
        yield
    finally:
        for key, token in tokens.items():
            if key == "session_id":
                _session_id.reset(token)
            elif key == "trace_id":
                _trace_id.reset(token)
            elif key == "signal_id":
                _signal_id.reset(token)
            elif key == "trade_id":
                _trade_id.reset(token)
            elif key == "ticket":
                _ticket.reset(token)
            elif key == "symbol":
                _symbol.reset(token)


def current_context() -> dict[str, Any]:
    """Snapshot of current context vars."""
    return {
        "session_id": _session_id.get(),
        "trace_id": _trace_id.get(),
        "signal_id": _signal_id.get(),
        "trade_id": _trade_id.get(),
        "ticket": _ticket.get(),
        "symbol": _symbol.get(),
    }
