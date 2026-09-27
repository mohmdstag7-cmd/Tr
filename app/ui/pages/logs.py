"""
Premium Logs Page — left categories, center log stream with level left-border,
right filter card, bottom toolbar. Tabular timestamps, colored badges.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.ui.theme.tokens import FONT_MONO, FONT_SIZE, RADIUS, get_palette

LEVEL_COLORS = {
    "DEBUG": "#8B92A8",
    "INFO": "#38BDF8",
    "WARNING": "#F59E0B",
    "ERROR": "#EF4444",
    "CRITICAL": "#DC2626",
}

CATEGORIES = [
    ("All", "◫", 128),
    ("Trading", "⇄", 42),
    ("Signals", "✦", 31),
    ("Risk", "⚠", 12),
    ("System", "⚙", 28),
    ("Model", "◊", 15),
]


class LogEntryFrame(QFrame):
    def __init__(self, timestamp: str, level: str, category: str, message: str, theme: str = "dark", parent=None):
        super().__init__(parent)
        p = get_palette(theme)
        color = LEVEL_COLORS.get(level.upper(), p.text_tertiary)
        self.setStyleSheet(f"background-color: {p.card}; border: 1px solid {p.border}; " f"border-left: 3px solid {color}; border-radius: {RADIUS.md}px;")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(10)

        ts = QLabel(timestamp)
        ts.setFixedWidth(88)
        ts.setStyleSheet(
            f"font-family: {FONT_MONO}; font-size: {FONT_SIZE.caption}px; color: {p.text_tertiary}; background: transparent; border: none; font-feature-settings: 'tnum';"
        )

        badge = QLabel(level.upper())
        badge.setFixedHeight(20)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(
            f"background-color: {color}18; color: {color}; border: 1px solid {color}30; "
            f"border-radius: 10px; padding: 0 8px; font-size: 10px; font-weight: 700; letter-spacing: 0.06em;"
        )

        cat = QLabel(category)
        cat.setFixedWidth(72)
        cat.setStyleSheet(f"font-size: {FONT_SIZE.caption}px; font-weight: 600; color: {p.text_secondary}; background: transparent; border: none;")

        msg = QLabel(message)
        msg.setWordWrap(True)
        msg.setStyleSheet(f"font-size: {FONT_SIZE.body}px; color: {p.text}; background: transparent; border: none;")

        lay.addWidget(ts)
        lay.addWidget(badge)
        lay.addWidget(cat)
        lay.addWidget(msg, 1)


class LogsPage(QWidget):
    filterChanged = Signal(dict)

    def __init__(self, parent=None, theme: str = "dark"):
        super().__init__(parent)
        self._theme = theme
        self.setObjectName("PageRoot")
        self._build_ui()
        self._apply_theme(theme)

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(16)

        # — Title —
        title_row = QHBoxLayout()
        self._title = QLabel("Logs")
        self._title.setObjectName("PageTitle")
        self._subtitle = QLabel("System and trading event stream")
        p = get_palette(self._theme)
        self._subtitle.setStyleSheet(f"font-size: {FONT_SIZE.body}px; color: {p.text_secondary}; background: transparent; border: none;")
        title_row.addWidget(self._title)
        title_row.addWidget(self._subtitle)
        title_row.addStretch(1)
        # search
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search logs…")
        self._search.setFixedWidth(260)
        self._search.setObjectName("SearchInput")
        title_row.addWidget(self._search)
        outer.addLayout(title_row)

        # — Main 3-column area —
        main = QHBoxLayout()
        main.setSpacing(16)

        # Left: categories
        self._left_card = QFrame()
        self._left_card.setObjectName("CardFrame")
        self._left_card.setFixedWidth(200)
        left_lay = QVBoxLayout(self._left_card)
        left_lay.setContentsMargins(8, 8, 8, 8)
        left_lay.setSpacing(2)
        hdr = QLabel("CATEGORIES")
        hdr.setStyleSheet(
            f"font-size: {FONT_SIZE.caption}px; font-weight: 600; color: {p.text_tertiary}; letter-spacing: 0.08em; background: transparent; border: none; padding: 8px 8px 6px 8px;"  # noqa: E501
        )
        left_lay.addWidget(hdr)
        self._cat_list = QListWidget()
        self._cat_list.setFrameShape(QFrame.NoFrame)
        self._cat_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        for name, icon, count in CATEGORIES:
            item = QListWidgetItem(f"  {icon}    {name}    ·  {count}")
            item.setData(Qt.UserRole, name)
            self._cat_list.addItem(item)
        self._cat_list.setCurrentRow(0)
        self._cat_list.setFixedHeight(220)
        left_lay.addWidget(self._cat_list)
        left_lay.addStretch(1)
        main.addWidget(self._left_card)

        # Center: log stream
        center_wrap = QVBoxLayout()
        center_wrap.setSpacing(8)

        # scroll area for log entries
        self._log_scroll = QScrollArea()
        self._log_scroll.setWidgetResizable(True)
        self._log_scroll.setFrameShape(QFrame.NoFrame)
        self._log_scroll.setStyleSheet("background: transparent; border: none;")
        self._log_container = QWidget()
        self._log_container.setStyleSheet("background: transparent;")
        self._log_lay = QVBoxLayout(self._log_container)
        self._log_lay.setContentsMargins(0, 0, 4, 0)
        self._log_lay.setSpacing(8)

        # demo entries
        demo_logs = [
            ("12:04:31.042", "INFO", "Trading", "Order #4821 filled — BUY 0.10 XAUUSD @ 2034.12"),
            ("12:04:29.881", "WARNING", "Risk", "Daily loss approaching 60% of limit — $298 / $500"),
            ("12:03:15.102", "DEBUG", "System", "Heartbeat OK — latency 42ms"),
            ("12:02:44.330", "ERROR", "Signals", "Signal rejected — spread too wide (4.2 pips)"),
            ("12:01:08.550", "INFO", "Model", "Model inference completed — confidence 0.84"),
        ]
        for ts, lvl, cat, msg in demo_logs:
            self._log_lay.addWidget(LogEntryFrame(ts, lvl, cat, msg, theme=self._theme))
        self._log_lay.addStretch(1)
        self._log_scroll.setWidget(self._log_container)
        center_wrap.addWidget(self._log_scroll, 1)

        # Bottom toolbar
        toolbar = QFrame()
        toolbar.setObjectName("CardFrame")
        tb_lay = QHBoxLayout(toolbar)
        tb_lay.setContentsMargins(12, 8, 12, 8)
        tb_lay.setSpacing(8)
        for txt, obj in [("Clear", "GhostButton"), ("Export", "SecondaryButton"), ("Copy", "GhostButton")]:
            b = QPushButton(txt)
            b.setObjectName(obj)
            b.setFixedHeight(32)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            tb_lay.addWidget(b)
        tb_lay.addStretch(1)
        self._auto_scroll = QCheckBox("Auto-scroll")
        self._auto_scroll.setChecked(True)
        tb_lay.addWidget(self._auto_scroll)
        center_wrap.addWidget(toolbar)
        main.addLayout(center_wrap, 1)

        # Right: filters card
        self._right_card = QFrame()
        self._right_card.setObjectName("CardFrame")
        self._right_card.setFixedWidth(240)
        right_lay = QVBoxLayout(self._right_card)
        right_lay.setContentsMargins(16, 16, 16, 16)
        right_lay.setSpacing(14)
        rf_title = QLabel("FILTERS")
        rf_title.setStyleSheet(f"font-size: {FONT_SIZE.caption}px; font-weight: 600; color: {p.text_tertiary}; letter-spacing: 0.08em; background: transparent; border: none;")
        right_lay.addWidget(rf_title)

        def _filter_row(label: str, widget: QWidget):
            w = QWidget()
            w.setStyleSheet("background: transparent; border: none;")
            vlay = QVBoxLayout(w)
            vlay.setContentsMargins(0, 0, 0, 0)
            vlay.setSpacing(6)
            lb = QLabel(label)
            lb.setStyleSheet(f"font-size: {FONT_SIZE.caption}px; font-weight: 600; color: {p.text_secondary}; letter-spacing: 0.06em; background: transparent; border: none;")
            vlay.addWidget(lb)
            vlay.addWidget(widget)
            return w

        self._level_combo = QComboBox()
        self._level_combo.addItems(["All levels", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        right_lay.addWidget(_filter_row("LEVEL", self._level_combo))

        self._cat_combo = QComboBox()
        self._cat_combo.addItems(["All categories"] + [c[0] for c in CATEGORIES[1:]])
        right_lay.addWidget(_filter_row("CATEGORY", self._cat_combo))

        self._since_input = QLineEdit()
        self._since_input.setPlaceholderText("e.g. 2024-01-01")
        right_lay.addWidget(_filter_row("SINCE", self._since_input))

        self._tail_check = QCheckBox("Tail mode (follow)")
        self._tail_check.setChecked(True)
        right_lay.addWidget(self._tail_check)

        right_lay.addStretch(1)
        apply_btn = QPushButton("Apply Filters")
        apply_btn.setObjectName("PrimaryButton")
        apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        right_lay.addWidget(apply_btn)

        main.addWidget(self._right_card)
        outer.addLayout(main, 1)

    def _apply_theme(self, theme: str):
        self._theme = theme
        p = get_palette(theme)
        self.setStyleSheet(f"#PageRoot {{ background-color: {p.bg}; }}")
        self._title.setStyleSheet(f"font-size: {FONT_SIZE.hero}px; font-weight: 700; color: {p.text}; letter-spacing: -0.03em; background: transparent; border: none;")
        self._subtitle.setStyleSheet(f"font-size: {FONT_SIZE.body}px; color: {p.text_secondary}; background: transparent; border: none;")
        for card in (self._left_card, self._right_card):
            card.setStyleSheet(f"#CardFrame {{ background-color: {p.card}; border: 1px solid {p.border}; border-radius: {RADIUS.lg}px; }}")

    def set_theme(self, theme: str):
        self._apply_theme(theme)

    def add_log_entry(self, timestamp: str, level: str, category: str, message: str):
        # insert at top
        w = LogEntryFrame(timestamp, level, category, message, theme=self._theme)
        self._log_lay.insertWidget(0, w)
