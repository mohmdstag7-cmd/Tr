"""Installer launch and rollback helpers."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from loguru import logger

log = logger.bind(category="update") if hasattr(logger, "bind") else logger  # type: ignore[attr-defined]


def _get_data_dir() -> Path:
    """Return writable user data dir for storing previous installer."""
    # Try platformdirs if available
    try:
        from platformdirs import user_data_dir  # type: ignore[import-not-found]

        return Path(user_data_dir("MT5TradingWorkstation", "MT5TradingWorkstation"))
    except ImportError:
        pass
    # Fallback: QStandardPaths via env or home
    base = Path.home() / ".mt5_trading_workstation"
    # Allow tests to override via env
    env_dir = os.environ.get("MT5_DATA_DIR")
    if env_dir:
        return Path(env_dir)
    return base


class Installer:
    """Launch Inno Setup installer and handle rollback."""

    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = data_dir or _get_data_dir()

    @property
    def previous_installer_path(self) -> Path:
        return self.data_dir / "previous_installer.exe"

    def keep_previous_installer(self, installer_path: Path) -> Path:
        """Copy *installer_path* to ``previous_installer.exe`` for rollback."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        dest = self.previous_installer_path
        try:
            shutil.copy2(installer_path, dest)
            log.info(f"Saved previous installer to {dest}")
        except OSError as exc:
            log.warning(f"Failed to save previous installer: {exc}")
            raise
        return dest

    def launch_silent_install(self, installer_path: Path) -> int:
        """Launch Inno Setup installer silently. Returns PID."""
        if not installer_path.exists():
            raise FileNotFoundError(f"Installer not found: {installer_path}")
        # Keep a copy for rollback before launching
        try:
            self.keep_previous_installer(installer_path)
        except OSError:
            # Non-fatal — continue with install
            pass

        args = [
            str(installer_path),
            "/VERYSILENT",
            "/SUPPRESSMSGS",
            "/NORESTART",
        ]
        log.info(f"Launching installer: {args}")
        # Use Popen so the installer outlives the current process
        proc = subprocess.Popen(args)  # noqa: S603
        return proc.pid

    def relaunch_after_install(self) -> None:
        """Schedule relaunch of the newly installed exe and exit.

        Per audit (Area 3, step 13): the previous implementation just called
        ``sys.exit(0)`` without scheduling a relaunch. With a REAL Inno Setup
        installer (which has ``[Run] postinstall`` in installer.iss), the
        installer itself will relaunch the app. But as a safety net — in case
        the installer's postinstall is skipped (e.g. ``/VERYSILENT`` without
        ``/NORESTART``) — we also schedule a delayed relaunch of our own exe.

        The delay (3 seconds) gives the installer time to finish writing files
        before we try to launch the new version.
        """
        import threading

        exe_path = Path(sys.executable)

        def _delayed_relaunch() -> None:
            """Wait 3s then relaunch the app (in a daemon thread)."""
            import time

            time.sleep(3.0)
            try:
                # On Windows, the installer may have just replaced our exe.
                # subprocess.Popen with creationflags=DETACHED_PROCESS ensures
                # the new process survives our own exit.
                kwargs: dict[str, Any] = {}
                if sys.platform == "win32":
                    kwargs["creationflags"] = 0x00000008  # DETACHED_PROCESS
                subprocess.Popen([str(exe_path)], **kwargs)  # noqa: S603
                log.info(f"Relaunched {exe_path} after install")
            except Exception as exc:  # noqa: BLE001
                log.warning(f"Delayed relaunch failed: {exc}")

        # Start the relaunch in a daemon thread so it survives our exit.
        t = threading.Thread(target=_delayed_relaunch, daemon=True)
        t.start()
        log.info("Exiting for installer to complete; app will be relaunched in 3s")
        try:
            sys.exit(0)
        except SystemExit:
            raise
        except Exception as exc:  # noqa: BLE001
            log.warning(f"relaunch_after_install failed: {exc}")
            sys.exit(0)

    def rollback_to_previous(self) -> bool:
        """If a previous installer exists, launch it silently and exit."""
        prev = self.previous_installer_path
        if not prev.exists():
            log.warning("No previous installer found for rollback")
            return False
        log.info(f"Rolling back via {prev}")
        try:
            proc = subprocess.Popen(  # noqa: S603
                [str(prev), "/VERYSILENT", "/SUPPRESSMSGS", "/NORESTART"]
            )
            log.info(f"Rollback installer launched pid={proc.pid}")
            sys.exit(0)
        except SystemExit:
            raise
        except Exception as exc:  # noqa: BLE001
            log.error(f"Rollback failed: {exc}")
            return False
        return True
