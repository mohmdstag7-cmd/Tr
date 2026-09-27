"""KpiCard widget - metric card with title, value and delta."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from app.ui.theme.tokens import get_tokens


def _apply_tabular(label: QLabel) -> None:
    """Enable tabular numbers (tnum) for a label."""
    font: QFont = label.font()
    try:
        Tag = getattr(QFont, "Tag", None)
        if Tag is not None:
            try:
                tag_val = Tag(b"tnum")  # type: ignore[call-arg]
                font.setFeature(tag_val, 1)
            except Exception:
                pass
        else:
            font.setFeature("tnum", 1)  # type: ignore[arg-type]
    except Exception:
        pass
    label.setFont(font)


def _resolve_color(tokens: Any, name: str, fallback: str) -> str:
    """Resolve a color from tokens with fallbacks for dict/object shapes."""
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


class KpiCard(QFrame):
    """Metric card showing title, value and optional delta."""

    def __init__(
        self,
        title: str,
        value: str,
        delta: str | None = None,
        delta_positive: bool | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("KpiCard")
        self._title_text: str = title
        self._value_text: str = value
        self._delta_text: str | None = delta
        self._delta_positive: bool | None = delta_positive
        self._tokens: Any = None

        try:
            self._tokens = get_tokens()
        except Exception:
            self._tokens = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        self._title_label = QLabel(title, self)
        self._title_label.setObjectName("KpiCardTitle")
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self._value_label = QLabel(value, self)
        self._value_label.setObjectName("KpiCardValue")
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        _apply_tabular(self._value_label)
        vf = self._value_label.font()
        vf.setBold(True)
        vf.setPointSize(22)
        self._value_label.setFont(vf)

        self._delta_label = QLabel(self)
        self._delta_label.setObjectName("KpiCardDelta")
        self._delta_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        _apply_tabular(self._delta_label)

        layout.addWidget(self._title_label)
        layout.addWidget(self._value_label)
        layout.addWidget(self._delta_label)

        self._update_delta()
        self.reapply_tokens(self._tokens)

    @property
    def title(self) -> str:
        return self._title_text

    @title.setter
    def title(self, value: str) -> None:
        self._title_text = value
        self._title_label.setText(value)

    @property
    def value(self) -> str:
        return self._value_text

    @value.setter
    def value(self, val: str) -> None:
        self._value_text = val
        self._value_label.setText(val)

    @property
    def delta(self) -> str | None:
        return self._delta_text

    @delta.setter
    def delta(self, val: str | None) -> None:
        self._delta_text = val
        self._update_delta()

    @property
    def delta_positive(self) -> bool | None:
        return self._delta_positive

    @delta_positive.setter
    def delta_positive(self, val: bool | None) -> None:
        self._delta_positive = val
        self._update_delta()

    def _update_delta(self) -> None:
        if self._delta_text is None or self._delta_positive is None:
            self._delta_label.hide()
            self._delta_label.setText("")
            return
        self._delta_label.show()
        raw = self._delta_text.strip()
        # Ensure +/- prefix for accessibility (never color alone)
        has_sign = raw.startswith("+") or raw.startswith("-")
        if not has_sign:
            raw = ("+" + raw) if self._delta_positive else ("-" + raw)
        # Pair color with icon and sign
        icon = "▲" if self._delta_positive else "▼"
        self._delta_label.setText(f"{icon} {raw}")

    def reapply_tokens(self, tokens: Any | None = None) -> None:
        if tokens is not None:
            self._tokens = tokens
        if self._tokens is None:
            try:
                self._tokens = get_tokens()
            except Exception:
                self._tokens = None

        bg = _resolve_color(self._tokens, "surface", "#1e1e24")
        card_bg = _resolve_color(self._tokens, "card", bg)
        border = _resolve_color(self._tokens, "border", "#2d2d36")
        text_primary = _resolve_color(self._tokens, "text_primary", "#f5f5f7")
        text_secondary = _resolve_color(self._tokens, "text_secondary", "#9aa0b2")
        profit = _resolve_color(self._tokens, "profit", "#2ecc71")
        loss = _resolve_color(self._tokens, "loss", "#e74c3c")

        # Delta color is set via inline style to keep icon+text pairing
        if self._delta_positive is True:
            delta_color = profit
        elif self._delta_positive is False:
            delta_color = loss
        else:
            delta_color = text_secondary

        self.setStyleSheet(
            f"""
            #KpiCard {{
                background-color: {card_bg};
                border: 1px solid {border};
                border-radius: 12px;
            }}
            #KpiCardTitle {{
                color: {text_secondary};
                font-size: 12px;
                font-weight: 500;
                background: transparent;
                border: none;
            }}
            #KpiCardValue {{
                color: {text_primary};
                font-size: 24px;
                font-weight: 700;
                background: transparent;
                border: none;
            }}
            #KpiCardDelta {{
                color: {delta_color};
                font-size: 12px;
                font-weight: 600;
                background: transparent;
                border: none;
            }}
            """
        )
        # Ensure transition hint via property (Qt doesn't support CSS transitions, but keep token duration)
        self.setProperty("transitionDuration", 180)

    def set_tokens(self, tokens: Any) -> None:
        self.reapply_tokens(tokens)
