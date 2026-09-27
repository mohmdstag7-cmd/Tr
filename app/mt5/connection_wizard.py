"""First-run connection wizard."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from PySide6.QtCore import QObject, QThread, Signal

from app.mt5.gateway import MT5Gateway
from app.mt5.profiles import AccountProfile, ProfileManager
from app.observability import get_logger

logger = get_logger("mt5.wizard")


@dataclass
class ConnectionCheck:
    name: str
    status: Literal["pending", "ok", "warning", "error", "skipped"] = "pending"
    detail: str = ""


class _WizardWorker(QObject):
    progress = Signal(str, str, str)  # step, status, detail
    finished_ok = Signal(object, object)  # AccountInfo, TerminalInfo
    finished_err = Signal(str, str)
    investor_detected = Signal()

    def __init__(
        self,
        gateway: MT5Gateway,
        terminal_path: str | None,
        login: int,
        password: str,
        server: str,
    ) -> None:
        super().__init__()
        self.gateway = gateway
        self.terminal_path = terminal_path
        self.login = login
        self.password = password
        self.server = server

    def run(self) -> None:  # noqa: C901, PLR0912
        def emit(step: str, status: str, detail: str = "") -> None:
            self.progress.emit(step, status, detail)

        try:
            # terminal_found
            emit("terminal_found", "pending", "Checking terminal")
            if self.terminal_path:
                import pathlib

                if not pathlib.Path(self.terminal_path).exists():
                    emit("terminal_found", "warning", "Terminal path not found, trying default")
                else:
                    emit("terminal_found", "ok", f"Terminal: {self.terminal_path}")
            else:
                emit("terminal_found", "ok", "Using default terminal")
            # login
            emit("login_ok", "pending", "Connecting")
            fut = self.gateway.initialize(self.terminal_path, self.login, self.password, self.server)
            try:
                ok = fut.result(timeout=35)
            except Exception as exc:
                emit("login_ok", "error", str(exc))
                self.finished_err.emit("login_ok", str(exc))
                return
            if not ok:
                emit("login_ok", "error", "Initialize returned false")
                self.finished_err.emit("login_ok", "Initialize failed")
                return
            emit("login_ok", "ok", "Login succeeded")

            # check investor password via account_info trade_allowed
            emit("account_info_loaded", "pending", "Loading account info")
            try:
                acc = self.gateway.account_info().result(timeout=5)
                term = self.gateway.terminal_info().result(timeout=5)
            except Exception as exc:
                emit("account_info_loaded", "error", str(exc))
                self.finished_err.emit("account_info_loaded", str(exc))
                return
            if acc is None:
                emit("account_info_loaded", "error", "No account info")
                self.finished_err.emit("account_info_loaded", "No account info")
                return
            emit("account_info_loaded", "ok", f"{acc.login} {acc.company} {acc.server}")

            # investor check: if trade_allowed false but connected, likely investor
            if not acc.trade_allowed:
                logger.warning("Investor password detected")
                self.investor_detected.emit()

            # algo_trading
            emit("algo_trading_on", "pending", "Checking algo trading")
            if term and not term.allow_auto_trading:
                emit("algo_trading_on", "warning", "Algo trading disabled — press Algo Trading button in MT5")
            else:
                emit("algo_trading_on", "ok", "Algo trading enabled")

            # trading_allowed
            emit("trading_allowed", "pending", "Checking trading allowed")
            if term and not term.trade_allowed:
                emit("trading_allowed", "warning", "Trading not allowed")
            else:
                emit("trading_allowed", "ok", "Trading allowed")

            # symbols
            emit("symbols_available", "pending", "Checking symbols")
            try:
                syms = self.gateway.symbols_get().result(timeout=10)
                if not syms:
                    emit("symbols_available", "warning", "No symbols found")
                else:
                    emit("symbols_available", "ok", f"{len(syms)} symbols")
            except Exception as exc:
                emit("symbols_available", "warning", str(exc))

            # live quotes
            emit("live_quotes", "pending", "Checking live quotes")
            try:
                tick = self.gateway.symbol_info_tick("EURUSD").result(timeout=5)
                if tick is None:
                    # try any symbol
                    syms2 = self.gateway.symbols_get().result(timeout=5)
                    if syms2:
                        tick = self.gateway.symbol_info_tick(syms2[0].name).result(timeout=5)
                if tick is None:
                    emit("live_quotes", "warning", "No live quotes")
                else:
                    emit("live_quotes", "ok", f"Tick {tick.symbol} {tick.bid}/{tick.ask}")
            except Exception as exc:
                emit("live_quotes", "warning", str(exc))

            # history
            emit("history_available", "pending", "Checking history")
            try:
                bars = self.gateway.copy_rates_from_pos("EURUSD", "M15", 0, 10).result(timeout=10)
                if not bars:
                    emit("history_available", "warning", "No history bars")
                else:
                    emit("history_available", "ok", f"{len(bars)} bars")
            except Exception as exc:
                emit("history_available", "warning", str(exc))

            self.finished_ok.emit(acc, term)

            # save profile
            try:
                pm = ProfileManager()
                prof = AccountProfile(
                    name=str(acc.login),
                    login=acc.login,
                    server=acc.server,
                    terminal_path=self.terminal_path,
                    is_investor_password=not acc.trade_allowed,
                )
                pm.save(prof, self.password)
                pm.set_default(prof.name)
            except Exception as exc:
                logger.warning(f"Failed to save profile: {exc}")

        except Exception as exc:  # pragma: no cover
            self.finished_err.emit("unknown", str(exc))


class ConnectionWizard(QObject):
    terminal_found = Signal(object)
    terminal_not_found = Signal()
    connection_progress = Signal(str, str)
    connection_success = Signal(object, object)
    connection_failed = Signal(str, str)
    investor_mode = Signal()

    def __init__(self, gateway: MT5Gateway, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.gateway = gateway
        self._thread: QThread | None = None
        self._worker: _WizardWorker | None = None

    def start(
        self,
        terminal_path: str | None,
        login: int,
        password: str,
        server: str,
        checklist: list[ConnectionCheck] | None = None,  # noqa: ARG002
    ) -> None:
        self._thread = QThread(self)
        self._worker = _WizardWorker(self.gateway, terminal_path, login, password, server)
        self._worker.moveToThread(self._thread)
        if self._thread is None:  # type: ignore[truthy-bool]
            return  # Defensive — QThread(self) above never returns None
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(lambda step, status, detail: self.connection_progress.emit(step, status))
        self._worker.finished_ok.connect(lambda acc, term: self.connection_success.emit(acc, term))
        self._worker.finished_err.connect(lambda step, err: self.connection_failed.emit(step, err))
        self._worker.investor_detected.connect(lambda: self.investor_mode.emit())
        self._worker.finished_ok.connect(lambda *_: self._cleanup())
        self._worker.finished_err.connect(lambda *_: self._cleanup())
        self._thread.start()

    def _cleanup(self) -> None:
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(2000)
