"""
Premium Dashboard — KPI row, equity curve skeleton, positions & risk cards.
24px page margins, 16px section gaps, card-based layout, scrollable.
"""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from app.ui.theme.tokens import FONT_MONO, FONT_SIZE, RADIUS, get_palette
from app.ui.widgets.kpi_card import KpiCard


class SkeletonBar(QFrame):
    """Shimmer skeleton bar — animated opacity pulse."""

    def __init__(self, w: int = 120, h: int = 12, radius: int = 6, parent=None):
        super().__init__(parent)
        self.setFixedSize(w, h)
        self.setObjectName("Skeleton")
        self._opacity = 0.6
        self._anim = QPropertyAnimation(self, b"windowOpacity")
        self._anim.setDuration(1200)
        self._anim.setLoopCount(-1)
        self._anim.setStartValue(0.6)
        self._anim.setKeyValueAt(0.5, 1.0)
        self._anim.setEndValue(0.6)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        # Use style opacity via stylesheet animation fallback: timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._pulse)
        self._timer.start(80)
        self._phase = 0

    def _pulse(self):
        import math

        self._phase = (self._phase + 1) % 100
        v = 0.55 + 0.35 * (0.5 + 0.5 * math.sin(self._phase * 0.2))
        self.setStyleSheet(f"#Skeleton {{ background-color: rgba(120,130,150,{v:.2f}); border-radius: {6}px; border: none; }}")


def _card_frame(theme: str = "dark") -> QFrame:
    f = QFrame()
    f.setObjectName("CardFrame")
    p = get_palette(theme)
    f.setStyleSheet(f"#CardFrame {{ background-color: {p.card}; border: 1px solid {p.border}; border-radius: {RADIUS.lg}px; }}")
    return f


def _section_header(title: str, subtitle: str | None = None, theme: str = "dark") -> QWidget:
    p = get_palette(theme)
    w = QWidget()
    w.setStyleSheet("background: transparent;")
    lay = QHBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(8)
    t = QLabel(title)
    t.setStyleSheet(f"font-size: {FONT_SIZE.subtitle}px; font-weight: 600; color: {p.text}; letter-spacing: -0.01em; background: transparent; border: none;")
    lay.addWidget(t)
    if subtitle:
        s = QLabel(subtitle)
        s.setStyleSheet(f"font-size: {FONT_SIZE.caption}px; color: {p.text_tertiary}; background: transparent; border: none;")
        lay.addWidget(s)
    lay.addStretch(1)
    return w


class DashboardPage(QWidget):
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

        # — Page title —
        title_row = QHBoxLayout()
        title_row.setSpacing(12)
        self._title = QLabel("Dashboard")
        self._title.setObjectName("PageTitle")
        self._subtitle = QLabel("Overview of your trading activity")
        p = get_palette(self._theme)
        self._subtitle.setStyleSheet(f"font-size: {FONT_SIZE.body}px; color: {p.text_secondary}; background: transparent; border: none;")
        title_row.addWidget(self._title)
        title_row.addWidget(self._subtitle)
        title_row.addStretch(1)
        lay.addLayout(title_row)

        # — KPI row —
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(16)
        self._kpi_balance = KpiCard("Balance", "$10,000.00", "+2.4% today", True, theme=self._theme)
        self._kpi_pnl = KpiCard("Today P/L", "+$124.50", "+1.24%", True, theme=self._theme)
        self._kpi_risk = KpiCard("Open Risk", "$342.00", "3 positions", None, theme=self._theme)
        for k in (self._kpi_balance, self._kpi_pnl, self._kpi_risk):
            k.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            kpi_row.addWidget(k)
        lay.addLayout(kpi_row)

        # — Equity curve placeholder —
        self._equity_card = _card_frame(self._theme)
        ec_lay = QVBoxLayout(self._equity_card)
        ec_lay.setContentsMargins(20, 20, 20, 20)
        ec_lay.setSpacing(16)
        ec_lay.addWidget(_section_header("Equity Curve", "Last 30 days", self._theme))

        # skeleton shimmer area
        skel_wrap = QFrame()
        skel_wrap.setStyleSheet("background: transparent; border: none;")
        skel_lay = QVBoxLayout(skel_wrap)
        skel_lay.setContentsMargins(0, 8, 0, 0)
        skel_lay.setSpacing(10)
        # fake chart skeleton: rows of bars
        for widths in [(320, 180, 240), (260, 300, 200), (340, 160, 220)]:
            row = QHBoxLayout()
            row.setSpacing(10)
            for w in widths:
                row.addWidget(SkeletonBar(w=w, h=10))
            row.addStretch(1)
            skel_lay.addLayout(row)
        hint = QLabel("Equity curve will appear here  •  Connect to MT5 to load data")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet(f"font-size: {FONT_SIZE.caption}px; color: {p.text_tertiary}; background: transparent; border: none; padding-top: 8px;")
        skel_lay.addWidget(hint)
        ec_lay.addWidget(skel_wrap)
        lay.addWidget(self._equity_card)

        # — Two-column row: Open Positions + Risk Limits —
        two_col = QHBoxLayout()
        two_col.setSpacing(16)

        # Open positions card
        self._pos_card = _card_frame(self._theme)
        pos_lay = QVBoxLayout(self._pos_card)
        pos_lay.setContentsMargins(20, 20, 20, 20)
        pos_lay.setSpacing(12)
        pos_lay.addWidget(_section_header("Open Positions", "3 active", self._theme))
        self._pos_table = QTableWidget(0, 5)
        self._pos_table.setHorizontalHeaderLabels(["Symbol", "Type", "Volume", "P/L", "Status"])
        self._pos_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._pos_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self._pos_table.verticalHeader().setVisible(False)
        self._pos_table.setAlternatingRowColors(True)
        self._pos_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._pos_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._pos_table.setFixedHeight(140)
        self._pos_table.setShowGrid(False)
        # empty state row hint inside table area
        pos_lay.addWidget(self._pos_table)
        empty_lbl = QLabel("No open positions — signals will appear here when active")
        empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_lbl.setStyleSheet(f"font-size: {FONT_SIZE.caption}px; color: {p.text_tertiary}; background: transparent; border: none; padding: 4px;")
        pos_lay.addWidget(empty_lbl)
        two_col.addWidget(self._pos_card, 3)

        # Risk limits card
        self._risk_card = _card_frame(self._theme)
        risk_lay = QVBoxLayout(self._risk_card)
        risk_lay.setContentsMargins(20, 20, 20, 20)
        risk_lay.setSpacing(14)
        risk_lay.addWidget(_section_header("Risk Limits", None, self._theme))
        for label, val, pct in [
            ("Daily loss", "$124 / $500", 25),
            ("Open exposure", "$342 / $1,000", 34),
            ("Drawdown", "1.2% / 5.0%", 24),
        ]:
            row_w = QWidget()
            row_w.setStyleSheet("background: transparent; border: none;")
            rl = QVBoxLayout(row_w)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.setSpacing(6)
            top = QHBoxLayout()
            top.setContentsMargins(0, 0, 0, 0)
            lbl = QLabel(label)
            lbl.setStyleSheet(
                f"font-size: {FONT_SIZE.caption}px; font-weight: 600; color: {p.text_secondary}; letter-spacing: 0.06em; text-transform: uppercase; background: transparent; border: none;"  # noqa: E501
            )
            v = QLabel(val)
            v.setStyleSheet(f"font-family: {FONT_MONO}; font-size: {FONT_SIZE.caption}px; color: {p.text}; font-feature-settings: 'tnum'; background: transparent; border: none;")
            top.addWidget(lbl)
            top.addStretch(1)
            top.addWidget(v)
            rl.addLayout(top)
            bar = QProgressBar()
            bar.setFixedHeight(6)
            bar.setTextVisible(False)
            bar.setValue(pct)
            if pct > 80:
                bar.setObjectName("LossBar")
            elif pct > 60:
                bar.setObjectName("WarningBar")
            rl.addWidget(bar)
            risk_lay.addWidget(row_w)
        risk_lay.addStretch(1)
        two_col.addWidget(self._risk_card, 2)

        lay.addLayout(two_col)
        lay.addStretch(1)

        scroll.setWidget(container)
        outer.addWidget(scroll)

    def _apply_theme(self, theme: str):
        self._theme = theme
        p = get_palette(theme)
        self.setStyleSheet(f"#PageRoot {{ background-color: {p.bg}; }}")
        self._container.setStyleSheet(f"background-color: {p.bg};")
        self._title.setStyleSheet(f"font-size: {FONT_SIZE.hero}px; font-weight: 700; color: {p.text}; letter-spacing: -0.03em; background: transparent; border: none;")
        self._subtitle.setStyleSheet(f"font-size: {FONT_SIZE.body}px; color: {p.text_secondary}; background: transparent; border: none;")
        for k in (self._kpi_balance, self._kpi_pnl, self._kpi_risk):
            k.set_theme(theme)
        for card in (self._equity_card, self._pos_card, self._risk_card):
            card.setStyleSheet(f"#CardFrame {{ background-color: {p.card}; border: 1px solid {p.border}; border-radius: {RADIUS.lg}px; }}")

    def set_theme(self, theme: str):
        self._apply_theme(theme)

    # Public updaters for live data
    def set_kpis(self, balance: float, pnl: float, risk: float):
        self._kpi_balance.set_numeric(balance, prefix="$")
        self._kpi_pnl.set_numeric(pnl, prefix="$", delta=pnl, delta_suffix="")
        self._kpi_risk.set_value(f"${risk:,.2f}")
