"""High-level facade for the auto-updater."""

from __future__ import annotations

from pathlib import Path

from loguru import logger
from PySide6.QtCore import QObject, QThread, Signal, Slot

from app.__version__ import __version__ as current_version
from app.core.config import AppSettings
from app.updater.models import UpdateInfo, UpdateStatus
from app.updater.update_worker import UpdateWorker

log = logger.bind(category="update") if hasattr(logger, "bind") else logger  # type: ignore[attr-defined]


class UpdateChecker(QObject):
    """Facade that owns the worker thread and exposes high-level signals."""

    update_available = Signal(object)  # UpdateInfo
    no_update = Signal()
    error = Signal(str)
    status_changed = Signal(object)  # UpdateStatus

    def __init__(
        self,
        parent: QObject | None = None,
        repo: str | None = None,
        settings: AppSettings | None = None,
    ) -> None:
        super().__init__(parent)
        self._settings = settings or AppSettings()
        self._repo = repo or self._settings.update_repo
        self._thread: QThread | None = None
        self._worker: UpdateWorker | None = None
        self._paused = False
        self._current_status = UpdateStatus(state="idle", current_version=current_version)

    # ------------------------------------------------------------------ public
    def pause_updates(self, paused: bool) -> None:
        self._paused = paused
        if paused:
            self.status_changed.emit(UpdateStatus(state="paused", current_version=current_version))

    def start_check(self) -> None:
        """Start an async update check (non-blocking)."""
        if self._paused:
            log.info("Updates paused — skipping check")
            self.status_changed.emit(UpdateStatus(state="paused", current_version=current_version))
            return
        if self._settings.pause_updates_during_auto:
            # Phase 1: no positions/Auto mode yet — gate is a no-op but we respect the setting
            # If Auto mode were running, we would pause here.
            pass

        # Clean up previous thread if any
        self._cleanup_thread()

        self._thread = QThread(self)
        self._worker = UpdateWorker(repo=self._repo)
        self._worker.moveToThread(self._thread)

        # Wire worker signals to facade signals
        self._worker.status_changed.connect(self._on_status_changed)
        self._worker.error.connect(self.error.emit)
        self._worker.ready_to_install.connect(self._on_ready_to_install)

        # Thread start -> worker check
        self._thread.started.connect(self._worker.check_for_updates)
        # Auto-cleanup when thread finishes
        self._thread.finished.connect(self._on_thread_finished)

        self._thread.start()

    def download_and_install(self, update_info: UpdateInfo) -> None:
        """Download the installer for *update_info* in the existing worker thread."""
        if self._worker is None or self._thread is None:
            # No active thread — create one for download
            self._cleanup_thread()
            self._thread = QThread(self)
            self._worker = UpdateWorker(repo=self._repo)
            self._worker.moveToThread(self._thread)
            self._worker.status_changed.connect(self._on_status_changed)
            self._worker.error.connect(self.error.emit)
            self._worker.ready_to_install.connect(self._on_ready_to_install)
            self._thread.finished.connect(self._on_thread_finished)
            self._thread.start()
            # Queue download after thread starts
            self._thread.started.connect(
                lambda: self._worker.download_and_verify(update_info)  # type: ignore[union-attr]
            )
            # If thread already started, call directly via queued connection
            if self._thread.isRunning():
                # Use singleShot to queue
                from PySide6.QtCore import QTimer

                QTimer.singleShot(0, lambda: self._worker.download_and_verify(update_info))  # type: ignore[union-attr]
        else:
            # Worker already in thread — invoke via queued slot.
            from PySide6.QtCore import QMetaObject, Qt

            try:
                QMetaObject.invokeMethod(  # type: ignore[call-overload]
                    self._worker,
                    "download_and_verify",
                    Qt.ConnectionType.QueuedConnection,
                    update_info,
                )
            except TypeError:
                QTimer.singleShot(0, lambda ui=update_info: self._worker.download_and_verify(ui))  # type: ignore[union-attr,misc]

    def install(self, installer_path: Path) -> None:
        """Launch installer and relaunch."""
        if self._worker is None:
            from app.updater.installer import Installer

            Installer().launch_silent_install(installer_path)
            Installer().relaunch_after_install()
            return
        # Use QMetaObject.invokeMethod to run on the worker thread.
        # Wrapped in try/except because the PySide6 type stubs are very strict
        # about argument types here and we just want the runtime behavior.
        from PySide6.QtCore import QMetaObject, Qt

        try:
            QMetaObject.invokeMethod(  # type: ignore[call-overload]
                self._worker,
                "install_and_relaunch",
                Qt.ConnectionType.QueuedConnection,
                installer_path,
            )
        except TypeError:
            # Fallback: call directly on the main thread (acceptable for Phase 1).
            self._worker.install_and_relaunch(installer_path)

    # ----------------------------------------------------------------- private
    @Slot(object)
    def _on_status_changed(self, status: UpdateStatus) -> None:
        self._current_status = status
        self.status_changed.emit(status)
        if status.state == "update_available" and status.update_info is not None:
            # Never auto-download major/breaking without confirmation — just notify
            self.update_available.emit(status.update_info)
        elif status.state == "no_update":
            self.no_update.emit()
        elif status.state == "error" and status.error_message:
            self.error.emit(status.error_message)

    @Slot(object, object)
    def _on_ready_to_install(self, info: UpdateInfo, path: Path) -> None:
        # Re-emit as status_changed already covers it; no extra signal needed
        log.info(f"Ready to install v{info.version} at {path}")

    @Slot()
    def _on_thread_finished(self) -> None:
        log.info("Update worker thread finished")

    def _cleanup_thread(self) -> None:
        if self._thread is not None:
            try:
                self._thread.quit()
                self._thread.wait(2000)
            except RuntimeError:
                pass
            self._thread = None
            self._worker = None

    def shutdown(self) -> None:
        self._cleanup_thread()
