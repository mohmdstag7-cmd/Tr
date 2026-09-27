"""Installer launch and rollback helpers."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

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
        """Schedule relaunch of the newly installed exe and exit."""
        # The installer overwrites the same install dir; we just exit.
        # On Windows the installer will handle file replacement on next launch.
        # For portable mode, the exe is in the same dir as current executable.
        Path(sys.executable)
        # If running as python script (dev), just exit
        log.info("Exiting for installer to complete; app will be relaunched by installer")
        # Give installer a moment to start
        try:
            # On Windows, we could schedule a relaunch via Popen + delay
            # For now, simply exit — Inno Setup can launch the app if configured
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
