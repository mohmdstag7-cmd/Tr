"""Wrapper script for PyInstaller build."""

from __future__ import annotations

import re
import sys
from pathlib import Path


def get_version() -> str:
    """Read version from app/__version__.py."""
    version_file = Path(__file__).resolve().parent.parent / "app" / "__version__.py"
    text = version_file.read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', text)
    if match is None:
        raise RuntimeError("Could not find __version__ in app/__version__.py")
    return match.group(1)


def main() -> None:
    """Build the application with PyInstaller."""
    version = get_version()
    print(f"Building MT5 Trading Workstation v{version}...")

    entry_point = str(Path(__file__).resolve().parent.parent / "app" / "main.py")

    hidden_imports = [
        "MetaTrader5",
        "PySide6.QtWidgets",
        "PySide6.QtCore",
        "PySide6.QtGui",
        "pyqtgraph",
    ]

    args: list[str] = [
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name",
        "MT5TradingWorkstation",
        "--collect-all",
        "MetaTrader5",
        "--collect-all",
        "PySide6",
        "--collect-all",
        "pyqtgraph",
    ]

    for imp in hidden_imports:
        args.extend(["--hidden-import", imp])

    args.append(entry_point)

    try:
        import PyInstaller.__main__  # noqa: WPS433

        PyInstaller.__main__.run(args)
    except ImportError:
        print("PyInstaller not installed. Install with: pip install pyinstaller", file=sys.stderr)
        sys.exit(1)

    dist_path = Path(__file__).resolve().parent.parent / "dist" / "MT5TradingWorkstation"
    print(f"Build complete: {dist_path}/")
    print(str(dist_path))


if __name__ == "__main__":
    main()
