"""Drawer widget - right-side sliding overlay."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRect, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
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


class Drawer(QWidget):
    """Right-side sliding drawer overlay."""

    closed = Signal()

    def __init__(
        self,
        title: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._title_text: str = title
        self._tokens: Any = None
        try:
            self._tokens = get_tokens()
        except Exception:
            self._tokens = None

        self.setObjectName("Drawer")
        # Drawer should overlay parent; hide initially
        self.hide()
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        # Fixed width drawer, height matches parent
        self.setFixedWidth(360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Title bar
        self._title_bar = QFrame(self)
        self._title_bar.setObjectName("DrawerTitleBar")
        title_layout = QHBoxLayout(self._title_bar)
        title_layout.setContentsMargins(16, 12, 16, 12)
        title_layout.setSpacing(8)

        self._title_label = QLabel(title, self._title_bar)
        self._title_label.setObjectName("DrawerTitle")
        title_layout.addWidget(self._title_label, 1)

        self._close_btn = QPushButton("✕", self._title_bar)
        self._close_btn.setObjectName("DrawerCloseButton")
        self._close_btn.setFixedSize(28, 28)
        self._close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_btn.setFlat(True)
        self._close_btn.clicked.connect(self.close_drawer)
        title_layout.addWidget(self._close_btn)

        layout.addWidget(self._title_bar)

        # Content container
        self._content_container = QFrame(self)
        self._content_container.setObjectName("DrawerContent")
        self._content_layout = QVBoxLayout(self._content_container)
        self._content_layout.setContentsMargins(16, 16, 16, 16)
        self._content_layout.setSpacing(8)
        layout.addWidget(self._content_container, 1)

        # Animation on geometry
        self._anim = QPropertyAnimation(self, b"geometry", self)
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._anim.finished.connect(self._on_anim_finished)
        self._is_open: bool = False
        self._pending_close: bool = False

        self.reapply_tokens(self._tokens)

        # Ensure drawer tracks parent size
        if parent is not None:
            parent.installEventFilter(self)

    def eventFilter(self, watched: Any, event: Any) -> bool:  # type: ignore[override]
        from PySide6.QtCore import QEvent

        if watched is self.parent() and event.type() == QEvent.Type.Resize:
            self._update_geometry_for_parent()
        return super().eventFilter(watched, event)

    def _update_geometry_for_parent(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        h = parent.height()
        self.setFixedHeight(h)
        if self._is_open:
            self.setGeometry(QRect(parent.width() - self.width(), 0, self.width(), h))
        else:
            self.setGeometry(QRect(parent.width(), 0, self.width(), h))

    def set_content(self, widget: QWidget) -> None:
        # Clear previous content
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
        widget.setParent(self._content_container)
        self._content_layout.addWidget(widget, 1)

    def open_drawer(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            self.show()
            self._is_open = True
            return
        self._update_geometry_for_parent()
        self.show()
        self.raise_()
        start = QRect(parent.width(), 0, self.width(), parent.height())
        end = QRect(parent.width() - self.width(), 0, self.width(), parent.height())
        self._pending_close = False
        self._is_open = True
        self._anim.stop()
        self._anim.setStartValue(start)
        self._anim.setEndValue(end)
        self._anim.start()

    def close_drawer(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            self.hide()
            self._is_open = False
            self.closed.emit()
            return
        start = self.geometry()
        end = QRect(parent.width(), 0, self.width(), parent.height())
        self._pending_close = True
        self._is_open = False
        self._anim.stop()
        self._anim.setStartValue(start)
        self._anim.setEndValue(end)
        self._anim.start()

    def _on_anim_finished(self) -> None:
        if self._pending_close:
            self.hide()
            self._pending_close = False
            self.closed.emit()

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

        self.setStyleSheet(
            f"""
            #Drawer {{
                background-color: {card};
                border-left: 1px solid {border};
                border-top-left-radius: 12px;
                border-bottom-left-radius: 12px;
            }}
            #DrawerTitleBar {{
                background-color: {bg};
                border-bottom: 1px solid {border};
                border-top-left-radius: 12px;
            }}
            #DrawerTitle {{
                color: {text_primary};
                font-size: 14px;
                font-weight: 600;
                background: transparent;
                border: none;
            }}
            #DrawerCloseButton {{
                background-color: transparent;
                color: {text_secondary};
                border: 1px solid transparent;
                border-radius: 12px;
                font-size: 14px;
            }}
            #DrawerCloseButton:hover {{
                background-color: {border};
                color: {text_primary};
            }}
            #DrawerContent {{
                background-color: {card};
                border: none;
            }}
            """
        )

    def set_tokens(self, tokens: Any) -> None:
        self.reapply_tokens(tokens)
