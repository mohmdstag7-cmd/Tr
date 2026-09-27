"""ProbabilityRing widget - donut progress with confidence label."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from app.ui.theme.tokens import get_tokens

BASELINE_SAMPLE_THRESHOLD: int = 300


def _apply_tabular(label: QLabel) -> None:
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


def _confidence_key(p: float) -> str:
    if p >= 0.6:
        return "confidence_high"
    if p >= 0.4:
        return "confidence_medium"
    return "confidence_low"


def _confidence_label(p: float) -> str:
    # Human readable paired with i18n key
    key = _confidence_key(p)
    mapping = {
        "confidence_high": "High confidence",
        "confidence_medium": "Medium confidence",
        "confidence_low": "Low confidence",
    }
    return mapping[key]


class ProbabilityRing(QWidget):
    """Circular progress ring showing probability and confidence."""

    def __init__(
        self,
        probability: float = 0.5,
        ci_low: float | None = None,
        ci_high: float | None = None,
        sample_size: int | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._probability: float = max(0.0, min(1.0, probability))
        self._ci_low: float | None = ci_low
        self._ci_high: float | None = ci_high
        self._sample_size: int | None = sample_size
        self._tokens: Any = None
        try:
            self._tokens = get_tokens()
        except Exception:
            self._tokens = None

        self.setMinimumSize(120, 140)
        self.setMaximumSize(200, 200)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Spacer to allow ring painting behind
        layout.addStretch(1)

        self._percent_label = QLabel(self)
        self._percent_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._percent_label.setObjectName("ProbabilityRingPercent")
        _apply_tabular(self._percent_label)
        pf = self._percent_label.font()
        pf.setBold(True)
        pf.setPointSize(20)
        self._percent_label.setFont(pf)

        self._detail_label = QLabel(self)
        self._detail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._detail_label.setObjectName("ProbabilityRingDetail")
        self._detail_label.setWordWrap(True)

        self._confidence_label = QLabel(self)
        self._confidence_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._confidence_label.setObjectName("ProbabilityRingConfidence")

        layout.addWidget(self._percent_label)
        layout.addWidget(self._detail_label)
        layout.addWidget(self._confidence_label)
        layout.addStretch(1)

        self._update_labels()
        self.reapply_tokens(self._tokens)

    @property
    def probability(self) -> float:
        return self._probability

    @probability.setter
    def probability(self, value: float) -> None:
        self._probability = max(0.0, min(1.0, value))
        self._update_labels()
        self.update()

    @property
    def ci_low(self) -> float | None:
        return self._ci_low

    @ci_low.setter
    def ci_low(self, value: float | None) -> None:
        self._ci_low = value
        self._update_labels()

    @property
    def ci_high(self) -> float | None:
        return self._ci_high

    @ci_high.setter
    def ci_high(self, value: float | None) -> None:
        self._ci_high = value
        self._update_labels()

    @property
    def sample_size(self) -> int | None:
        return self._sample_size

    @sample_size.setter
    def sample_size(self, value: int | None) -> None:
        self._sample_size = value
        self._update_labels()

    def _ring_color(self) -> str:
        p = self._probability
        if p >= 0.6:
            return _resolve_color(self._tokens, "profit", "#2ecc71")
        if p >= 0.4:
            return _resolve_color(self._tokens, "warning", "#f1c40f")
        return _resolve_color(self._tokens, "loss", "#e74c3c")

    def _update_labels(self) -> None:
        pct = int(round(self._probability * 100))
        self._percent_label.setText(f"{pct}%")

        # Detail line
        if self._sample_size is not None and self._sample_size < BASELINE_SAMPLE_THRESHOLD:
            self._detail_label.setText(f"baseline (n={self._sample_size})")
        elif self._ci_low is not None and self._ci_high is not None:
            # Compute ± in percentage points
            mid = self._probability * 100
            low = self._ci_low * 100
            high = self._ci_high * 100
            delta = (high - low) / 2.0
            # Clamp to reasonable
            delta_str = f"{delta:.1f}".rstrip("0").rstrip(".")
            n_part = f" (n={self._sample_size})" if self._sample_size is not None else ""
            self._detail_label.setText(f"{int(round(mid))}% ± {delta_str}%{n_part}")
        elif self._sample_size is not None:
            self._detail_label.setText(f"n={self._sample_size}")
        else:
            self._detail_label.setText("")

        # Confidence label - always shown, never color alone
        conf_text = _confidence_label(self._probability)
        # Include icon pairing for profit/loss distinction
        if self._probability >= 0.6:
            icon = "▲"
        elif self._probability < 0.4:
            icon = "▼"
        else:
            icon = "●"
        self._confidence_label.setText(f"{icon} {conf_text}")

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
        ring_color = self._ring_color()

        self._percent_label.setStyleSheet(f"color: {text_primary}; background: transparent; border: none;")
        self._detail_label.setStyleSheet(
            f"color: {text_secondary}; font-size: 11px; background: transparent; border: none;"
        )
        # Confidence label uses ring color but always paired with icon+text
        self._confidence_label.setStyleSheet(
            f"color: {ring_color}; font-size: 11px; font-weight: 600; background: transparent; border: none;"
        )
        self.update()

    def set_tokens(self, tokens: Any) -> None:
        self.reapply_tokens(tokens)

    def paintEvent(self, event: Any) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # Determine square for ring centered in widget
        w = self.width()
        h = self.height()
        # Reserve space for labels; ring is top-centered
        size = min(w - 16, h - 48, 120)
        if size <= 0:
            return
        x = (w - size) // 2
        y = 8
        rect = QRect(x, y, size, size)

        # Background track
        track_color = QColor(_resolve_color(self._tokens, "border", "#2d2d36"))
        bg_pen = QPen(track_color, 10)
        bg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(bg_pen)
        painter.drawEllipse(rect)

        # Progress arc
        ring_qcolor = QColor(self._ring_color())
        pen = QPen(ring_qcolor, 10)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        # QPainter arc: angles in 1/16 degree, 0 at 3 o'clock, positive counter-clockwise
        # We want start at top (90 degrees) and go clockwise
        start_angle = 90 * 16
        span_angle = int(-self._probability * 360 * 16)
        # Adjust rect for pen width
        inset = 5
        arc_rect = rect.adjusted(inset, inset, -inset, -inset)
        painter.drawArc(arc_rect, start_angle, span_angle)

        # Inner donut hole (optional subtle inner border)
        painter.end()

    def sizeHint(self) -> Any:  # type: ignore[override]
        from PySide6.QtCore import QSize

        return QSize(140, 160)
