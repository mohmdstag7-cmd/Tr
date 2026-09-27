"""EmptyState and ErrorState widgets."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

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


class EmptyState(QWidget):
    """Empty state with icon, headline, sub-headline and optional action."""

    action_triggered = Signal()

    def __init__(
        self,
        headline: str = "No data",
        sub_headline: str = "There is nothing to display yet.",
        action_label: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._headline = headline
        self._sub_headline = sub_headline
        self._action_label = action_label
        self._tokens: Any = None
        try:
            self._tokens = get_tokens()
        except Exception:
            self._tokens = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._icon_label = QLabel("○", self)
        self._icon_label.setObjectName("EmptyStateIcon")
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        f = self._icon_label.font()
        f.setPointSize(36)
        self._icon_label.setFont(f)
        layout.addWidget(self._icon_label)

        self._headline_label = QLabel(headline, self)
        self._headline_label.setObjectName("EmptyStateHeadline")
        self._headline_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hf = self._headline_label.font()
        hf.setPointSize(14)
        hf.setBold(True)
        self._headline_label.setFont(hf)
        layout.addWidget(self._headline_label)

        self._sub_label = QLabel(sub_headline, self)
        self._sub_label.setObjectName("EmptyStateSub")
        self._sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._sub_label.setWordWrap(True)
        sf = self._sub_label.font()
        sf.setPointSize(11)
        self._sub_label.setFont(sf)
        layout.addWidget(self._sub_label)

        self._action_btn: QPushButton | None = None
        if action_label is not None:
            self._action_btn = QPushButton(action_label, self)
            self._action_btn.setObjectName("EmptyStateAction")
            self._action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._action_btn.clicked.connect(self.action_triggered.emit)
            layout.addWidget(self._action_btn, 0, Qt.AlignmentFlag.AlignCenter)

        self.reapply_tokens(self._tokens)

    def reapply_tokens(self, tokens: Any | None = None) -> None:
        if tokens is not None:
            self._tokens = tokens
        if self._tokens is None:
            try:
                self._tokens = get_tokens()
            except Exception:
                self._tokens = None

        text_primary = _resolve_color(self._tokens, "text_primary", "#f5f5f7")
        text_secondary = _resolve_color(self._tokens, "text_secondary", "#9aa0b2")
        border = _resolve_color(self._tokens, "border", "#2d2d36")
        accent = _resolve_color(self._tokens, "accent", "#7b61ff")
        surface = _resolve_color(self._tokens, "surface", "#1e1e24")

        self._icon_label.setStyleSheet(f"color: {text_secondary}; background: transparent; border: none;")
        self._headline_label.setStyleSheet(f"color: {text_primary}; background: transparent; border: none;")
        self._sub_label.setStyleSheet(f"color: {text_secondary}; background: transparent; border: none;")
        if self._action_btn is not None:
            self._action_btn.setStyleSheet(
                f"""
                #EmptyStateAction {{
                    background-color: {accent};
                    color: #ffffff;
                    border: 1px solid {border};
                    border-radius: 12px;
                    padding: 8px 16px;
                    font-size: 13px;
                    font-weight: 600;
                }}
                #EmptyStateAction:hover {{
                    background-color: {surface};
                    color: {text_primary};
                    border: 1px solid {accent};
                }}
                """
            )

    def set_tokens(self, tokens: Any) -> None:
        self.reapply_tokens(tokens)


class ErrorState(QWidget):
    """Error state with icon, headline, sub-headline and retry button."""

    retry_requested = Signal()

    def __init__(
        self,
        headline: str = "Something went wrong",
        sub_headline: str = "An unexpected error occurred. Please try again.",
        retry_label: str = "Retry",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._headline = headline
        self._sub_headline = sub_headline
        self._retry_label = retry_label
        self._tokens: Any = None
        try:
            self._tokens = get_tokens()
        except Exception:
            self._tokens = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._icon_label = QLabel("⚠", self)
        self._icon_label.setObjectName("ErrorStateIcon")
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        f = self._icon_label.font()
        f.setPointSize(36)
        self._icon_label.setFont(f)
        layout.addWidget(self._icon_label)

        self._headline_label = QLabel(headline, self)
        self._headline_label.setObjectName("ErrorStateHeadline")
        self._headline_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hf = self._headline_label.font()
        hf.setPointSize(14)
        hf.setBold(True)
        self._headline_label.setFont(hf)
        layout.addWidget(self._headline_label)

        self._sub_label = QLabel(sub_headline, self)
        self._sub_label.setObjectName("ErrorStateSub")
        self._sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._sub_label.setWordWrap(True)
        sf = self._sub_label.font()
        sf.setPointSize(11)
        self._sub_label.setFont(sf)
        layout.addWidget(self._sub_label)

        self._retry_btn = QPushButton(retry_label, self)
        self._retry_btn.setObjectName("ErrorStateRetry")
        self._retry_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._retry_btn.clicked.connect(self.retry_requested.emit)
        layout.addWidget(self._retry_btn, 0, Qt.AlignmentFlag.AlignCenter)

        self.reapply_tokens(self._tokens)

    def reapply_tokens(self, tokens: Any | None = None) -> None:
        if tokens is not None:
            self._tokens = tokens
        if self._tokens is None:
            try:
                self._tokens = get_tokens()
            except Exception:
                self._tokens = None

        text_primary = _resolve_color(self._tokens, "text_primary", "#f5f5f7")
        text_secondary = _resolve_color(self._tokens, "text_secondary", "#9aa0b2")
        border = _resolve_color(self._tokens, "border", "#2d2d36")
        loss = _resolve_color(self._tokens, "loss", "#e74c3c")
        surface = _resolve_color(self._tokens, "surface", "#1e1e24")

        self._icon_label.setStyleSheet(f"color: {loss}; background: transparent; border: none;")
        self._headline_label.setStyleSheet(f"color: {text_primary}; background: transparent; border: none;")
        self._sub_label.setStyleSheet(f"color: {text_secondary}; background: transparent; border: none;")
        self._retry_btn.setStyleSheet(
            f"""
            #ErrorStateRetry {{
                background-color: {loss};
                color: #ffffff;
                border: 1px solid {border};
                border-radius: 12px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 600;
            }}
            #ErrorStateRetry:hover {{
                background-color: {surface};
                color: {text_primary};
                border: 1px solid {loss};
            }}
            """
        )

    def set_tokens(self, tokens: Any) -> None:
        self.reapply_tokens(tokens)
