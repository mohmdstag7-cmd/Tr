"""Dismissible banner shown when an update is available."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from app.updater.models import UpdateInfo


class UpdateBanner(QFrame):
    """Non-modal banner for available updates."""

    update_requested = Signal(object)  # UpdateInfo
    dismissed = Signal()

    def __init__(self, parent=None) -> None:  # type: ignore[no-untyped-def]
        super().__init__(parent)
        self.setObjectName("UpdateBanner")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self._update_info: UpdateInfo | None = None

        self._label = QLabel(self)
        self._label.setWordWrap(True)

        self._notes_btn = QPushButton("Release notes", self)
        self._notes_btn.setFlat(True)
        self._notes_btn.setCursor(self._notes_btn.cursor())
        self._notes_btn.clicked.connect(self._on_notes_clicked)

        self._update_btn = QPushButton("Update now", self)
        self._update_btn.setObjectName("UpdateNowButton")
        self._update_btn.clicked.connect(self._on_update_clicked)

        self._dismiss_btn = QPushButton("Dismiss", self)
        self._dismiss_btn.setFlat(True)
        self._dismiss_btn.clicked.connect(self._on_dismiss_clicked)

        # Layout
        top_row = QHBoxLayout()
        top_row.addWidget(self._label, 1)
        top_row.addWidget(self._notes_btn)
        top_row.addWidget(self._update_btn)
        top_row.addWidget(self._dismiss_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.addLayout(top_row)

        self.setVisible(False)
        self.setStyleSheet("#UpdateBanner { background-color: palette(highlight); border-radius: 6px; }")

    def set_update_info(self, update_info: UpdateInfo) -> None:
        self._update_info = update_info
        first_line = update_info.release_notes.splitlines()[0] if update_info.release_notes else ""
        if len(first_line) > 120:
            first_line = first_line[:117] + "..."
        suffix = f" — {first_line}" if first_line else ""
        self._label.setText(f"v{update_info.version} available{suffix}")
        self.setVisible(True)

    def clear(self) -> None:
        self._update_info = None
        self.setVisible(False)

    # ------------------------------------------------------------------ slots
    def _on_notes_clicked(self) -> None:
        if self._update_info is None:
            return
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        QDesktopServices.openUrl(QUrl(self._update_info.notes_url))

    def _on_update_clicked(self) -> None:
        if self._update_info is not None:
            self.update_requested.emit(self._update_info)

    def _on_dismiss_clicked(self) -> None:
        self.clear()
        self.dismissed.emit()
