"""FakeMT5 simulator — mimics MetaTrader5 package API."""

from __future__ import annotations

import collections
import datetime as dt
import time
from typing import Any


class _FakeInfo:
    def __init__(self, **kwargs: Any) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)

    def _asdict(self) -> dict[str, Any]:
        return dict(self.__dict__)


class FakeMT5:
    """Scripted FakeMT5."""

    def __init__(self, scenario: dict[str, Any] | None = None) -> None:
        self.scenario: dict[str, Any] = scenario or {}
        self.__version__ = "5.0.45-fake"
        self._connected = True
        self._initialized = False
        self.call_counts: collections.Counter[str] = collections.Counter()
        self._sleep: dict[str, float] = {}
        # defaults
        self._terminal_info = _FakeInfo(
            build=4567,
            connected=True,
            trade_allowed=True,
            community_account=False,
            community_connection=False,
            codepage=1251,
            name="MetaTrader 5",
            path=r"C:\Program Files\MetaTrader 5\terminal64.exe",
            data_path=r"C:\Users\test\AppData\Roaming\MetaQuotes\Terminal\ABC",
            common_data_path=r"C:\Users\test\AppData\Roaming\MetaQuotes\Terminal\Common",
            ping_last=42,
        )
        self._account_info = _FakeInfo(
            login=12345678,
            leverage=100,
            server="MetaQuotes-Demo",
            currency="USD",
            balance=10000.0,
            equity=10050.0,
            margin=100.0,
            margin_free=9900.0,
            margin_level=10050.0,
            name="Test User",
            company="MetaQuotes",
            profit=50.0,
            credit=0.0,
            margin_mode=1,
            trade_allowed=True,
            trade_expert=True,
            limit_orders=200,
            margin_so_call=50.0,
            margin_so_so=20.0,
        )
        self._symbols: list[_FakeInfo] = [
            _FakeInfo(
                name="EURUSD",
                path="Forex",
                digits=5,
                point=0.00001,
                spread=10,
                spread_float=False,
                contract_size=100000,
                trade_tick_size=0.00001,
                trade_tick_value=1.0,
                trade_mode=2,
                trade_stops_level=10,
                trade_freeze_level=0,
                volume_min=0.01,
                volume_max=100.0,
                volume_step=0.01,
                currency_base="EUR",
                currency_profit="USD",
                visible=True,
                select=True,
            ),
            _FakeInfo(
                name="EURUSD.m",
                path="Forex",
                digits=5,
                point=0.00001,
                spread=12,
                spread_float=False,
                contract_size=100000,
                trade_tick_size=0.00001,
                trade_tick_value=1.0,
                trade_mode=2,
                trade_stops_level=10,
                trade_freeze_level=0,
                volume_min=0.01,
                volume_max=100.0,
                volume_step=0.01,
                currency_base="EUR",
                currency_profit="USD",
                visible=True,
                select=True,
            ),
            _FakeInfo(
                name="GBPUSD.m",
                path="Forex",
                digits=5,
                point=0.00001,
                spread=12,
                spread_float=False,
                contract_size=100000,
                trade_tick_size=0.00001,
                trade_tick_value=1.0,
                trade_mode=2,
                trade_stops_level=10,
                trade_freeze_level=0,
                volume_min=0.01,
                volume_max=100.0,
                volume_step=0.01,
                currency_base="GBP",
                currency_profit="USD",
                visible=True,
                select=True,
            ),
            _FakeInfo(
                name="XAUUSD",
                path="Metals",
                digits=2,
                point=0.01,
                spread=30,
                spread_float=False,
                contract_size=100,
                trade_tick_size=0.01,
                trade_tick_value=1.0,
                trade_mode=2,
                trade_stops_level=20,
                trade_freeze_level=0,
                volume_min=0.01,
                volume_max=10.0,
                volume_step=0.01,
                currency_base="XAU",
                currency_profit="USD",
                visible=True,
                select=True,
            ),
        ]
        # ticks: symbol -> (time, bid, ask)
        now = int(dt.datetime.now(tz=dt.UTC).timestamp())
        self._ticks: dict[str, _FakeInfo] = {
            "EURUSD": _FakeInfo(time=now, bid=1.08500, ask=1.08510, last=1.08505, volume=100, flags=0),
            "GBPUSD": _FakeInfo(time=now, bid=1.27000, ask=1.27010, last=1.27005, volume=100, flags=0),
            "XAUUSD": _FakeInfo(time=now, bid=2030.00, ask=2030.50, last=2030.25, volume=10, flags=0),
        }
        # bars: "EURUSD,M15" -> list of tuples
        bars = []
        base_time = now - 10 * 900
        for i in range(20):
            t = base_time + i * 900
            o = 1.08 + i * 0.0001
            bars.append((t, o, o + 0.0002, o - 0.0001, o + 0.00005, 100, 10, 0))
        self._bars: dict[str, list[tuple[Any, ...]]] = {"EURUSD,M15": bars}
        # deals
        self._deals: list[_FakeInfo] = []
        for i in range(5):
            self._deals.append(
                _FakeInfo(
                    ticket=1000 + i,
                    order=2000 + i,
                    time=now - i * 86400,
                    type=0 if i % 2 == 0 else 1,
                    entry=1,
                    magic=0,
                    position_id=3000 + i,
                    commission=0.0,
                    swap=0.0,
                    profit=10.0 * i,
                    symbol="EURUSD",
                    comment="",
                    external_id="",
                    volume=0.1,
                    price=1.08,
                )
            )
        self._last_error: tuple[int, str] = (0, "No error")
        # apply scenario overrides
        if "ticks" in self.scenario:
            for sym, vals in self.scenario["ticks"].items():
                # vals is list of (time, bid, ask)
                if vals:
                    t, b, a = vals[0]
                    self._ticks[sym] = _FakeInfo(
                        time=int(t.timestamp()) if isinstance(t, dt.datetime) else int(t),
                        bid=b,
                        ask=a,
                        last=(b + a) / 2,
                        volume=100,
                        flags=0,
                    )
        if "bars" in self.scenario:
            self._bars.update(self.scenario["bars"])
        if "sleep" in self.scenario:
            self._sleep.update(self.scenario["sleep"])

    # API
    def initialize(
        self,
        path: str | None = None,
        login: int | None = None,
        password: str | None = None,
        server: str | None = None,
        timeout: int = 60000,
    ) -> bool:  # noqa: ARG002
        self.call_counts["initialize"] += 1
        if "initialize" in self._sleep:
            time.sleep(self._sleep["initialize"])
        # simulate investor password
        if password == "investor":
            self._account_info.trade_allowed = False
            self._initialized = True
            self._connected = True
            return True
        if login == 99999:
            self._last_error = (-6, "Authorization failed")
            return False
        self._initialized = True
        self._connected = True
        self._terminal_info.connected = True
        return True

    def shutdown(self) -> None:
        self.call_counts["shutdown"] += 1
        self._initialized = False
        self._connected = False

    def terminal_info(self) -> Any:
        self.call_counts["terminal_info"] += 1
        if "terminal_info" in self._sleep:
            time.sleep(self._sleep["terminal_info"])
        if not self._connected:
            return None
        return self._terminal_info

    def account_info(self) -> Any:
        self.call_counts["account_info"] += 1
        if not self._connected:
            return None
        return self._account_info

    def symbols_get(self, group: str | None = None) -> Any:  # noqa: ARG002
        self.call_counts["symbols_get"] += 1
        return list(self._symbols)

    def symbol_info(self, symbol: str) -> Any:
        self.call_counts["symbol_info"] += 1
        for s in self._symbols:
            if s.name == symbol:
                return s
        return None

    def symbol_select(self, symbol: str, enable: bool = True) -> bool:  # noqa: ARG002
        self.call_counts["symbol_select"] += 1
        return True

    def symbol_info_tick(self, symbol: str) -> Any:
        self.call_counts["symbol_info_tick"] += 1
        if "symbol_info_tick" in self._sleep:
            time.sleep(self._sleep["symbol_info_tick"])
        if not self._connected:
            return None
        return self._ticks.get(symbol)

    def copy_rates_from_pos(self, symbol: str, timeframe: int, start: int, count: int) -> Any:
        self.call_counts["copy_rates_from_pos"] += 1
        if "copy_rates_from_pos" in self._sleep:
            time.sleep(self._sleep["copy_rates_from_pos"])
        # map timeframe int back to string for lookup
        tf_str = "M15"
        for k, v in {"M1": 1, "M5": 5, "M15": 15, "M30": 30, "H1": 16385, "H4": 16386, "D1": 16408}.items():
            if v == timeframe:
                tf_str = k
                break
        key = f"{symbol},{tf_str}"
        bars = self._bars.get(key, self._bars.get("EURUSD,M15", []))
        # slice from start
        return bars[start : start + count]

    def orders_get(self, **kwargs: Any) -> Any:  # noqa: ARG002
        self.call_counts["orders_get"] += 1
        return []

    def positions_get(self, **kwargs: Any) -> Any:  # noqa: ARG002
        self.call_counts["positions_get"] += 1
        return []

    def history_deals_get(self, from_date: dt.datetime, to_date: dt.datetime) -> Any:  # noqa: ARG002
        self.call_counts["history_deals_get"] += 1
        return list(self._deals)

    def order_send(self, request: dict[str, Any]) -> Any:
        self.call_counts["order_send"] += 1
        retcodes = self.scenario.get("retcodes", {}).get("order_send", [])
        if retcodes:
            rc = retcodes.pop(0)
            return {"retcode": rc, "comment": "simulated"}
        return {"retcode": 10009, "order": 12345}

    def order_calc_margin(self, *args: Any, **kwargs: Any) -> Any:  # noqa: ARG002
        self.call_counts["order_calc_margin"] += 1
        return 100.0

    def order_calc_profit(self, *args: Any, **kwargs: Any) -> Any:  # noqa: ARG002
        self.call_counts["order_calc_profit"] += 1
        return 10.0

    def order_check(self, request: dict[str, Any]) -> Any:  # noqa: ARG002
        self.call_counts["order_check"] += 1
        return {"retcode": 0, "comment": "ok"}

    def last_error(self) -> tuple[int, str]:
        return self._last_error

    # test helpers
    def disconnect(self) -> None:
        self._connected = False
        if hasattr(self._terminal_info, "connected"):
            self._terminal_info.connected = False

    def reconnect(self) -> None:
        self._connected = True
        if hasattr(self._terminal_info, "connected"):
            self._terminal_info.connected = True

    # constants
    TIMEFRAME_M1 = 1
    TIMEFRAME_M5 = 5
    TIMEFRAME_M15 = 15
    TIMEFRAME_M30 = 30
    TIMEFRAME_H1 = 16385
    TIMEFRAME_H4 = 16386
    TIMEFRAME_D1 = 16408
    TIMEFRAME_W1 = 32769
    TIMEFRAME_MN1 = 49152
