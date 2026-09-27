"""Pydantic v2 models for MT5 data."""

from __future__ import annotations

import datetime as dt
from typing import Any, Literal

from pydantic import BaseModel, Field


def _to_utc(naive_or_aware: dt.datetime | int | float | None, offset_seconds: int = 0) -> dt.datetime | None:
    if naive_or_aware is None:
        return None
    if isinstance(naive_or_aware, int | float):
        # MT5 returns seconds since epoch (broker time)
        broker_dt = dt.datetime.fromtimestamp(int(naive_or_aware), tz=dt.UTC)
        # broker time = UTC + offset, so UTC = broker - offset
        return broker_dt - dt.timedelta(seconds=offset_seconds)
    if isinstance(naive_or_aware, dt.datetime):
        if naive_or_aware.tzinfo is None:
            # naive broker time -> treat as broker tz then convert to UTC
            aware = naive_or_aware.replace(tzinfo=dt.timezone(dt.timedelta(seconds=offset_seconds)))
            return aware.astimezone(dt.UTC)
        return naive_or_aware.astimezone(dt.UTC)
    return None


def _ensure_utc(value: dt.datetime | int | float | None, offset: int = 0) -> dt.datetime:
    res = _to_utc(value, offset)
    if res is None:
        return dt.datetime.now(tz=dt.UTC)
    return res


class TerminalInfo(BaseModel):
    build: int | None = None
    connected: bool = False
    trade_allowed: bool = False
    community_account: bool | None = None
    community_connection: bool | None = None
    allow_auto_trading: bool = False
    code_page: int | None = None
    name: str | None = None
    path: str | None = None
    data_path: str | None = None
    common_data_path: str | None = None
    last_error: str | None = None
    ping_last: int | None = None

    @classmethod
    def from_mt5(cls, raw: Any, offset: int = 0) -> TerminalInfo:  # noqa: ARG003
        if raw is None:
            return cls(connected=False)
        d = raw._asdict() if hasattr(raw, "_asdict") else dict(raw.__dict__) if hasattr(raw, "__dict__") else {}

        # raw may be tuple-like; try attribute access
        def g(k: str, default: Any = None) -> Any:
            return getattr(raw, k, d.get(k, default))

        return cls(
            build=g("build"),
            connected=bool(g("connected", False)),
            trade_allowed=bool(g("trade_allowed", False)),
            community_account=g("community_account"),
            community_connection=g("community_connection"),
            allow_auto_trading=bool(g("trade_allowed", False)),
            code_page=g("codepage") or g("code_page"),
            name=g("name"),
            path=g("path"),
            data_path=g("data_path"),
            common_data_path=g("common_data_path"),
            ping_last=g("ping_last"),
        )


class AccountInfo(BaseModel):
    login: int
    trade_account: str | None = None
    leverage: int = 0
    server: str = ""
    currency: str = ""
    balance: float = 0.0
    equity: float = 0.0
    margin: float = 0.0
    margin_free: float = 0.0
    margin_level: float = 0.0
    margin_initial: float | None = None
    margin_maintenance: float | None = None
    name: str | None = None
    company: str | None = None
    profit: float = 0.0
    credit: float = 0.0
    margin_mode: Literal[1, 2, 3] | int = 1
    trade_allowed: bool = False
    trade_expert: bool = False
    margin_so_mode: int | None = None
    profit_currency: str | None = None
    profit_balance: float | None = None
    profit_so_activation: float | None = None
    profit_so_level: float | None = None
    swap_mode: int | None = None
    swap_credit: float | None = None
    swap_profit: float | None = None
    limit_orders: int | None = None
    margin_call: float | None = None
    margin_stop_out: float | None = None
    ping_last: int | None = None
    ping_average: int | None = None
    account_type: Literal["demo", "real", "contest"] = "demo"

    @classmethod
    def from_mt5(cls, raw: Any, offset: int = 0) -> AccountInfo:  # noqa: ARG003
        def g(k: str, default: Any = None) -> Any:
            return getattr(raw, k, default)

        login = int(g("login", 0))
        server = str(g("server", "") or "")
        # Infer account_type per MT5 convention:
        # - server name contains 'contest' -> contest
        # - login < 100000 -> demo
        # - otherwise -> real
        if "contest" in server.lower():
            account_type: Literal["demo", "real", "contest"] = "contest"
        elif login < 100000:
            account_type = "demo"
        else:
            account_type = "real"
        return cls(
            login=login,
            trade_account=str(g("login", "")),
            leverage=int(g("leverage", 0) or 0),
            server=server,
            currency=str(g("currency", "") or ""),
            balance=float(g("balance", 0) or 0),
            equity=float(g("equity", 0) or 0),
            margin=float(g("margin", 0) or 0),
            margin_free=float(g("margin_free", 0) or g("free_margin", 0) or 0),
            margin_level=float(g("margin_level", 0) or 0),
            name=g("name"),
            company=g("company"),
            profit=float(g("profit", 0) or 0),
            credit=float(g("credit", 0) or 0),
            margin_mode=g("margin_mode", 1),
            trade_allowed=bool(g("trade_allowed", False)),
            trade_expert=bool(g("trade_expert", False)),
            limit_orders=g("limit_orders"),
            margin_call=g("margin_so_call") or g("margin_call"),
            margin_stop_out=g("margin_so_so") or g("margin_stop_out"),
            account_type=account_type,
        )


class SymbolInfo(BaseModel):
    name: str
    path: str | None = None
    base: str | None = None
    profit: str | None = None
    margin: str | None = None
    digits: int = 5
    point: float = 0.00001
    spread: int = 0
    spread_float: bool = False
    ticks_postime: int | None = None
    trade_contract_size: float = 100000
    trade_tick_size: float = 0.00001
    trade_tick_value: float = 1.0
    trade_tick_value_loss: float | None = None
    trade_tick_value_profit: float | None = None
    trade_mode: Literal["full", "closeonly", "disabled"] = "full"
    trade_stops_level: int = 0
    trade_freeze_level: int = 0
    trade_volume_min: float = 0.01
    trade_volume_max: float = 100.0
    trade_volume_step: float = 0.01
    currency_base: str | None = None
    currency_profit: str | None = None
    currency_margin: str | None = None
    fill_modes: list[int] = Field(default_factory=list)
    expiration_modes: list[int] = Field(default_factory=list)
    background: str | None = None
    visible: bool = True
    selection: bool = True
    visible_in_market_watch: bool = True
    session_deals: int | None = None
    session_buy_orders: int | None = None
    session_sell_orders: int | None = None
    volume_high: float | None = None
    volume_low: float | None = None

    @classmethod
    def from_mt5(cls, raw: Any, offset: int = 0) -> SymbolInfo:  # noqa: ARG003
        def g(k: str, default: Any = None) -> Any:
            return getattr(raw, k, default)

        mode = g("trade_mode", 0)
        if mode == 0:
            tmode: Literal["full", "closeonly", "disabled"] = "disabled"
        elif mode == 1:
            tmode = "closeonly"
        else:
            tmode = "full"
        name = str(g("name", "") or g("symbol", ""))
        return cls(
            name=name,
            path=g("path"),
            digits=int(g("digits", 5) or 5),
            point=float(g("point", 0.00001) or 0.00001),
            spread=int(g("spread", 0) or 0),
            spread_float=bool(g("spread_float", False)),
            trade_contract_size=float(g("contract_size", 100000) or g("trade_contract_size", 100000) or 100000),
            trade_tick_size=float(g("trade_tick_size", 0.00001) or 0.00001),
            trade_tick_value=float(g("trade_tick_value", 1) or 1),
            trade_mode=tmode,
            trade_stops_level=int(g("trade_stops_level", 0) or 0),
            trade_freeze_level=int(g("trade_freeze_level", 0) or 0),
            trade_volume_min=float(g("volume_min", 0.01) or 0.01),
            trade_volume_max=float(g("volume_max", 100) or 100),
            trade_volume_step=float(g("volume_step", 0.01) or 0.01),
            currency_base=g("currency_base"),
            currency_profit=g("currency_profit"),
            currency_margin=g("currency_margin"),
            visible=bool(g("visible", True)),
            selection=bool(g("select", True) or g("selection", True)),
            visible_in_market_watch=bool(g("visible", True)),
        )


class Tick(BaseModel):
    symbol: str
    time: dt.datetime
    bid: float
    ask: float
    last: float = 0.0
    volume: float | None = None
    flags: int | None = None

    @classmethod
    def from_mt5(cls, raw: Any, symbol: str = "", offset: int = 0) -> Tick:
        def g(k: str, default: Any = None) -> Any:
            return getattr(raw, k, default)

        t = g("time", 0)
        utc = _ensure_utc(t, offset)
        return cls(
            symbol=symbol or str(g("symbol", "")),
            time=utc,
            bid=float(g("bid", 0) or 0),
            ask=float(g("ask", 0) or 0),
            last=float(g("last", 0) or 0),
            volume=g("volume"),
            flags=g("flags"),
        )


class Bar(BaseModel):
    symbol: str
    timeframe: str
    time: dt.datetime
    open: float
    high: float
    low: float
    close: float
    tick_volume: int = 0
    spread: int = 0
    real_volume: int | None = None

    @classmethod
    def from_mt5(cls, raw: Any, symbol: str = "", timeframe: str = "M15", offset: int = 0) -> Bar:
        # raw may be tuple (time, open, high, low, close, tick_volume, spread, real_volume)
        if isinstance(raw, list | tuple) and len(raw) >= 6:
            t, o, h, lo, c, tv = raw[0], raw[1], raw[2], raw[3], raw[4], raw[5]
            sp = raw[6] if len(raw) > 6 else 0
            rv = raw[7] if len(raw) > 7 else None
            utc = _ensure_utc(t, offset)
            return cls(
                symbol=symbol,
                timeframe=timeframe,
                time=utc,
                open=float(o),
                high=float(h),
                low=float(lo),
                close=float(c),
                tick_volume=int(tv),
                spread=int(sp),
                real_volume=int(rv) if rv is not None else None,
            )

        def g(k: str, default: Any = None) -> Any:
            return getattr(raw, k, default)

        utc2 = _ensure_utc(g("time", 0), offset)
        return cls(
            symbol=symbol,
            timeframe=timeframe,
            time=utc2,
            open=float(g("open", 0) or 0),
            high=float(g("high", 0) or 0),
            low=float(g("low", 0) or 0),
            close=float(g("close", 0) or 0),
            tick_volume=int(g("tick_volume", 0) or 0),
            spread=int(g("spread", 0) or 0),
            real_volume=g("real_volume"),
        )


class Deal(BaseModel):
    ticket: int
    order: int = 0
    time: dt.datetime
    type: Literal["buy", "sell", "balance", "credit", "charge", "correction"] = "buy"
    entry: Literal["in", "out", "inout"] = "in"
    magic: int = 0
    position_id: int = 0
    reason: int | None = None
    commission: float = 0.0
    swap: float = 0.0
    profit: float = 0.0
    symbol: str = ""
    comment: str | None = None
    external_id: str | None = None
    volume: float = 0.0
    price: float = 0.0
    currency: str | None = None

    @classmethod
    def from_mt5(cls, raw: Any, offset: int = 0) -> Deal:
        def g(k: str, default: Any = None) -> Any:
            return getattr(raw, k, default)

        tmap = {0: "buy", 1: "sell", 2: "balance", 3: "credit", 4: "charge", 5: "correction"}
        emap = {0: "in", 1: "out", 2: "inout"}
        utc = _ensure_utc(g("time", 0), offset)
        return cls(
            ticket=int(g("ticket", 0) or 0),
            order=int(g("order", 0) or 0),
            time=utc,
            type=tmap.get(int(g("type", 0) or 0), "buy"),  # type: ignore[arg-type]
            entry=emap.get(int(g("entry", 0) or 0), "in"),  # type: ignore[arg-type]
            magic=int(g("magic", 0) or 0),
            position_id=int(g("position_id", 0) or 0),
            commission=float(g("commission", 0) or 0),
            swap=float(g("swap", 0) or 0),
            profit=float(g("profit", 0) or 0),
            symbol=str(g("symbol", "") or ""),
            comment=g("comment"),
            external_id=g("external_id"),
            volume=float(g("volume", 0) or 0),
            price=float(g("price", 0) or 0),
        )


class Order(BaseModel):
    ticket: int
    time_setup: dt.datetime
    time_done: dt.datetime | None = None
    type: int = 0
    type_filling: int | None = None
    state: int | None = None
    magic: int = 0
    position_id: int | None = None
    position_by_id: int | None = None
    volume_initial: float = 0.0
    volume_current: float = 0.0
    price_open: float = 0.0
    sl: float = 0.0
    tp: float = 0.0
    price_current: float = 0.0
    price_stoptlimit: float | None = None
    symbol: str = ""
    comment: str | None = None
    external_id: str | None = None
    current_price: float | None = None

    @classmethod
    def from_mt5(cls, raw: Any, offset: int = 0) -> Order:
        def g(k: str, default: Any = None) -> Any:
            return getattr(raw, k, default)

        return cls(
            ticket=int(g("ticket", 0) or 0),
            time_setup=_ensure_utc(g("time_setup", 0), offset),
            time_done=_to_utc(g("time_done"), offset),
            type=int(g("type", 0) or 0),
            state=g("state"),
            magic=int(g("magic", 0) or 0),
            volume_initial=float(g("volume_initial", 0) or 0),
            volume_current=float(g("volume_current", 0) or 0),
            price_open=float(g("price_open", 0) or 0),
            sl=float(g("sl", 0) or 0),
            tp=float(g("tp", 0) or 0),
            price_current=float(g("price_current", 0) or 0),
            symbol=str(g("symbol", "") or ""),
            comment=g("comment"),
        )


class PositionInfo(BaseModel):
    ticket: int
    time: dt.datetime
    time_update: dt.datetime
    type: int = 0
    magic: int = 0
    identifier: int | None = None
    volume: float = 0.0
    price_open: float = 0.0
    sl: float = 0.0
    tp: float = 0.0
    price_current: float = 0.0
    swap: float = 0.0
    profit: float = 0.0
    symbol: str = ""
    comment: str | None = None
    external_id: str | None = None

    @classmethod
    def from_mt5(cls, raw: Any, offset: int = 0) -> PositionInfo:
        def g(k: str, default: Any = None) -> Any:
            return getattr(raw, k, default)

        return cls(
            ticket=int(g("ticket", 0) or 0),
            time=_ensure_utc(g("time", 0), offset),
            time_update=_ensure_utc(g("time_update", 0), offset),
            type=int(g("type", 0) or 0),
            magic=int(g("magic", 0) or 0),
            identifier=g("identifier"),
            volume=float(g("volume", 0) or 0),
            price_open=float(g("price_open", 0) or 0),
            sl=float(g("sl", 0) or 0),
            tp=float(g("tp", 0) or 0),
            price_current=float(g("price_current", 0) or 0),
            swap=float(g("swap", 0) or 0),
            profit=float(g("profit", 0) or 0),
            symbol=str(g("symbol", "") or ""),
            comment=g("comment"),
        )


def terminal_info_summary(info: TerminalInfo | None) -> str:
    if info is None:
        return "Terminal: not connected"
    return f"Terminal build {info.build} connected={info.connected} algo={info.allow_auto_trading}"


def account_info_summary(info: AccountInfo | None) -> str:
    if info is None:
        return "Account: not connected"
    return f"Account {info.login} ({info.account_type}) {info.company} {info.server} bal={info.balance}"
