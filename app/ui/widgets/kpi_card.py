"""
Premium KpiCard — bordered card with shadow, uppercase title, 24px tabular value,
delta with ▲/▼ and semantic color, 16px padding.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from app.ui.theme.tokens import FONT_MONO, FONT_SIZE, RADIUS, get_palette


class KpiCard(QFrame):
    def __init__(
        self,
        title: str = "—",
        value: str = "—",
        delta: str | None = None,
        delta_positive: bool | None = None,
        parent=None,
        theme: str = "dark",
    ):
        super().__init__(parent)
        self._theme = theme
        self._title_text = title
        self._value_text = value
        self._delta_text = delta
        self._delta_positive = delta_positive
        self.setObjectName("CardFrame")
        self.setMinimumWidth(160)
        self.setMinimumHeight(110)
        self._build_ui()
        self._apply_theme(theme)

    def _build_ui(self):
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 16, 16, 16)
        self._layout.setSpacing(8)

        self._title_label = QLabel(self._title_text.upper())
        self._title_label.setObjectName("KpiTitle")

        self._value_label = QLabel(self._value_text)
        self._value_label.setObjectName("KpiValue")
        self._value_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self._delta_label = QLabel("")
        self._delta_label.setObjectName("KpiDelta")
        self._delta_label.setVisible(False)

        self._layout.addWidget(self._title_label)
        self._layout.addWidget(self._value_label)
        self._layout.addStretch(1)
        self._layout.addWidget(self._delta_label)

        self._refresh_delta()

    def _apply_theme(self, theme: str):
        self._theme = theme
        p = get_palette(theme)
        self.setStyleSheet(f"#CardFrame {{ background-color: {p.card}; border: 1px solid {p.border}; border-radius: {RADIUS.lg}px; }}")
        self._title_label.setStyleSheet(
            f"font-size: {FONT_SIZE.caption}px; font-weight: 600; color: {p.text_secondary}; " f"letter-spacing: 0.08em; background: transparent; border: none;"
        )
        self._value_label.setStyleSheet(
            f"font-size: {FONT_SIZE.kpi_value}px; font-weight: 600; color: {p.text}; "
            f"font-family: {FONT_MONO}; font-feature-settings: 'tnum'; letter-spacing: -0.02em; "
            f"background: transparent; border: none;"
        )
        self._refresh_delta()

    def _refresh_delta(self):
        if not self._delta_text:
            self._delta_label.setVisible(False)
            return
        p = get_palette(self._theme)
        self._delta_label.setVisible(True)
        if self._delta_positive is True:
            arrow = "▲"
            color = p.profit
        elif self._delta_positive is False:
            arrow = "▼"
            color = p.loss
        else:
            arrow = ""
            color = p.text_secondary
        txt = f"{arrow} {self._delta_text}" if arrow else self._delta_text
        self._delta_label.setText(txt)
        self._delta_label.setStyleSheet(
            f"font-size: {FONT_SIZE.body}px; font-weight: 600; color: {color}; " f"font-family: {FONT_MONO}; font-feature-settings: 'tnum'; background: transparent; border: none;"
        )

    # ── Public API ──
    def set_title(self, title: str):
        self._title_text = title
        self._title_label.setText(title.upper())

    def set_value(self, value: str):
        self._value_text = value
        self._value_label.setText(value)

    def set_delta(self, text: str | None, positive: bool | None = None):
        self._delta_text = text
        self._delta_positive = positive
        self._refresh_delta()

    def set_theme(self, theme: str):
        self._apply_theme(theme)

    # Convenience: numeric helper
    def set_numeric(self, value: float, prefix: str = "$", decimals: int = 2, delta: float | None = None, delta_suffix: str = "%"):
        self.set_value(f"{prefix}{value:,.{decimals}f}")
        if delta is not None:
            self.set_delta(f"{delta:+.{decimals}f}{delta_suffix}", positive=(delta >= 0))
