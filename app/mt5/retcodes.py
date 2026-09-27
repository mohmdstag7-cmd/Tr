"""MT5 trade retcodes — constants and helpers."""

from __future__ import annotations

# Real MT5 / MQL5 trade return codes (TRADE_RETCODE_*)
RETCODE_DONE = 10009
RETCODE_DONE_PARTIAL = 10010
RETCODE_PLACED = 10008
RETCODE_REQUOTE = 10004
RETCODE_REJECT = 10006
RETCODE_CANCEL = 10007
RETCODE_ERROR = 10011
RETCODE_TIMEOUT = 10012
RETCODE_INVALID = 10013
RETCODE_INVALID_VOLUME = 10014
RETCODE_INVALID_PRICE = 10015
RETCODE_INVALID_STOPS = 10016
RETCODE_TRADE_DISABLED = 10017
RETCODE_MARKET_CLOSED = 10018
RETCODE_NO_MONEY = 10019
RETCODE_PRICE_CHANGED = 10020
RETCODE_PRICE_OFF = 10021
RETCODE_INVALID_EXPIRATION = 10022
RETCODE_ORDER_CHANGED = 10023
RETCODE_TOO_MANY_REQUESTS = 10024
RETCODE_NO_CHANGES = 10025
RETCODE_SERVER_DISABLES_AT = 10026
RETCODE_CLIENT_DISABLES_AT = 10027
RETCODE_LOCKED = 10028
RETCODE_FROZEN = 10029
RETCODE_INVALID_FILL = 10030
RETCODE_CONNECTION = 10031
RETCODE_ONLY_REAL = 10032
RETCODE_LIMIT_ORDERS = 10033
RETCODE_LIMIT_VOLUME = 10034
RETCODE_INVALID_ORDER = 10035
RETCODE_POSITION_CLOSED = 10036
RETCODE_INVALID_CLOSE_VOLUME = 10038
RETCODE_CLOSE_ORDER_EXIST = 10039
RETCODE_LIMIT_POSITIONS = 10040
RETCODE_REJECT_CANCEL = 10041
RETCODE_LONG_ONLY = 10042
RETCODE_SHORT_ONLY = 10043
RETCODE_CLOSE_ONLY = 10044
RETCODE_FIFO_CLOSE = 10045

# Aliases required by spec (spec uses slightly different numbers for some)
RETCODE_CONNECTION_LOST = RETCODE_CONNECTION
# Spec explicitly says 10027 is TRADE_DISABLED, 10008 is TIMEOUT/CONNECTION_LOST
# We keep both mappings for compatibility
_SPEC_TRADE_DISABLED = 10027
_SPEC_TIMEOUT = 10008

_RETCODES: dict[int, str] = {
    10004: "Requote",
    10006: "Request rejected",
    10007: "Request canceled by trader",
    10008: "Order placed (placed)",
    10009: "Request completed",
    10010: "Only part of the request was completed",
    10011: "Request processing error",
    10012: "Request timed out",
    10013: "Invalid request",
    10014: "Invalid volume",
    10015: "Invalid price",
    10016: "Invalid stops",
    10017: "Trade disabled",
    10018: "Market closed",
    10019: "Not enough money",
    10020: "Prices changed",
    10021: "Off quotes",
    10022: "Invalid expiration",
    10023: "Order state changed",
    10024: "Too many requests",
    10025: "No changes",
    10026: "Autotrading disabled by server",
    10027: "Autotrading disabled by client",
    10028: "Order locked",
    10029: "Order frozen",
    10030: "Invalid fill mode",
    10031: "No connection",
    10032: "Only real accounts allowed",
    10033: "Limit orders reached",
    10034: "Limit volume reached",
    10035: "Invalid order",
    10036: "Position closed",
    10038: "Invalid close volume",
    10039: "Close order already exists",
    10040: "Limit positions reached",
    10041: "Reject cancel",
    10042: "Long only",
    10043: "Short only",
    10044: "Close only",
    10045: "FIFO close",
}

# Retcodes safe to retry (transient market conditions)
RETRYABLE_RETCODES: set[int] = {
    RETCODE_REQUOTE,  # 10004
    RETCODE_PRICE_CHANGED,  # 10020
    RETCODE_PRICE_OFF,  # 10021
    RETCODE_TIMEOUT,  # 10012
    10008,  # spec says 10008 is timeout/connection_lost — treat as retryable
    RETCODE_CONNECTION,  # 10031
}

# Retcodes that are terminal — never retry
TERMINAL_RETCODES: set[int] = {
    RETCODE_INVALID_STOPS,  # 10016
    RETCODE_NO_MONEY,  # 10019
    RETCODE_TRADE_DISABLED,  # 10017
    _SPEC_TRADE_DISABLED,  # 10027 spec alias
    RETCODE_MARKET_CLOSED,  # 10018
    RETCODE_INVALID_VOLUME,  # 10014
    RETCODE_INVALID_PRICE,  # 10015
    RETCODE_INVALID_EXPIRATION,  # 10022
    RETCODE_INVALID_ORDER,  # 10035
    RETCODE_POSITION_CLOSED,  # 10036
}


def retcode_text(retcode: int) -> str:
    """Return friendly description for a retcode."""
    return _RETCODES.get(retcode, f"Unknown retcode {retcode}")


def should_retry(retcode: int) -> bool:
    """Return True if retcode is in retryable set."""
    return retcode in RETRYABLE_RETCODES
