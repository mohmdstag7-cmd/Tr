"""QThread worker for update checks and downloads."""

from __future__ import annotations

import tempfile
from pathlib import Path

from loguru import logger
from PySide6.QtCore import QObject, Signal, Slot

from app.__version__ import __version__ as current_version
from app.updater.downloader import ChecksumMismatchError, Downloader
from app.updater.installer import Installer
from app.updater.models import SemVer, UpdateInfo, UpdateStatus
from app.updater.release_feed import ReleaseFeed, ReleaseFeedError

log = logger.bind(category="update") if hasattr(logger, "bind") else logger  # type: ignore[attr-defined]


class UpdateWorker(QObject):
    """Worker that runs network/file operations off the UI thread.

    This object is intended to be moved to a ``QThread``. All public methods
    are slots that emit signals to communicate back to the UI thread.
    """

    status_changed = Signal(object)  # UpdateStatus
    download_progress = Signal(float)  # 0..1
    error = Signal(str)
    ready_to_install = Signal(object, object)  # UpdateInfo, Path

    def __init__(
        self,
        repo: str = "mohmdstag7-cmd/Tr",
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.repo = repo
        self._downloader = Downloader()
        self._installer = Installer()
        self._temp_dir: Path | None = None

    @Slot()
    def check_for_updates(self) -> None:
        """Fetch latest release and compare versions."""
        log.info("Checking for updates...")
        self.status_changed.emit(UpdateStatus(state="checking", current_version=current_version))
        try:
            feed = ReleaseFeed(repo=self.repo)
            info = feed.fetch_latest_sync()
            latest = SemVer.from_string(info.version)
            current = SemVer.from_string(current_version)
            if latest > current:
                log.info(f"Update available: {current_version} -> {info.version}")
                self.status_changed.emit(
                    UpdateStatus(
                        state="update_available",
                        current_version=current_version,
                        latest_version=info.version,
                        update_info=info,
                    )
                )
            else:
                log.info(f"No update: current {current_version} >= latest {info.version}")
                self.status_changed.emit(
                    UpdateStatus(
                        state="no_update",
                        current_version=current_version,
                        latest_version=info.version,
                        update_info=info,
                    )
                )
        except ReleaseFeedError as exc:
            msg = str(exc)
            log.warning(f"Update check failed: {msg}")
            self.status_changed.emit(
                UpdateStatus(
                    state="error",
                    current_version=current_version,
                    error_message=msg,
                )
            )
            self.error.emit(msg)
        except Exception as exc:  # noqa: BLE001
            msg = f"Unexpected error during update check: {exc}"
            log.error(msg)
            self.status_changed.emit(
                UpdateStatus(
                    state="error",
                    current_version=current_version,
                    error_message=msg,
                )
            )
            self.error.emit(msg)

    @Slot(object)
    def download_and_verify(self, update_info: UpdateInfo) -> None:
        """Download installer and verify SHA-256."""
        log.info(f"Downloading installer for v{update_info.version}")
        self.status_changed.emit(
            UpdateStatus(
                state="downloading",
                current_version=current_version,
                latest_version=update_info.version,
                update_info=update_info,
                download_progress_pct=0.0,
            )
        )

        def _on_progress(p: float) -> None:
            self.download_progress.emit(p)
            self.status_changed.emit(
                UpdateStatus(
                    state="downloading",
                    current_version=current_version,
                    latest_version=update_info.version,
                    update_info=update_info,
                    download_progress_pct=p * 100.0,
                )
            )

        try:
            tmp = Path(tempfile.mkdtemp(prefix="mt5_update_"))
            self._temp_dir = tmp
            dest = tmp / f"MT5TradingWorkstation-Setup-{update_info.version}.exe"

            self._downloader.download_sync(
                url=update_info.installer_url,
                dest_path=dest,
                expected_sha256=update_info.installer_sha256,
                progress_callback=_on_progress,
            )

            # Verifying state
            self.status_changed.emit(
                UpdateStatus(
                    state="verifying",
                    current_version=current_version,
                    latest_version=update_info.version,
                    update_info=update_info,
                    download_progress_pct=100.0,
                )
            )

            # Already verified inside downloader; emit ready
            self.status_changed.emit(
                UpdateStatus(
                    state="ready_to_install",
                    current_version=current_version,
                    latest_version=update_info.version,
                    update_info=update_info,
                    download_progress_pct=100.0,
                )
            )
            self.ready_to_install.emit(update_info, dest)
            log.info(f"Ready to install {dest}")

        except ChecksumMismatchError as exc:
            msg = f"Checksum mismatch: expected {exc.expected}, got {exc.actual}"
            log.error(msg)
            self.status_changed.emit(
                UpdateStatus(
                    state="error",
                    current_version=current_version,
                    latest_version=update_info.version,
                    update_info=update_info,
                    error_message=msg,
                )
            )
            self.error.emit(msg)
        except Exception as exc:  # noqa: BLE001
            msg = f"Download failed: {exc}"
            log.error(msg)
            self.status_changed.emit(
                UpdateStatus(
                    state="error",
                    current_version=current_version,
                    latest_version=update_info.version,
                    update_info=update_info,
                    error_message=msg,
                )
            )
            self.error.emit(msg)

    @Slot(object)
    def install_and_relaunch(self, installer_path: Path) -> None:
        """Launch installer silently and exit."""
        log.info(f"Installing from {installer_path}")
        self.status_changed.emit(
            UpdateStatus(
                state="installing",
                current_version=current_version,
                latest_version=None,
                download_progress_pct=100.0,
            )
        )
        try:
            pid = self._installer.launch_silent_install(installer_path)
            log.info(f"Installer launched pid={pid}, exiting app")
            self._installer.relaunch_after_install()
        except Exception as exc:  # noqa: BLE001
            msg = f"Failed to launch installer: {exc}"
            log.error(msg)
            self.status_changed.emit(
                UpdateStatus(
                    state="error",
                    current_version=current_version,
                    error_message=msg,
                )
            )
            self.error.emit(msg)
