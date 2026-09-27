"""Auto-detect terminal64.exe installations."""

from __future__ import annotations

import pathlib
import platform
from dataclasses import dataclass


@dataclass
class Terminal:
    path: pathlib.Path
    broker_name: str
    data_path: pathlib.Path | None = None


def find_terminals() -> list[Terminal]:
    """Search for MT5 terminals. Returns [] on non-Windows."""
    if platform.system() != "Windows":
        return []

    found: list[Terminal] = []
    seen: set[str] = set()

    def _add(path: pathlib.Path, broker: str = "", data_path: pathlib.Path | None = None) -> None:
        key = str(path).lower()
        if key in seen or not path.exists():
            return
        seen.add(key)
        # infer broker from path
        if not broker:
            parts = path.parts
            # e.g. C:\Program Files\MetaQuotes\MetaTrader 5\terminal64.exe
            # or C:\Program Files\IC Markets\terminal64.exe
            if len(parts) >= 3:
                broker = parts[-2] if parts[-2].lower() != "metatrader 5" else parts[-3] if len(parts) >= 4 else "MetaTrader 5"
        found.append(Terminal(path=path, broker_name=broker, data_path=data_path))

    # 1. Common Program Files
    for base in [pathlib.Path(r"C:\Program Files"), pathlib.Path(r"C:\Program Files (x86)")]:
        if base.exists():
            for p in base.rglob("terminal64.exe"):
                _add(p)

    # 2. AppData MetaQuotes
    import os

    appdata = os.environ.get("APPDATA", "")
    if appdata:
        mq = pathlib.Path(appdata) / "MetaQuotes" / "Terminal"
        if mq.exists():
            for child in mq.iterdir():
                # look for terminal install inside?
                for p in child.rglob("terminal64.exe"):
                    _add(p, data_path=child)

    # 3. Registry (Windows-only; non-Windows silently skips)
    try:
        import winreg  # type: ignore[import-not-found]

        # mypy doesn't have stubs for winreg on non-Windows dev machines;
        # access via getattr() so the static type checker doesn't complain.
        hklm = getattr(winreg, "HKEY_LOCAL_MACHINE", None)
        hkcu = getattr(winreg, "HKEY_CURRENT_USER", None)
        wow32 = getattr(winreg, "KEY_WOW64_32KEY", 0)
        wow64 = getattr(winreg, "KEY_WOW64_64KEY", 0)
        key_read = getattr(winreg, "KEY_READ", 0)
        if hklm is not None and hkcu is not None:
            for hive in [hklm, hkcu]:
                for access in [0, wow32, wow64]:
                    try:
                        with winreg.OpenKey(  # type: ignore[attr-defined]
                            hive, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", 0, key_read | access
                        ) as key:
                            info = winreg.QueryInfoKey(key)  # type: ignore[attr-defined]
                            for i in range(info[0]):
                                try:
                                    sub = winreg.EnumKey(key, i)  # type: ignore[attr-defined]
                                    with winreg.OpenKey(key, sub) as sk:  # type: ignore[attr-defined]
                                        try:
                                            disp = winreg.QueryValueEx(sk, "DisplayName")[0]  # type: ignore[attr-defined]
                                            if "metatrader 5" in str(disp).lower():
                                                loc = winreg.QueryValueEx(sk, "InstallLocation")[0]  # type: ignore[attr-defined]
                                                cand = pathlib.Path(str(loc)) / "terminal64.exe"
                                                _add(cand, broker=str(disp))
                                        except FileNotFoundError:
                                            continue
                                except OSError:
                                    continue
                    except OSError:
                        continue
    except ImportError:
        pass

    # 4. Running processes via psutil
    try:
        import psutil  # type: ignore[import-not-found]

        for proc in psutil.process_iter(["exe", "name"]):
            try:
                name = (proc.info.get("name") or "").lower()
                if name == "terminal64.exe":
                    exe = proc.info.get("exe")
                    if exe:
                        _add(pathlib.Path(exe))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except ImportError:
        pass

    return found
