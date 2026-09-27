"""Connection diagnostics."""

from __future__ import annotations

import datetime as dt

from PySide6.QtCore import QObject

from app.mt5.connection import detect_broker_utc_offset
from app.mt5.connection_wizard import ConnectionCheck
from app.mt5.gateway import MT5Gateway
from app.observability import get_logger

logger = get_logger("mt5.diagnostics")


class ConnectionDiagnostics(QObject):
    def __init__(self, gateway: MT5Gateway, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.gateway = gateway

    def run_all_checks(self) -> dict[str, ConnectionCheck]:
        checks: dict[str, ConnectionCheck] = {}

        def add(name: str, status: str, detail: str) -> None:  # type: ignore[no-untyped-def]
            checks[name] = ConnectionCheck(name=name, status=status, detail=detail)  # type: ignore[arg-type]

        # terminal
        try:
            tinfo = self.gateway.terminal_info().result(timeout=5)
            if tinfo and tinfo.connected:
                add("terminal", "ok", f"build {tinfo.build} connected")
            elif tinfo:
                add("terminal", "error", "not connected")
            else:
                add("terminal", "error", "no terminal info")
        except Exception as exc:
            add("terminal", "error", str(exc))

        # account
        try:
            acc = self.gateway.account_info().result(timeout=5)
            if acc:
                add("account", "ok", f"{acc.login} {acc.company} {acc.server} {acc.account_type}")
            else:
                add("account", "error", "no account info")
        except Exception as exc:
            add("account", "error", str(exc))

        # ping
        try:
            tinfo2 = self.gateway.terminal_info().result(timeout=5)
            ping = getattr(tinfo2, "ping_last", None) if tinfo2 else None
            add("ping_last", "ok" if ping is not None else "warning", f"ping_last={ping}")
        except Exception as exc:
            add("ping_last", "warning", str(exc))

        # broker offset
        try:
            off = detect_broker_utc_offset()
            add("broker_utc_offset", "ok", f"{off}s ({off/3600:.1f}h)")
        except Exception as exc:
            add("broker_utc_offset", "warning", str(exc))

        # permissions
        try:
            tinfo3 = self.gateway.terminal_info().result(timeout=5)
            acc2 = self.gateway.account_info().result(timeout=5)
            algo = bool(tinfo3 and tinfo3.allow_auto_trading)
            trade = bool(tinfo3 and tinfo3.trade_allowed)
            expert = bool(acc2 and acc2.trade_expert)
            add(
                "permission_flags",
                "ok" if algo and trade else "warning",
                f"algo={algo} trade_allowed={trade} trade_expert={expert}",
            )
        except Exception as exc:
            add("permission_flags", "warning", str(exc))

        # history per symbol/tf
        try:
            for sym, tf in [("EURUSD", "M15"), ("GBPUSD", "M15"), ("XAUUSD", "M15")]:
                try:
                    bars = self.gateway.copy_rates_from_pos(sym, tf, 0, 10).result(timeout=10)
                    add(f"history_{sym}_{tf}", "ok" if bars else "warning", f"{len(bars) if bars else 0} bars")
                except Exception as exc:
                    add(f"history_{sym}_{tf}", "warning", str(exc))
        except Exception as exc:
            add("history", "warning", str(exc))

        # symbol specs
        try:
            syms = self.gateway.symbols_get().result(timeout=10)
            add("symbol_specs_table", "ok" if syms else "warning", f"{len(syms) if syms else 0} symbols")
        except Exception as exc:
            add("symbol_specs_table", "warning", str(exc))

        # quotes fresh
        try:
            tick = self.gateway.symbol_info_tick("EURUSD").result(timeout=5)
            if tick:
                age = (dt.datetime.now(tz=dt.UTC) - tick.time).total_seconds()
                status = "ok" if age < 5 else "warning" if age < 60 else "error"
                add("quotes_fresh", status, f"age {age:.1f}s bid={tick.bid} ask={tick.ask}")
            else:
                add("quotes_fresh", "warning", "no tick")
        except Exception as exc:
            add("quotes_fresh", "warning", str(exc))

        return checks

    def generate_text_report(self, checks: dict[str, ConnectionCheck]) -> str:
        lines: list[str] = []
        lines.append("MT5 Connection Diagnostics")
        lines.append("=" * 40)
        lines.append(f"Generated: {dt.datetime.now(tz=dt.UTC).isoformat()}")
        lines.append("")
        for name, chk in checks.items():
            lines.append(f"[{chk.status.upper():7}] {name}: {chk.detail}")
        lines.append("")
        lines.append("Notes: passwords are never included in this report.")
        return "\n".join(lines)
