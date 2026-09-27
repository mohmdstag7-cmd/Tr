"""
Premium Status Bar — 32px, connection dot with pulse, pill badges,
tabular numbers, vertical dividers, kill switch.
"""

from __future__ import annotations

from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton

from app.ui.theme.tokens import FONT_MONO, FONT_SIZE, get_palette


class DotIndicator(QFrame):
    """8px circle dot. Pulse animation when connecting."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(10, 10)
        self._color = "#22C55E"
        self._opacity = 1.0
        self._pulse_anim = None

    def set_color(self, color: str):
        self._color = color
        self.update()

    def set_opacity(self, v: float):
        self._opacity = v
        self.update()

    def get_opacity(self) -> float:
        return self._opacity

    opacity = Property(float, get_opacity, set_opacity)

    def start_pulse(self):
        if self._pulse_anim and self._pulse_anim.state() == QPropertyAnimation.Running:
            return
        self._pulse_anim = QPropertyAnimation(self, b"opacity")
        self._pulse_anim.setDuration(900)
        self._pulse_anim.setLoopCount(-1)
        self._pulse_anim.setStartValue(1.0)
        self._pulse_anim.setKeyValueAt(0.5, 0.25)
        self._pulse_anim.setEndValue(1.0)
        self._pulse_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._pulse_anim.start()

    def stop_pulse(self):
        if self._pulse_anim:
            self._pulse_anim.stop()
        self._opacity = 1.0
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        c = QColor(self._color)
        c.setAlphaF(self._opacity)
        p.setBrush(c)
        p.setPen(Qt.NoPen)
        p.drawEllipse(1, 1, 8, 8)
        p.end()


def _v_divider(palette) -> QFrame:
    f = QFrame()
    f.setFixedSize(1, 16)
    f.setObjectName("VDivider")
    f.setStyleSheet(f"#VDivider {{ background-color: {palette.border}; border: none; }}")
    return f


def _pill_label(text: str, bg: str, fg: str, border: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setFixedHeight(20)
    lbl.setStyleSheet(
        f"background-color: {bg}; color: {fg}; border: 1px solid {border}; "
        f"border-radius: 10px; padding: 0 8px; font-size: {FONT_SIZE.caption}px; "
        f"font-weight: 700; letter-spacing: 0.06em;"
    )
    return lbl


class StatusBar(QFrame):
    killRequested = Signal()

    def __init__(self, parent=None, theme: str = "dark"):
        super().__init__(parent)
        self._theme = theme
        self.setObjectName("StatusBarFrame")
        self.setFixedHeight(32)
        self._build_ui()
        self._apply_theme(theme)

        # clock timer
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._tick_clock)
        self._clock_timer.start(1000)
        self._tick_clock()

    def _build_ui(self):
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(12, 0, 12, 0)
        self._layout.setSpacing(10)

        # Left: dot + connection text + badges
        self._dot = DotIndicator()
        self._conn_label = QLabel("Connected")
        self._conn_label.setStyleSheet(f"font-size: {FONT_SIZE.caption}px; font-weight: 600; background: transparent; border: none;")

        p = get_palette(self._theme)
        self._mode_badge = _pill_label("DEMO", p.warning_soft, p.warning, p.warning + "30")
        self._env_badge = _pill_label("PAPER", p.surface, p.text_secondary, p.border)

        self._layout.addWidget(self._dot)
        self._layout.addWidget(self._conn_label)
        self._layout.addSpacing(2)
        self._layout.addWidget(self._mode_badge)
        self._layout.addWidget(self._env_badge)
        self._layout.addWidget(_v_divider(p))

        # Middle: balance | equity | today P/L
        self._balance_label = QLabel("Balance  $10,000.00")
        self._equity_label = QLabel("Equity  $10,124.50")
        self._pnl_label = QLabel("Today  ▲ $124.50")
        for lbl in (self._balance_label, self._equity_label, self._pnl_label):
            lbl.setStyleSheet(f"font-family: {FONT_MONO}; font-size: {FONT_SIZE.caption}px; font-feature-settings: 'tnum'; background: transparent; border: none;")
        self._pnl_label.setStyleSheet(f"font-family: {FONT_MONO}; font-size: {FONT_SIZE.caption}px; font-weight: 600; color: {p.profit}; background: transparent; border: none;")

        self._layout.addWidget(self._balance_label)
        self._layout.addWidget(_v_divider(p))
        self._layout.addWidget(self._equity_label)
        self._layout.addWidget(_v_divider(p))
        self._layout.addWidget(self._pnl_label)
        self._layout.addStretch(1)

        # Right: bot state | sync | clock | kill
        self._bot_label = QLabel("● Bot idle")
        self._bot_label.setStyleSheet(f"font-size: {FONT_SIZE.caption}px; color: {p.text_secondary}; background: transparent; border: none;")
        self._sync_label = QLabel("Synced just now")
        self._sync_label.setStyleSheet(f"font-size: {FONT_SIZE.caption}px; color: {p.text_tertiary}; background: transparent; border: none;")
        self._clock_label = QLabel("--:--:--")
        self._clock_label.setStyleSheet(
            f"font-family: {FONT_MONO}; font-size: {FONT_SIZE.caption}px; color: {p.text_secondary}; background: transparent; border: none; font-feature-settings: 'tnum';"
        )

        self._kill_btn = QPushButton("⬢ Kill Switch")
        self._kill_btn.setObjectName("DangerButton")
        self._kill_btn.setFixedHeight(24)
        self._kill_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._kill_btn.clicked.connect(self.killRequested.emit)

        p2 = get_palette(self._theme)
        self._layout.addWidget(self._bot_label)
        self._layout.addWidget(_v_divider(p2))
        self._layout.addWidget(self._sync_label)
        self._layout.addWidget(_v_divider(p2))
        self._layout.addWidget(self._clock_label)
        self._layout.addSpacing(4)
        self._layout.addWidget(self._kill_btn)

    def _apply_theme(self, theme: str):
        self._theme = theme
        p = get_palette(theme)
        self.setStyleSheet(f"#StatusBarFrame {{ background-color: {p.surface}; border-top: 1px solid {p.border}; border-left: none; border-right: none; border-bottom: none; }}")
        # refresh text colors
        self._conn_label.setStyleSheet(f"font-size: {FONT_SIZE.caption}px; font-weight: 600; color: {p.text}; background: transparent; border: none;")
        for lbl in (self._balance_label, self._equity_label):
            lbl.setStyleSheet(
                f"font-family: {FONT_MONO}; font-size: {FONT_SIZE.caption}px; color: {p.text_secondary}; font-feature-settings: 'tnum'; background: transparent; border: none;"
            )
        self._bot_label.setStyleSheet(f"font-size: {FONT_SIZE.caption}px; color: {p.text_secondary}; background: transparent; border: none;")
        self._sync_label.setStyleSheet(f"font-size: {FONT_SIZE.caption}px; color: {p.text_tertiary}; background: transparent; border: none;")
        self._clock_label.setStyleSheet(
            f"font-family: {FONT_MONO}; font-size: {FONT_SIZE.caption}px; color: {p.text_secondary}; background: transparent; border: none; font-feature-settings: 'tnum';"
        )

    # ── Public API ──
    def set_theme(self, theme: str):
        self._apply_theme(theme)

    def set_connection_state(self, state: str):
        """state: connected | connecting | disconnected | error"""
        p = get_palette(self._theme)
        s = state.lower()
        if s == "connected":
            self._dot.set_color(p.profit)
            self._dot.stop_pulse()
            self._conn_label.setText("Connected")
            self._conn_label.setStyleSheet(f"font-size: {FONT_SIZE.caption}px; font-weight: 600; color: {p.profit}; background: transparent; border: none;")
        elif s == "connecting":
            self._dot.set_color(p.warning)
            self._dot.start_pulse()
            self._conn_label.setText("Connecting…")
            self._conn_label.setStyleSheet(f"font-size: {FONT_SIZE.caption}px; font-weight: 600; color: {p.warning}; background: transparent; border: none;")
        elif s in ("disconnected", "offline"):
            self._dot.set_color(p.text_tertiary)
            self._dot.stop_pulse()
            self._conn_label.setText("Offline")
            self._conn_label.setStyleSheet(f"font-size: {FONT_SIZE.caption}px; font-weight: 600; color: {p.text_tertiary}; background: transparent; border: none;")
        else:  # error
            self._dot.set_color(p.loss)
            self._dot.stop_pulse()
            self._conn_label.setText("Error")
            self._conn_label.setStyleSheet(f"font-size: {FONT_SIZE.caption}px; font-weight: 600; color: {p.loss}; background: transparent; border: none;")

    def set_mode(self, mode: str):
        """DEMO / REAL"""
        p = get_palette(self._theme)
        m = mode.upper()
        self._mode_badge.setText(m)
        if m == "REAL":
            self._mode_badge.setStyleSheet(
                f"background-color: {p.profit_soft}; color: {p.profit}; border: 1px solid {p.profit}30; "
                f"border-radius: 10px; padding: 0 8px; font-size: {FONT_SIZE.caption}px; font-weight: 700; letter-spacing: 0.06em;"
            )
        else:
            self._mode_badge.setStyleSheet(
                f"background-color: {p.warning_soft}; color: {p.warning}; border: 1px solid {p.warning}30; "
                f"border-radius: 10px; padding: 0 8px; font-size: {FONT_SIZE.caption}px; font-weight: 700; letter-spacing: 0.06em;"
            )

    def set_balance(self, balance: float, equity: float, pnl: float):
        self._balance_label.setText(f"Balance  ${balance:,.2f}")
        self._equity_label.setText(f"Equity  ${equity:,.2f}")
        p = get_palette(self._theme)
        arrow = "▲" if pnl >= 0 else "▼"
        color = p.profit if pnl >= 0 else p.loss
        sign = "+" if pnl >= 0 else ""
        self._pnl_label.setText(f"Today  {arrow} {sign}${pnl:,.2f}")
        self._pnl_label.setStyleSheet(
            f"font-family: {FONT_MONO}; font-size: {FONT_SIZE.caption}px; font-weight: 700; color: {color}; background: transparent; border: none; font-feature-settings: 'tnum';"
        )

    def set_bot_state(self, text: str):
        self._bot_label.setText(f"● {text}")

    def set_sync_text(self, text: str):
        self._sync_label.setText(text)

    def _tick_clock(self):
        from datetime import datetime

        self._clock_label.setText(datetime.now().strftime("%H:%M:%S"))
