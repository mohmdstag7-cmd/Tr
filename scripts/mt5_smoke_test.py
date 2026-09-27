"""Standalone MT5 smoke test CLI script."""

from __future__ import annotations

import sys


def main() -> int:
    """Run MT5 smoke test. Returns 0 on success, 1 on failure."""
    try:
        import MetaTrader5 as mt5  # noqa: WPS433
    except ImportError:
        print("MetaTrader5 not installed")
        return 1

    try:
        initialized = mt5.initialize()
        if not initialized:
            error = mt5.last_error()
            print(f"MT5 initialize failed: {error}")
            return 1

        print("MT5 initialized successfully")

        account_info = mt5.account_info()
        if account_info is not None:
            print(f"Broker: {account_info.server}")
            print(f"Login: {account_info.login}")
            print(f"Balance: {account_info.balance}")
        else:
            print("No account info available")

        symbols = mt5.symbols_get()
        if symbols is not None:
            count = min(10, len(symbols))
            print(f"Symbols ({count}/{len(symbols)}):")
            for sym in symbols[:10]:
                print(f"  {sym.name}")
        else:
            print("symbols_get returned None")

        return 0

    finally:
        try:
            mt5.shutdown()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
