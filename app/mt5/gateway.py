"""Single-threaded MT5 gateway — owns all MetaTrader5 calls."""

from __future__ import annotations

import concurrent.futures
import datetime as dt
import queue
import threading
from dataclasses import dataclass, field
from typing import Any, Literal

from PySide6.QtCore import QObject, QThread, QTimer, Signal

from app.mt5.connection import MT5Connection, _get_mt5, _require_mt5
from app.mt5.exceptions import MT5TimeoutError
from app.mt5.types import AccountInfo, Bar, Deal, Order, PositionInfo, SymbolInfo, TerminalInfo, Tick
from app.observability import audit_log, get_logger

logger = get_logger("mt5.gateway")

MT5ConnectionState = Literal["disconnected", "connecting", "connected", "reconnecting", "error"]


@dataclass
class MT5Command:
    name: str
    args: tuple[Any, ...] = ()
    kwargs: dict[str, Any] = field(default_factory=dict)
    future: concurrent.futures.Future[Any] = field(default_factory=concurrent.futures.Future)
    timeout: float = 5.0


@dataclass
class MT5CommandResult:
    success: bool
    value: Any = None
    error: str | None = None


# timeframe string -> MT5 constant (fallback to int mapping)
_TF_MAP: dict[str, int] = {
    "M1": 1,
    "M5": 5,
    "M15": 15,
    "M30": 30,
    "H1": 16385,
    "H4": 16386,
    "D1": 16408,
    "W1": 32769,
    "MN1": 49152,
}


def _tf_to_mt5(tf: str) -> int:
    if _get_mt5() is not None:
        # try to resolve real constants
        mapping = {
            "M1": getattr(_require_mt5(), "TIMEFRAME_M1", 1),
            "M5": getattr(_require_mt5(), "TIMEFRAME_M5", 5),
            "M15": getattr(_require_mt5(), "TIMEFRAME_M15", 15),
            "M30": getattr(_require_mt5(), "TIMEFRAME_M30", 30),
            "H1": getattr(_require_mt5(), "TIMEFRAME_H1", 16385),
            "H4": getattr(_require_mt5(), "TIMEFRAME_H4", 16386),
            "D1": getattr(_require_mt5(), "TIMEFRAME_D1", 16408),
            "W1": getattr(_require_mt5(), "TIMEFRAME_W1", 32769),
            "MN1": getattr(_require_mt5(), "TIMEFRAME_MN1", 49152),
        }
        return mapping.get(tf, _TF_MAP.get(tf, 15))
    return _TF_MAP.get(tf, 15)


class _Worker(QObject):
    def __init__(self, q: queue.Queue[MT5Command], conn: MT5Connection) -> None:
        super().__init__()
        self._q = q
        self._conn = conn
        self._running = True

    def stop(self) -> None:
        self._running = False

    def run(self) -> None:
        while self._running:
            try:
                cmd: MT5Command = self._q.get(timeout=0.2)
            except queue.Empty:
                continue
            if cmd.future.cancelled():
                continue
            try:
                result = self._execute(cmd)
                if not cmd.future.done():
                    cmd.future.set_result(result)
            except Exception as exc:  # pragma: no cover
                if not cmd.future.done():
                    cmd.future.set_exception(exc)

    def _execute(self, cmd: MT5Command) -> Any:  # noqa: C901, PLR0911
        name = cmd.name
        if name == "initialize":
            return self._conn.initialize(*cmd.args, **cmd.kwargs)
        if name == "shutdown":
            return self._conn.shutdown()
        if name == "terminal_info":
            return self._conn.terminal_info()
        if name == "account_info":
            return self._conn.account_info()
        if name == "broker_offset":
            # Cached at initialize() time; safe to read from any thread.
            return getattr(self._conn, "_broker_offset", 0)
        if name == "symbols_get":
            return self._symbols_get(*cmd.args, **cmd.kwargs)
        if name == "symbol_info":
            return self._symbol_info(*cmd.args, **cmd.kwargs)
        if name == "symbol_select":
            return self._symbol_select(*cmd.args, **cmd.kwargs)
        if name == "symbol_info_tick":
            return self._symbol_info_tick(*cmd.args, **cmd.kwargs)
        if name == "copy_rates_from_pos":
            return self._copy_rates(*cmd.args, **cmd.kwargs)
        if name == "orders_get":
            return self._orders_get(*cmd.args, **cmd.kwargs)
        if name == "positions_get":
            return self._positions_get(*cmd.args, **cmd.kwargs)
        if name == "history_deals_get":
            return self._history_deals_get(*cmd.args, **cmd.kwargs)
        if name == "order_send":
            return self._order_send(*cmd.args, **cmd.kwargs)
        if name == "order_calc_margin":
            return self._order_calc_margin(*cmd.args, **cmd.kwargs)
        if name == "order_calc_profit":
            return self._order_calc_profit(*cmd.args, **cmd.kwargs)
        if name == "order_check":
            return self._order_check(*cmd.args, **cmd.kwargs)
        raise ValueError(f"Unknown command {name}")

    def _symbols_get(self, group: str | None = None) -> list[SymbolInfo]:
        if _get_mt5() is None:
            return []
        raws = _require_mt5().symbols_get(group) if group else _require_mt5().symbols_get()
        if not raws:
            return []
        return [SymbolInfo.from_mt5(r, self._conn.broker_offset) for r in raws]

    def _symbol_info(self, symbol: str) -> SymbolInfo | None:
        if _get_mt5() is None:
            return None
        raw = _require_mt5().symbol_info(symbol)
        if raw is None:
            return None
        return SymbolInfo.from_mt5(raw, self._conn.broker_offset)

    def _symbol_select(self, symbol: str, enable: bool = True) -> bool:
        if _get_mt5() is None:
            return False
        return bool(_require_mt5().symbol_select(symbol, enable))

    def _symbol_info_tick(self, symbol: str) -> Tick | None:
        if _get_mt5() is None:
            return None
        raw = _require_mt5().symbol_info_tick(symbol)
        if raw is None:
            return None
        return Tick.from_mt5(raw, symbol, self._conn.broker_offset)

    def _copy_rates(self, symbol: str, timeframe: str, start: int, count: int) -> list[Bar]:
        if _get_mt5() is None:
            return []
        tf = _tf_to_mt5(timeframe)
        raws = _require_mt5().copy_rates_from_pos(symbol, tf, start, count)
        if raws is None:
            return []
        out: list[Bar] = []
        for r in raws:
            # r may be tuple or numpy structured array
            if hasattr(r, "_asdict"):
                out.append(Bar.from_mt5(r, symbol, timeframe, self._conn.broker_offset))
            elif isinstance(r, list | tuple):
                out.append(Bar.from_mt5(tuple(r), symbol, timeframe, self._conn.broker_offset))
            else:
                # numpy void
                try:
                    tup = (
                        int(r[0]),
                        float(r[1]),
                        float(r[2]),
                        float(r[3]),
                        float(r[4]),
                        int(r[5]),
                        int(r[6]),
                        int(r[7]),
                    )
                    out.append(Bar.from_mt5(tup, symbol, timeframe, self._conn.broker_offset))
                except Exception:
                    continue
        return out

    def _orders_get(self, **kwargs: Any) -> list[Order]:
        if _get_mt5() is None:
            return []
        raws = _require_mt5().orders_get(**kwargs) if kwargs else _require_mt5().orders_get()
        if not raws:
            return []
        return [Order.from_mt5(r, self._conn.broker_offset) for r in raws]

    def _positions_get(self, **kwargs: Any) -> list[PositionInfo]:
        if _get_mt5() is None:
            return []
        raws = _require_mt5().positions_get(**kwargs) if kwargs else _require_mt5().positions_get()
        if not raws:
            return []
        return [PositionInfo.from_mt5(r, self._conn.broker_offset) for r in raws]

    def _history_deals_get(self, from_date: dt.datetime, to_date: dt.datetime) -> list[Deal]:
        if _get_mt5() is None:
            return []
        raws = _require_mt5().history_deals_get(from_date, to_date)
        if not raws:
            return []
        return [Deal.from_mt5(r, self._conn.broker_offset) for r in raws]

    def _order_send(self, request: dict[str, Any]) -> dict[str, Any]:
        if _get_mt5() is None:
            return {"retcode": 10031, "comment": "MT5 not available"}
        return _require_mt5().order_send(request)  # type: ignore[no-any-return]

    def _order_calc_margin(self, *args: Any, **kwargs: Any) -> float:
        if _get_mt5() is None:
            return 0.0
        return float(_require_mt5().order_calc_margin(*args, **kwargs) or 0)

    def _order_calc_profit(self, *args: Any, **kwargs: Any) -> float:
        if _get_mt5() is None:
            return 0.0
        return float(_require_mt5().order_calc_profit(*args, **kwargs) or 0)

    def _order_check(self, request: dict[str, Any]) -> dict[str, Any]:
        if _get_mt5() is None:
            return {"retcode": 10031}
        return _require_mt5().order_check(request)  # type: ignore[no-any-return]


class MT5Gateway(QObject):
    """Single-threaded owner of all MT5 calls."""

    connection_state_changed = Signal(str)
    connection_lost = Signal(str)
    connection_restored = Signal()
    tick_received = Signal(str, object)
    mt5_error = Signal(object)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._queue: queue.Queue[MT5Command] = queue.Queue()
        self._conn = MT5Connection()
        self._state: MT5ConnectionState = "disconnected"
        self._thread = QThread(self)
        self._worker = _Worker(self._queue, self._conn)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._thread.start()

        # heartbeat
        self._heartbeat = QTimer(self)
        self._heartbeat.setInterval(5000)
        self._heartbeat.timeout.connect(self._on_heartbeat)
        self._heartbeat.start()

        self._reconnect_attempts = 0
        self._saved_path: str | None = None
        self._saved_login: int | None = None
        self._saved_password: str | None = None
        self._saved_server: str | None = None
        self._last_connected = False

    def _set_state(self, state: MT5ConnectionState) -> None:
        if state != self._state:
            self._state = state
            self.connection_state_changed.emit(state)

    def _on_heartbeat(self) -> None:
        # lightweight check via queue
        fut = self.terminal_info()
        try:
            info = fut.result(timeout=3)
            connected = bool(info and info.connected)
        except Exception:
            connected = False
        if connected and not self._last_connected:
            self._last_connected = True
            self._set_state("connected")
            self.connection_restored.emit()
            self._reconnect_attempts = 0
        elif not connected and self._last_connected:
            self._last_connected = False
            self._set_state("reconnecting")
            # check if positions open
            try:
                pos_fut = self.positions_get()
                positions = pos_fut.result(timeout=2)
                if positions:
                    msg = "Connection lost while positions are open"
                    logger.critical(msg)
                    audit_log.log(
                        "system",
                        "mt5_connection_lost",
                        after={"reason": msg, "open_positions": len(positions)},
                    )
                    self.connection_lost.emit(msg)
                else:
                    self.connection_lost.emit("Connection lost")
            except Exception:
                self.connection_lost.emit("Connection lost")
            self._schedule_reconnect()
        elif not connected and self._state == "connected":
            self._set_state("reconnecting")
            self._schedule_reconnect()

    def _schedule_reconnect(self) -> None:
        if self._saved_login is None:
            return
        delay = min(2**self._reconnect_attempts, 60)
        self._reconnect_attempts += 1
        logger.info(f"Scheduling reconnect in {delay}s (attempt {self._reconnect_attempts})")
        QTimer.singleShot(int(delay * 1000), self._try_reconnect)

    def _try_reconnect(self) -> None:
        if self._saved_login is None:
            return
        logger.info("Attempting auto-reconnect")
        try:
            fut = self.initialize(
                self._saved_path, self._saved_login, self._saved_password or "", self._saved_server or ""
            )
            ok = fut.result(timeout=35)
            if ok:
                logger.info("Auto-reconnect succeeded")
                self._set_state("connected")
                self._last_connected = True
                self.connection_restored.emit()
                self._reconnect_attempts = 0
            else:
                self._schedule_reconnect()
        except Exception as exc:
            logger.warning(f"Auto-reconnect failed: {exc}")
            self._schedule_reconnect()

    def _submit(self, name: str, *args: Any, timeout: float = 5.0, **kwargs: Any) -> concurrent.futures.Future[Any]:
        fut: concurrent.futures.Future[Any] = concurrent.futures.Future()
        cmd = MT5Command(name=name, args=args, kwargs=kwargs, future=fut, timeout=timeout)
        self._queue.put(cmd)

        # Enforce timeout on the future. We spawn a daemon Timer that fires
        # at most once. If the worker resolves the future first, the
        # ``add_done_callback`` cancels the timer (no resource leak).
        # ``set_exception`` is wrapped in try/except because between
        # ``fut.done()`` returning False and the call below, the worker
        # may complete the future (TOCTOU race) — calling ``set_exception``
        # on a done future raises ``InvalidStateError``.
        def _timeout_check() -> None:
            if not fut.done():
                try:
                    fut.set_exception(MT5TimeoutError(f"MT5 call {name} timed out after {timeout}s"))
                except concurrent.futures.InvalidStateError:
                    pass  # Worker won the race; nothing to do.

        timer = threading.Timer(timeout, _timeout_check)
        timer.daemon = True
        fut.add_done_callback(lambda _fut: timer.cancel())
        timer.start()
        return fut

    # public API
    def initialize(
        self, path: str | None, login: int, password: str, server: str, timeout: int = 60000
    ) -> concurrent.futures.Future[bool]:
        self._set_state("connecting")
        self._saved_path = path
        self._saved_login = login
        self._saved_password = password
        self._saved_server = server
        return self._submit("initialize", path, login, password, server, timeout=30.0)

    def shutdown(self) -> concurrent.futures.Future[None]:
        self._set_state("disconnected")
        return self._submit("shutdown", timeout=5.0)

    def terminal_info(self) -> concurrent.futures.Future[TerminalInfo | None]:
        return self._submit("terminal_info", timeout=5.0)

    def account_info(self) -> concurrent.futures.Future[AccountInfo | None]:
        return self._submit("account_info", timeout=5.0)

    def broker_offset(self) -> concurrent.futures.Future[int]:
        """Return the cached broker UTC offset (seconds) via the worker thread.

        The offset is computed once at ``initialize()`` time and cached on
        the ``MT5Connection`` instance. Reading it through the gateway (rather
        than calling :func:`detect_broker_utc_offset` directly from the main
        thread) avoids the ADR-002 violation noted in the Phase 1-3 audit
        (C3): no MT5 calls happen outside the gateway worker thread.
        """
        return self._submit("broker_offset", timeout=2.0)

    def symbols_get(self, group: str | None = None) -> concurrent.futures.Future[list[SymbolInfo]]:
        return self._submit("symbols_get", group, timeout=10.0)

    def symbol_info(self, symbol: str) -> concurrent.futures.Future[SymbolInfo | None]:
        return self._submit("symbol_info", symbol, timeout=5.0)

    def symbol_select(self, symbol: str, enable: bool = True) -> concurrent.futures.Future[bool]:
        return self._submit("symbol_select", symbol, enable, timeout=5.0)

    def symbol_info_tick(self, symbol: str) -> concurrent.futures.Future[Tick | None]:
        return self._submit("symbol_info_tick", symbol, timeout=5.0)

    def copy_rates_from_pos(
        self, symbol: str, timeframe: str, start: int, count: int
    ) -> concurrent.futures.Future[list[Bar]]:
        return self._submit("copy_rates_from_pos", symbol, timeframe, start, count, timeout=60.0)

    def orders_get(self, **kwargs: Any) -> concurrent.futures.Future[list[Order]]:
        return self._submit("orders_get", timeout=10.0, **kwargs)

    def positions_get(self, **kwargs: Any) -> concurrent.futures.Future[list[PositionInfo]]:
        return self._submit("positions_get", timeout=10.0, **kwargs)

    def history_deals_get(self, from_date: dt.datetime, to_date: dt.datetime) -> concurrent.futures.Future[list[Deal]]:
        return self._submit("history_deals_get", from_date, to_date, timeout=60.0)

    def order_send(self, request: dict[str, Any]) -> concurrent.futures.Future[dict[str, Any]]:
        return self._submit("order_send", request, timeout=10.0)

    def order_calc_margin(self, *args: Any, **kwargs: Any) -> concurrent.futures.Future[float]:
        return self._submit("order_calc_margin", *args, timeout=5.0, **kwargs)

    def order_calc_profit(self, *args: Any, **kwargs: Any) -> concurrent.futures.Future[float]:
        return self._submit("order_calc_profit", *args, timeout=5.0, **kwargs)

    def order_check(self, request: dict[str, Any]) -> concurrent.futures.Future[dict[str, Any]]:
        return self._submit("order_check", request, timeout=5.0)

    def is_connected(self) -> bool:
        return self._state == "connected"

    def close(self) -> None:
        """Stop the worker QThread and the heartbeat QTimer.

        Safe to call multiple times. Without this, the worker thread leaks
        and Qt prints "QThread: Destroyed while thread is still running" on
        garbage collection (Phase 1-3 audit C7).
        """
        try:
            self._heartbeat.stop()
        except Exception:
            pass
        try:
            self._worker.stop()
        except Exception:
            pass
        try:
            self._thread.quit()
            self._thread.wait(2000)
        except Exception:
            pass

    def __del__(self) -> None:
        """Best-effort cleanup if :meth:`close` wasn't called explicitly.

        Per Opus 5.5 audit: ``__del__`` may run on the GUI thread during GC.
        ``thread.wait()`` without a timeout would deadlock if the worker is
        blocked. Use a short timeout and never block GC.
        """
        try:
            self._heartbeat.stop()
        except Exception:
            pass
        try:
            self._worker.stop()
        except Exception:
            pass
        try:
            self._thread.quit()
            self._thread.wait(100)  # 100ms max — never block GC
        except Exception:
            pass
