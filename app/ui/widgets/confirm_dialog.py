"""ConfirmDialog - modal confirmation with optional typed confirmation."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.ui.theme.tokens import get_tokens


def _resolve_color(tokens: Any, name: str, fallback: str) -> str:
    try:
        if hasattr(tokens, "colors"):
            colors = tokens.colors
            if hasattr(colors, name):
                return str(getattr(colors, name))
            if isinstance(colors, dict) and name in colors:
                return str(colors[name])
        if isinstance(tokens, dict) and name in tokens:
            return str(tokens[name])
        if hasattr(tokens, name):
            return str(getattr(tokens, name))
    except Exception:
        pass
    return fallback


class ConfirmDialog(QDialog):
    """Modal confirmation dialog with optional typed confirmation gate."""

    confirmed = Signal()
    cancelled = Signal()

    def __init__(
        self,
        title: str,
        message: str,
        confirm_label: str = "OK",
        cancel_label: str = "Cancel",
        require_typed_confirmation: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("ConfirmDialog")
        self.setWindowTitle(title)
        self.setModal(True)
        self._require_typed: str | None = require_typed_confirmation
        self._tokens: Any = None
        try:
            self._tokens = get_tokens()
        except Exception:
            self._tokens = None

        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        self._title_label = QLabel(title, self)
        self._title_label.setObjectName("ConfirmDialogTitle")
        tf = self._title_label.font()
        tf.setPointSize(14)
        tf.setBold(True)
        self._title_label.setFont(tf)
        layout.addWidget(self._title_label)

        self._message_label = QLabel(message, self)
        self._message_label.setObjectName("ConfirmDialogMessage")
        self._message_label.setWordWrap(True)
        layout.addWidget(self._message_label)

        self._confirm_input: QLineEdit | None = None
        if require_typed_confirmation is not None:
            hint = QLabel(f'Type "{require_typed_confirmation}" to confirm:', self)
            hint.setObjectName("ConfirmDialogHint")
            layout.addWidget(hint)
            self._confirm_input = QLineEdit(self)
            self._confirm_input.setObjectName("ConfirmDialogInput")
            self._confirm_input.setPlaceholderText(require_typed_confirmation)
            layout.addWidget(self._confirm_input)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        btn_layout.addStretch(1)

        self._cancel_btn = QPushButton(cancel_label, self)
        self._cancel_btn.setObjectName("ConfirmDialogCancel")
        self._cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cancel_btn.clicked.connect(self._on_cancel)
        btn_layout.addWidget(self._cancel_btn)

        self._confirm_btn = QPushButton(confirm_label, self)
        self._confirm_btn.setObjectName("ConfirmDialogConfirm")
        self._confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._confirm_btn.clicked.connect(self._on_confirm)
        btn_layout.addWidget(self._confirm_btn)

        layout.addLayout(btn_layout)

        if self._confirm_input is not None:
            self._confirm_btn.setEnabled(False)
            self._confirm_input.textChanged.connect(self._on_typed_changed)

        self.reapply_tokens(self._tokens)

    def _on_typed_changed(self, text: str) -> None:
        if self._require_typed is None or self._confirm_input is None:
            return
        self._confirm_btn.setEnabled(text == self._require_typed)

    def _on_confirm(self) -> None:
        self.confirmed.emit()
        self.accept()

    def _on_cancel(self) -> None:
        self.cancelled.emit()
        self.reject()

    def reapply_tokens(self, tokens: Any | None = None) -> None:
        if tokens is not None:
            self._tokens = tokens
        if self._tokens is None:
            try:
                self._tokens = get_tokens()
            except Exception:
                self._tokens = None

        bg = _resolve_color(self._tokens, "surface", "#1e1e24")
        card = _resolve_color(self._tokens, "card", "#1e1e24")
        border = _resolve_color(self._tokens, "border", "#2d2d36")
        text_primary = _resolve_color(self._tokens, "text_primary", "#f5f5f7")
        text_secondary = _resolve_color(self._tokens, "text_secondary", "#9aa0b2")
        accent = _resolve_color(self._tokens, "accent", "#7b61ff")
        loss = _resolve_color(self._tokens, "loss", "#e74c3c")

        self.setStyleSheet(
            f"""
            #ConfirmDialog {{
                background-color: {card};
                border: 1px solid {border};
                border-radius: 12px;
            }}
            #ConfirmDialogTitle {{
                color: {text_primary};
                background: transparent;
                border: none;
            }}
            #ConfirmDialogMessage {{
                color: {text_secondary};
                font-size: 13px;
                background: transparent;
                border: none;
            }}
            #ConfirmDialogHint {{
                color: {text_secondary};
                font-size: 11px;
                background: transparent;
                border: none;
            }}
            #ConfirmDialogInput {{
                background-color: {bg};
                color: {text_primary};
                border: 1px solid {border};
                border-radius: 12px;
                padding: 8px 12px;
                font-size: 13px;
            }}
            #ConfirmDialogInput:focus {{
                border: 1px solid {accent};
            }}
            #ConfirmDialogCancel {{
                background-color: transparent;
                color: {text_primary};
                border: 1px solid {border};
                border-radius: 12px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 600;
            }}
            #ConfirmDialogCancel:hover {{
                background-color: {bg};
            }}
            #ConfirmDialogConfirm {{
                background-color: {loss};
                color: #ffffff;
                border: 1px solid {border};
                border-radius: 12px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 600;
            }}
            #ConfirmDialogConfirm:hover {{
                background-color: {accent};
            }}
            #ConfirmDialogConfirm:disabled {{
                background-color: {border};
                color: {text_secondary};
            }}
            """
        )

    def set_tokens(self, tokens: Any) -> None:
        self.reapply_tokens(tokens)

    def keyPressEvent(self, event: Any) -> None:  # type: ignore[override]
        if event.key() == Qt.Key.Key_Escape:
            self._on_cancel()
            event.accept()
            return
        super().keyPressEvent(event)
