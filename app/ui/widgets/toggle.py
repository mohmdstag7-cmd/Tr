"""Toggle widget - custom pill switch."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

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


class Toggle(QWidget):
    """Custom on/off pill switch (36x20)."""

    toggled = Signal(bool)

    def __init__(
        self,
        checked: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._checked: bool = checked
        self._tokens: Any = None
        try:
            self._tokens = get_tokens()
        except Exception:
            self._tokens = None

        self._knob_pos: float = 1.0 if checked else 0.0
        self.setFixedSize(36, 20)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

        self._anim = QPropertyAnimation(self, b"knobPosition", self)
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

        self.reapply_tokens(self._tokens)

    def _get_knob_position(self) -> float:
        return self._knob_pos

    def _set_knob_position(self, value: float) -> None:
        self._knob_pos = value
        self.update()

    knobPosition = Property(float, _get_knob_position, _set_knob_position)  # type: ignore[assignment]

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool) -> None:
        if self._checked == checked:
            return
        self._checked = checked
        self._animate_to(1.0 if checked else 0.0)
        self.toggled.emit(checked)

    def _animate_to(self, target: float) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._knob_pos)
        self._anim.setEndValue(target)
        self._anim.start()

    def mousePressEvent(self, event: Any) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self.setChecked(not self._checked)
        super().mousePressEvent(event)

    def keyPressEvent(self, event: Any) -> None:  # type: ignore[override]
        if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.setChecked(not self._checked)
            event.accept()
            return
        super().keyPressEvent(event)

    def reapply_tokens(self, tokens: Any | None = None) -> None:
        if tokens is not None:
            self._tokens = tokens
        if self._tokens is None:
            try:
                self._tokens = get_tokens()
            except Exception:
                self._tokens = None
        self.update()

    def set_tokens(self, tokens: Any) -> None:
        self.reapply_tokens(tokens)

    def paintEvent(self, event: Any) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # Colors
        bg_off = QColor(_resolve_color(self._tokens, "border", "#2d2d36"))
        bg_on = QColor(_resolve_color(self._tokens, "accent", "#7b61ff"))
        # Fallback to profit if accent not distinct
        if bg_on.name() == bg_off.name():
            bg_on = QColor(_resolve_color(self._tokens, "profit", "#2ecc71"))
        knob_color = QColor("#ffffff")
        border_color = QColor(_resolve_color(self._tokens, "border", "#2d2d36"))

        # Interpolate background based on knob position
        r = int(bg_off.red() + (bg_on.red() - bg_off.red()) * self._knob_pos)
        g = int(bg_off.green() + (bg_on.green() - bg_off.green()) * self._knob_pos)
        b = int(bg_off.blue() + (bg_on.blue() - bg_off.blue()) * self._knob_pos)
        bg = QColor(r, g, b)

        rect = self.rect()
        # Pill background
        painter.setPen(QPen(border_color, 1))
        painter.setBrush(bg)
        painter.drawRoundedRect(rect.adjusted(0, 0, -1, -1), 10, 10)

        # Knob
        knob_size = 14
        # Travel distance: width - knob_size - 4 (2px padding each side)
        travel = 36 - knob_size - 6
        x = 3 + int(travel * self._knob_pos)
        y = (20 - knob_size) // 2
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(knob_color)
        # Simple shadow
        painter.setOpacity(0.15)
        painter.drawEllipse(x + 1, y + 1, knob_size, knob_size)
        painter.setOpacity(1.0)
        painter.drawEllipse(x, y, knob_size, knob_size)
        painter.end()

    def sizeHint(self) -> Any:  # type: ignore[override]
        from PySide6.QtCore import QSize

        return QSize(36, 20)
