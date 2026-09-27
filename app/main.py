"""Composition root for MT5 Trading Workstation."""

from __future__ import annotations

import argparse
import sys

from loguru import logger

__app_name__ = "MT5 Trading Workstation"
__version__ = "0.1.0"


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="mt5tw",
        description="MT5 Trading Workstation",
    )
    parser.add_argument(
        "--self-check",
        action="store_true",
        help="Run self-check and exit",
    )
    parser.add_argument(
        "--mt5-smoke-test",
        action="store_true",
        help="Run MT5 smoke test and exit",
    )
    parser.add_argument(
        "--mt5-trade-test",
        action="store_true",
        help="Run MT5 trade test and exit",
    )
    parser.add_argument(
        "--profile",
        type=str,
        default=None,
        help="Profile name to use",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print version and exit",
    )
    return parser.parse_args(argv)


def _handle_version() -> int:
    print(f"{__app_name__} {__version__}")
    return 0


def _handle_self_check() -> int:
    print(f"{__app_name__} {__version__}")
    try:
        import MetaTrader5 as mt5  # type: ignore[import-untyped]

        ver = getattr(mt5, "__version__", getattr(mt5, "version", lambda: "unknown"))
        if callable(ver):
            try:
                ver = ver()
            except Exception:
                ver = "unknown"
        print(f"MetaTrader5 import OK — version: {ver}")
        return 0
    except ImportError as exc:
        print(f"MetaTrader5 import FAILED: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"MetaTrader5 import FAILED: {exc}", file=sys.stderr)
        return 1


def _handle_mt5_smoke_test() -> int:
    print(f"{__app_name__} {__version__} — MT5 smoke test")
    try:
        import MetaTrader5 as mt5  # type: ignore[import-untyped]
    except ImportError as exc:
        print(f"MetaTrader5 import FAILED: {exc}", file=sys.stderr)
        return 1
    try:
        initialized = mt5.initialize()
        print(f"mt5.initialize() -> {initialized}")
        if not initialized:
            err = mt5.last_error()
            print(f"initialize failed: {err}", file=sys.stderr)
            return 1
        info = mt5.terminal_info()
        print(f"terminal_info: {info}")
        ver = mt5.version()
        print(f"mt5.version(): {ver}")
        mt5.shutdown()
        print("MT5 smoke test PASSED")
        return 0
    except Exception as exc:
        print(f"MT5 smoke test FAILED: {exc}", file=sys.stderr)
        logger.exception("MT5 smoke test failed")
        try:
            import MetaTrader5 as mt5  # type: ignore[import-untyped]

            mt5.shutdown()
        except Exception:
            pass
        return 1


def _handle_mt5_trade_test() -> int:
    print(f"{__app_name__} {__version__} — MT5 trade test")
    try:
        import MetaTrader5 as mt5  # type: ignore[import-untyped]
    except ImportError as exc:
        print(f"MetaTrader5 import FAILED: {exc}", file=sys.stderr)
        return 1
    try:
        initialized = mt5.initialize()
        print(f"mt5.initialize() -> {initialized}")
        if not initialized:
            err = mt5.last_error()
            print(f"initialize failed: {err}", file=sys.stderr)
            return 1
        account = mt5.account_info()
        print(f"account_info: {account}")
        symbols = mt5.symbols_get()
        count = len(symbols) if symbols is not None else 0
        print(f"symbols_get count: {count}")
        mt5.shutdown()
        print("MT5 trade test PASSED (no order sent)")
        return 0
    except Exception as exc:
        print(f"MT5 trade test FAILED: {exc}", file=sys.stderr)
        logger.exception("MT5 trade test failed")
        try:
            import MetaTrader5 as mt5  # type: ignore[import-untyped]

            mt5.shutdown()
        except Exception:
            pass
        return 1


def main(argv: list[str] | None = None) -> None:
    """Application entry point."""
    args = _parse_args(argv)

    if args.version:
        sys.exit(_handle_version())

    if args.self_check:
        sys.exit(_handle_self_check())

    if args.mt5_smoke_test:
        sys.exit(_handle_mt5_smoke_test())

    if args.mt5_trade_test:
        sys.exit(_handle_mt5_trade_test())

    # Normal GUI startup
    from PySide6.QtWidgets import QApplication, QLabel, QMainWindow

    from app.core.config import load_settings
    from app.ui.theme.qss import generate_qss
    from app.ui.theme.tokens import get_tokens

    app = QApplication(sys.argv)
    app.setApplicationName(__app_name__)
    app.setApplicationVersion(__version__)

    settings = load_settings()
    tokens = get_tokens(settings.theme)
    app.setStyleSheet(generate_qss(tokens))

    # Try to load the real MainWindow, fall back to a minimal placeholder
    try:
        from app.ui.main_window import MainWindow as RealMainWindow  # type: ignore[import-untyped]

        window_cls: type[QMainWindow] = RealMainWindow
    except ImportError:

        class FallbackMainWindow(QMainWindow):
            def __init__(self) -> None:
                super().__init__()
                self.setWindowTitle(__app_name__)
                self.setMinimumSize(1100, 700)
                label = QLabel("MT5 Trading Workstation — Foundation")
                label.setStyleSheet("padding: 24px; font-size: 16px;")
                self.setCentralWidget(label)

        window_cls = FallbackMainWindow

    lock = None
    if args.profile is not None:
        from app.core.single_instance import InstanceAlreadyRunningError, SingleInstance

        try:
            lock = SingleInstance(profile_name=str(args.profile))
            lock.__enter__()
        except InstanceAlreadyRunningError as exc:
            logger.error(str(exc))
            print(str(exc), file=sys.stderr)
            sys.exit(1)

    window = window_cls()
    window.show()

    exit_code = app.exec()

    if lock is not None:
        lock.__exit__(None, None, None)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
