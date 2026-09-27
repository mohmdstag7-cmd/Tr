"""
Premium Health Page — summary card, checks table with status icons,
performance metrics with progress bars, debug bundle action.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.ui.theme.tokens import FONT_MONO, FONT_SIZE, RADIUS, get_palette

STATUS_CFG = {
    "ok": ("✓", "#22C55E", "Healthy"),
    "warn": ("⚠", "#F59E0B", "Degraded"),
    "error": ("✗", "#EF4444", "Critical"),
    "unknown": ("?", "#8B92A8", "Unknown"),
}


def _card(theme: str) -> QFrame:
    f = QFrame()
    f.setObjectName("CardFrame")
    p = get_palette(theme)
    f.setStyleSheet(f"#CardFrame {{ background-color: {p.card}; border: 1px solid {p.border}; border-radius: {RADIUS.lg}px; }}")
    return f


class HealthPage(QWidget):
    debugBundleRequested = Signal()
    refreshRequested = Signal()

    def __init__(self, parent=None, theme: str = "dark"):
        super().__init__(parent)
        self._theme = theme
        self.setObjectName("PageRoot")
        self._build_ui()
        self._apply_theme(theme)

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent; border: none;")

        container = QWidget()
        container.setObjectName("PageRoot")
        self._container = container
        lay = QVBoxLayout(container)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(16)

        # — Title —
        title_row = QHBoxLayout()
        self._title = QLabel("Health")
        self._title.setObjectName("PageTitle")
        self._subtitle = QLabel("System diagnostics and performance")
        p = get_palette(self._theme)
        self._subtitle.setStyleSheet(f"font-size: {FONT_SIZE.body}px; color: {p.text_secondary}; background: transparent; border: none;")
        title_row.addWidget(self._title)
        title_row.addWidget(self._subtitle)
        title_row.addStretch(1)
        refresh_btn = QPushButton("↻ Refresh")
        refresh_btn.setObjectName("SecondaryButton")
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.clicked.connect(self.refreshRequested.emit)
        title_row.addWidget(refresh_btn)
        lay.addLayout(title_row)

        # — Summary card —
        self._summary_card = _card(self._theme)
        s_lay = QHBoxLayout(self._summary_card)
        s_lay.setContentsMargins(20, 20, 20, 20)
        s_lay.setSpacing(16)

        # status icon circle
        self._summary_icon = QLabel("✓")
        self._summary_icon.setFixedSize(48, 48)
        self._summary_icon.setAlignment(Qt.AlignCenter)
        self._summary_icon.setStyleSheet(
            f"background-color: {p.profit_soft}; color: {p.profit}; border-radius: 24px; font-size: 22px; font-weight: 700; border: 1px solid {p.profit}30;"
        )
        s_lay.addWidget(self._summary_icon)

        txt_col = QVBoxLayout()
        txt_col.setSpacing(4)
        self._summary_title = QLabel("All systems operational")
        self._summary_title.setStyleSheet(f"font-size: {FONT_SIZE.subtitle}px; font-weight: 600; color: {p.text}; background: transparent; border: none;")
        self._summary_desc = QLabel("8 checks passed  •  Last checked just now  •  Uptime 3d 14h")
        self._summary_desc.setStyleSheet(f"font-size: {FONT_SIZE.body}px; color: {p.text_secondary}; background: transparent; border: none;")
        txt_col.addWidget(self._summary_title)
        txt_col.addWidget(self._summary_desc)
        s_lay.addLayout(txt_col, 1)

        self._overall_badge = QLabel("HEALTHY")
        self._overall_badge.setAlignment(Qt.AlignCenter)
        self._overall_badge.setFixedHeight(28)
        self._overall_badge.setStyleSheet(
            f"background-color: {p.profit_soft}; color: {p.profit}; border: 1px solid {p.profit}30; "
            f"border-radius: 14px; padding: 0 14px; font-size: {FONT_SIZE.caption}px; font-weight: 700; letter-spacing: 0.08em;"
        )
        s_lay.addWidget(self._overall_badge)
        lay.addWidget(self._summary_card)

        # — Checks table —
        self._checks_card = _card(self._theme)
        c_lay = QVBoxLayout(self._checks_card)
        c_lay.setContentsMargins(20, 20, 20, 20)
        c_lay.setSpacing(12)
        hdr = QLabel("CHECKS")
        hdr.setStyleSheet(f"font-size: {FONT_SIZE.caption}px; font-weight: 600; color: {p.text_tertiary}; letter-spacing: 0.08em; background: transparent; border: none;")
        c_lay.addWidget(hdr)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["Check", "Status", "Latency", "Message"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setShowGrid(False)
        self._table.setFixedHeight(260)
        self._populate_checks()
        c_lay.addWidget(self._table)
        lay.addWidget(self._checks_card)

        # — Performance metrics —
        perf_row = QHBoxLayout()
        perf_row.setSpacing(16)
        for title, value, pct, color_key in [
            ("CPU", "24%", 24, "accent"),
            ("Memory", "1.2 GB / 4.0 GB", 30, "accent"),
            ("Event loop lag", "8 ms", 16, "profit"),
            ("MT5 latency", "42 ms", 42, "warning"),
        ]:
            card = _card(self._theme)
            cl = QVBoxLayout(card)
            cl.setContentsMargins(16, 16, 16, 16)
            cl.setSpacing(10)
            t = QLabel(title.upper())
            t.setStyleSheet(f"font-size: {FONT_SIZE.caption}px; font-weight: 600; color: {p.text_secondary}; letter-spacing: 0.08em; background: transparent; border: none;")
            v = QLabel(value)
            v.setStyleSheet(
                f"font-family: {FONT_MONO}; font-size: {FONT_SIZE.subtitle}px; font-weight: 600; color: {p.text}; font-feature-settings: 'tnum'; background: transparent; border: none;"  # noqa: E501
            )
            bar = QProgressBar()
            bar.setFixedHeight(6)
            bar.setTextVisible(False)
            bar.setValue(pct)
            if color_key == "warning":
                bar.setObjectName("WarningBar")
            elif color_key == "profit":
                bar.setObjectName("ProfitBar")
            cl.addWidget(t)
            cl.addWidget(v)
            cl.addWidget(bar)
            card.setMinimumWidth(160)
            perf_row.addWidget(card)
        lay.addLayout(perf_row)

        # — Debug bundle —
        self._debug_card = _card(self._theme)
        d_lay = QHBoxLayout(self._debug_card)
        d_lay.setContentsMargins(20, 16, 20, 16)
        d_lay.setSpacing(12)
        d_icon = QLabel("⬢")
        d_icon.setStyleSheet(f"font-size: 18px; color: {p.text_tertiary}; background: transparent; border: none;")
        d_lay.addWidget(d_icon)
        d_text = QVBoxLayout()
        d_text.setSpacing(2)
        d_title = QLabel("Debug bundle")
        d_title.setStyleSheet(f"font-size: {FONT_SIZE.body}px; font-weight: 600; color: {p.text}; background: transparent; border: none;")
        d_desc = QLabel("Collect logs, config and diagnostics into a zip for support")
        d_desc.setStyleSheet(f"font-size: {FONT_SIZE.caption}px; color: {p.text_secondary}; background: transparent; border: none;")
        d_text.addWidget(d_title)
        d_text.addWidget(d_desc)
        d_lay.addLayout(d_text, 1)
        self._debug_btn = QPushButton("Create Debug Bundle")
        self._debug_btn.setObjectName("DangerButton")
        self._debug_btn.setCursor(Qt.PointingHandCursor)
        self._debug_btn.clicked.connect(self.debugBundleRequested.emit)
        d_lay.addWidget(self._debug_btn)
        lay.addWidget(self._debug_card)

        lay.addStretch(1)
        scroll.setWidget(container)
        outer.addWidget(scroll)

    def _populate_checks(self):
        checks = [
            ("MT5 Connection", "ok", "42 ms", "Connected to demo server"),
            ("Data Feed", "ok", "18 ms", "Ticks flowing"),
            ("Risk Engine", "ok", "2 ms", "Limits enforced"),
            ("Model Service", "warn", "210 ms", "High latency — consider restart"),
            ("Disk Space", "ok", "—", "78% free"),
            ("Permissions", "ok", "—", "All required permissions granted"),
            ("Network", "ok", "12 ms", "Stable"),
            ("Clock Sync", "ok", "—", "NTP synchronized"),
        ]
        self._table.setRowCount(len(checks))
        for i, (name, status, latency, msg) in enumerate(checks):
            icon, color, label = STATUS_CFG.get(status, STATUS_CFG["unknown"])
            # Check name
            it0 = QTableWidgetItem(f"  {name}")
            it0.setFlags(it0.flags() & ~Qt.ItemIsEditable)
            self._table.setItem(i, 0, it0)
            # Status with icon
            it1 = QTableWidgetItem(f"{icon}  {label}")
            it1.setForeground(QColor(color))
            it1.setFlags(it1.flags() & ~Qt.ItemIsEditable)
            self._table.setItem(i, 1, it1)
            # Latency mono
            it2 = QTableWidgetItem(latency)
            it2.setFlags(it2.flags() & ~Qt.ItemIsEditable)
            self._table.setItem(i, 2, it2)
            # Message
            it3 = QTableWidgetItem(msg)
            it3.setFlags(it3.flags() & ~Qt.ItemIsEditable)
            self._table.setItem(i, 3, it3)

    def _apply_theme(self, theme: str):
        self._theme = theme
        p = get_palette(theme)
        self.setStyleSheet(f"#PageRoot {{ background-color: {p.bg}; }}")
        self._container.setStyleSheet(f"background-color: {p.bg};")
        self._title.setStyleSheet(f"font-size: {FONT_SIZE.hero}px; font-weight: 700; color: {p.text}; letter-spacing: -0.03em; background: transparent; border: none;")
        self._subtitle.setStyleSheet(f"font-size: {FONT_SIZE.body}px; color: {p.text_secondary}; background: transparent; border: none;")
        for card in (self._summary_card, self._checks_card, self._debug_card):
            card.setStyleSheet(f"#CardFrame {{ background-color: {p.card}; border: 1px solid {p.border}; border-radius: {RADIUS.lg}px; }}")

    def set_theme(self, theme: str):
        self._apply_theme(theme)

    def set_overall_status(self, status: str):
        """status: ok | warn | error"""
        get_palette(self._theme)
        icon, color, label = STATUS_CFG.get(status, STATUS_CFG["unknown"])
        self._summary_icon.setText(icon)
        self._summary_icon.setStyleSheet(f"background-color: {color}18; color: {color}; border-radius: 24px; font-size: 22px; font-weight: 700; border: 1px solid {color}30;")
        self._overall_badge.setText(label.upper())
        self._overall_badge.setStyleSheet(
            f"background-color: {color}18; color: {color}; border: 1px solid {color}30; "
            f"border-radius: 14px; padding: 0 14px; font-size: {FONT_SIZE.caption}px; font-weight: 700; letter-spacing: 0.08em;"
        )
