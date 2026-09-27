"""Modal dialog for downloading and installing updates."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QProgressBar,
    QVBoxLayout,
)

from app.updater.models import UpdateInfo, UpdateStatus
from app.updater.update_worker import UpdateWorker


class UpdateDialog(QDialog):
    """Modal dialog showing download progress and install action."""

    install_requested = Signal(object)  # Path

    def __init__(
        self,
        update_info: UpdateInfo,
        worker: UpdateWorker | None = None,
        parent=None,  # type: ignore[no-untyped-def]
    ) -> None:
        super().__init__(parent)
        self.setObjectName("UpdateDialog")
        self.setWindowTitle(f"Update to v{update_info.version}")
        self.setModal(True)
        self.resize(480, 220)

        self._update_info = update_info
        self._worker = worker
        self._installer_path: Path | None = None
        self._is_breaking = update_info.is_breaking

        # Widgets
        self._step_label = QLabel("Preparing download...", self)
        self._progress = QProgressBar(self)
        self._progress.setRange(0, 100)
        self._progress.setValue(0)

        self._error_label = QLabel(self)
        self._error_label.setWordWrap(True)
        self._error_label.setStyleSheet("color: red;")
        self._error_label.setVisible(False)

        self._confirm_label = QLabel('Type "I understand this is a breaking update" to enable install:', self)
        self._confirm_input = QLineEdit(self)
        self._confirm_input.setPlaceholderText("I understand this is a breaking update")
        self._confirm_label.setVisible(self._is_breaking)
        self._confirm_input.setVisible(self._is_breaking)
        if self._is_breaking:
            self._confirm_input.textChanged.connect(self._update_button_state)

        self._button_box = QDialogButtonBox(self)
        self._cancel_btn = self._button_box.addButton(QDialogButtonBox.StandardButton.Cancel)
        self._install_btn = self._button_box.addButton(
            f"Restart to install v{update_info.version}",
            QDialogButtonBox.ButtonRole.AcceptRole,
        )
        self._install_btn.setEnabled(False)

        self._button_box.rejected.connect(self.reject)
        self._button_box.accepted.connect(self._on_install_clicked)

        layout = QVBoxLayout(self)
        layout.addWidget(self._step_label)
        layout.addWidget(self._progress)
        layout.addWidget(self._error_label)
        layout.addWidget(self._confirm_label)
        layout.addWidget(self._confirm_input)
        layout.addWidget(self._button_box)

        # Wire worker signals if provided
        if self._worker is not None:
            self._worker.status_changed.connect(self._on_status_changed)
            self._worker.download_progress.connect(self._on_download_progress)
            self._worker.error.connect(self._on_error)
            self._worker.ready_to_install.connect(self._on_ready_to_install)

    # ------------------------------------------------------------------ slots
    @Slot(object)
    def _on_status_changed(self, status: UpdateStatus) -> None:
        if status.state == "downloading":
            self._step_label.setText("Downloading...")
            self._progress.setValue(int(status.download_progress_pct))
        elif status.state == "verifying":
            self._step_label.setText("Verifying checksum...")
            self._progress.setValue(100)
        elif status.state == "ready_to_install":
            self._step_label.setText("Ready to install")
            self._progress.setValue(100)
            self._update_button_state()
        elif status.state == "installing":
            self._step_label.setText("Installing...")
        elif status.state == "error":
            self._error_label.setText(status.error_message or "Unknown error")
            self._error_label.setVisible(True)
            self._step_label.setText("Error")

    @Slot(float)
    def _on_download_progress(self, pct: float) -> None:
        self._progress.setValue(int(pct * 100))
        self._step_label.setText(f"Downloading... {int(pct*100)}%")

    @Slot(str)
    def _on_error(self, msg: str) -> None:
        self._error_label.setText(msg)
        self._error_label.setVisible(True)
        self._step_label.setText("Error")

    @Slot(object, object)
    def _on_ready_to_install(self, info: UpdateInfo, path: Path) -> None:
        self._installer_path = path
        self._step_label.setText("Ready to install")
        self._progress.setValue(100)
        self._update_button_state()

    def _update_button_state(self) -> None:
        if self._installer_path is None:
            self._install_btn.setEnabled(False)
            return
        if self._is_breaking:
            ok = self._confirm_input.text().strip() == "I understand this is a breaking update"
            self._install_btn.setEnabled(ok)
        else:
            self._install_btn.setEnabled(True)

    def _on_install_clicked(self) -> None:
        if self._installer_path is None:
            return
        if self._is_breaking:
            if self._confirm_input.text().strip() != "I understand this is a breaking update":
                return
        self.install_requested.emit(self._installer_path)
        # Worker will handle actual install; close dialog
        self.accept()

    def set_installer_path(self, path: Path) -> None:
        """Manually set installer path (for testing or direct use)."""
        self._installer_path = path
        self._update_button_state()
