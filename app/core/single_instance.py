"""Cross-process single-instance lock per profile.

Choice: file-based locking.
- On Windows: ``msvcrt.locking`` on a file in ``%LOCALAPPDATA%\\MT5TradingWorkstation\\``.
- On POSIX: ``fcntl.flock`` on a file in ``~/.mt5tw/``.

This avoids requiring a fixed TCP port and works per-profile by using
distinct lock files. The lock is held for the lifetime of the context
manager.
"""

from __future__ import annotations

import io
import os
import sys
from pathlib import Path
from types import TracebackType

from loguru import logger


class InstanceAlreadyRunningError(RuntimeError):
    """Raised when another instance already holds the lock."""


def _lock_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA")
        if base:
            return Path(base) / "MT5TradingWorkstation"
        return Path.home() / "AppData" / "Local" / "MT5TradingWorkstation"
    return Path.home() / ".mt5tw"


class SingleInstance:
    """Single-instance guard for a given profile name."""

    def __init__(self, profile_name: str) -> None:
        self.profile_name = profile_name
        safe = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in profile_name)
        self._lock_path = _lock_dir() / f"mt5tw-{safe}.lock"
        self._fh: io.TextIOWrapper | None = None

    @property
    def lock_path(self) -> Path:
        """Path to the lock file."""
        return self._lock_path

    def __enter__(self) -> SingleInstance:
        self._lock_path.parent.mkdir(parents=True, exist_ok=True)
        # Open file for locking
        fh = open(self._lock_path, "a+", encoding="utf-8")  # noqa: SIM115
        try:
            if sys.platform == "win32":
                import msvcrt

                try:
                    # Lock first byte non-blocking
                    fh.seek(0)
                    msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
                except OSError as exc:
                    fh.close()
                    msg = f"Another instance is already running for profile '{self.profile_name}'"
                    raise InstanceAlreadyRunningError(msg) from exc
            else:
                import fcntl

                try:
                    fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except OSError as exc:
                    fh.close()
                    msg = f"Another instance is already running for profile '{self.profile_name}'"
                    raise InstanceAlreadyRunningError(msg) from exc
            # Write pid for diagnostics
            fh.seek(0)
            fh.truncate(0)
            fh.write(str(os.getpid()))
            fh.flush()
            self._fh = fh
            logger.info(f"Acquired single-instance lock for profile '{self.profile_name}' at {self._lock_path}")
            return self
        except Exception:
            # Ensure file is closed on unexpected error
            try:
                fh.close()
            except Exception:
                pass
            raise

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        fh = self._fh
        if fh is None:
            return
        try:
            if sys.platform == "win32":
                import msvcrt

                try:
                    fh.seek(0)
                    msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
                except OSError:
                    logger.warning("Failed to unlock file on Windows")
            else:
                import fcntl

                try:
                    fcntl.flock(fh, fcntl.LOCK_UN)
                except OSError:
                    logger.warning("Failed to unlock file on POSIX")
            fh.close()
            logger.info(f"Released single-instance lock for profile '{self.profile_name}'")
        except Exception:
            logger.exception("Error releasing single-instance lock")
        finally:
            self._fh = None
