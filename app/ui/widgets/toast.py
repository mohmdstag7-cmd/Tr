"""Toast widget - non-blocking notification."""

from __future__ import annotations

from typing import Any, Literal

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRect, Qt, QTimer
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QWidget

from app.ui.theme.tokens import get_tokens

ToastKind = Literal["info", "success", "warning", "error"]


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


_KIND_COLOR: dict[str, str] = {
    "info": "accent",
    "success": "profit",
    "warning": "warning",
    "error": "loss",
}

_KIND_ICON: dict[str, str] = {
    "info": "ℹ",
    "success": "✓",
    "warning": "⚠",
    "error": "✕",
}


class Toast(QFrame):
    """Bottom-right auto-dismiss toast."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Toast")
        self._tokens: Any = None
        try:
            self._tokens = get_tokens()
        except Exception:
            self._tokens = None

        self._kind: ToastKind = "info"
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._hide_animated)

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.hide()
        self.setFixedWidth(320)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self._icon_label = QLabel(self)
        self._icon_label.setObjectName("ToastIcon")
        self._icon_label.setFixedSize(20, 20)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._icon_label)

        self._message_label = QLabel(self)
        self._message_label.setObjectName("ToastMessage")
        self._message_label.setWordWrap(True)
        self._message_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._message_label, 1)

        self._close_btn = QPushButton("✕", self)
        self._close_btn.setObjectName("ToastCloseButton")
        self._close_btn.setFixedSize(20, 20)
        self._close_btn.setFlat(True)
        self._close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_btn.clicked.connect(self._hide_animated)
        layout.addWidget(self._close_btn)

        self._anim = QPropertyAnimation(self, b"geometry", self)
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

        self.reapply_tokens(self._tokens)

    def show_toast(self, message: str, kind: ToastKind = "info", duration_ms: int = 3000) -> None:
        self._kind = kind
        self._message_label.setText(message)
        self._icon_label.setText(_KIND_ICON.get(kind, "ℹ"))
        self.reapply_tokens(self._tokens)

        parent = self.parentWidget()
        if parent is not None:
            # Position at bottom-right with 16px margin (8px grid *2)
            x = parent.width() - self.width() - 16
            y = parent.height() - self.height() - 16
            self.setGeometry(QRect(x, y + 20, self.width(), self.height()))
            self.show()
            self.raise_()
            # Slide in
            self._anim.stop()
            self._anim.setStartValue(QRect(x, y + 20, self.width(), self.height()))
            self._anim.setEndValue(QRect(x, y, self.width(), self.height()))
            self._anim.start()
        else:
            self.show()

        self._timer.stop()
        if duration_ms > 0:
            self._timer.start(duration_ms)

    def _hide_animated(self) -> None:
        self._timer.stop()
        parent = self.parentWidget()
        if parent is not None and self.isVisible():
            start = self.geometry()
            end = QRect(start.x(), start.y() + 20, start.width(), start.height())
            self._anim.stop()
            self._anim.setStartValue(start)
            self._anim.setEndValue(end)
            self._anim.finished.connect(self._on_hide_finished)
            self._anim.start()
        else:
            self.hide()

    def _on_hide_finished(self) -> None:
        try:
            self._anim.finished.disconnect(self._on_hide_finished)
        except Exception:
            pass
        self.hide()

    def reapply_tokens(self, tokens: Any | None = None) -> None:
        if tokens is not None:
            self._tokens = tokens
        if self._tokens is None:
            try:
                self._tokens = get_tokens()
            except Exception:
                self._tokens = None

        bg = _resolve_color(self._tokens, "surface", "#1e1e24")
        border = _resolve_color(self._tokens, "border", "#2d2d36")
        text_primary = _resolve_color(self._tokens, "text_primary", "#f5f5f7")
        text_secondary = _resolve_color(self._tokens, "text_secondary", "#9aa0b2")
        kind_token = _KIND_COLOR.get(self._kind, "accent")
        accent = _resolve_color(self._tokens, kind_token, "#7b61ff")

        self.setStyleSheet(
            f"""
            #Toast {{
                background-color: {bg};
                border: 1px solid {border};
                border-left: 3px solid {accent};
                border-radius: 12px;
            }}
            #ToastIcon {{
                color: {accent};
                font-size: 14px;
                font-weight: 700;
                background: transparent;
                border: none;
            }}
            #ToastMessage {{
                color: {text_primary};
                font-size: 13px;
                background: transparent;
                border: none;
            }}
            #ToastCloseButton {{
                color: {text_secondary};
                background: transparent;
                border: none;
                border-radius: 6px;
                font-size: 12px;
            }}
            #ToastCloseButton:hover {{
                background-color: {border};
                color: {text_primary};
            }}
            """
        )

    def set_tokens(self, tokens: Any) -> None:
        self.reapply_tokens(tokens)
