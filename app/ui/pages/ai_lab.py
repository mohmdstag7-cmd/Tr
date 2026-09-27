"""AI Lab page — Phase 1 stub."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from app.ui.i18n import tr
from app.ui.theme.tokens import get_tokens
from app.ui.widgets import EmptyState


class AiLabPage(QWidget):
    """AI Lab page (Phase 1 stub)."""

    refresh_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("AiLabPage")
        tokens = get_tokens("dark")
        try:
            pad = int(getattr(getattr(tokens, "spacing", None), "md", 16))  # type: ignore[arg-type]
        except Exception:
            pad = 16

        root = QVBoxLayout(self)
        root.setContentsMargins(pad, pad, pad, pad)
        root.setSpacing(pad)

        title = QLabel(tr("ai_lab.title", default="AI Lab"), self)
        title.setObjectName("PageTitle")
        title.setStyleSheet("font-size: 20px; font-weight: 700;")
        root.addWidget(title)

        self.empty = EmptyState(  # type: ignore[call-arg]
            headline=tr("common.empty_title", default="No data yet"),
            sub_headline=tr(
                "ai_lab.empty_state",
                default="AI improvement loop will appear here after Phase 13.",
            ),
            parent=self,
        )
        root.addWidget(self.empty, 1)

    def refresh_data(self) -> None:
        """Stub: refresh AI Lab."""
        self.refresh_requested.emit()
