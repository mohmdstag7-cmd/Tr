"""
Market Page — Watchlist, Live tick table, Analysis card, MTF matrix, Session clock
Replaces stub per Phase 5 spec.
"""

from __future__ import annotations

from datetime import UTC, datetime

try:
    from PyQt5.QtCore import Qt, QTimer
    from PyQt5.QtWidgets import (
        QGroupBox,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QListWidget,
        QListWidgetItem,
        QSplitter,
        QTableWidget,
        QTableWidgetItem,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )

    QT_AVAILABLE = True
except ImportError:
    try:
        from PySide6.QtCore import Qt, QTimer
        from PySide6.QtWidgets import (
            QGroupBox,
            QHBoxLayout,
            QHeaderView,
            QLabel,
            QListWidget,
            QListWidgetItem,
            QSplitter,
            QTableWidget,
            QTableWidgetItem,
            QTextEdit,
            QVBoxLayout,
            QWidget,
        )

        QT_AVAILABLE = True
    except ImportError:
        QT_AVAILABLE = False
        QWidget = object  # type: ignore

from app.analysis.analysis_card import AnalysisCard
from app.analysis.sessions import SessionClock


class MarketPage(QWidget):
    """
    Working Market page with:
      - Watchlist (QListWidget)
      - Live tick table (symbol, bid, ask, spread, time — updates via QTimer)
      - Analysis card area
      - MTF trend matrix display
      - Session clock display
    """

    def __init__(self, symbols: list[str] | None = None, parent=None):
        if not QT_AVAILABLE:
            self.symbols = symbols or ["EURUSD", "GBPUSD", "XAUUSD", "USDJPY"]
            return
        super().__init__(parent)
        self.symbols = symbols or ["EURUSD", "GBPUSD", "XAUUSD", "USDJPY", "EURJPY", "AUDUSD"]
        self.ticks: dict[str, dict] = {s: {"bid": 0.0, "ask": 0.0, "time": ""} for s in self.symbols}
        self.analysis_texts: dict[str, str] = {}
        self.mtf_data: dict[str, dict] = {}

        self.session_clock = SessionClock()
        self.analysis_card = AnalysisCard()

        self._init_ui()
        self._init_timer()

    def _init_ui(self):
        layout = QHBoxLayout(self)

        splitter = QSplitter(Qt.Horizontal)

        # Left: Watchlist
        left_box = QGroupBox("Watchlist")
        left_layout = QVBoxLayout(left_box)
        self.watchlist = QListWidget()
        for sym in self.symbols:
            item = QListWidgetItem(sym)
            self.watchlist.addItem(item)
        self.watchlist.currentTextChanged.connect(self._on_symbol_selected)
        left_layout.addWidget(self.watchlist)
        # Session clock
        self.session_label = QLabel("Session: --")
        self.session_label.setStyleSheet("font-weight: bold; padding: 4px;")
        left_layout.addWidget(self.session_label)
        splitter.addWidget(left_box)

        # Center: Tick table + MTF matrix
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)

        tick_box = QGroupBox("Live Ticks")
        tick_layout = QVBoxLayout(tick_box)
        self.tick_table = QTableWidget(len(self.symbols), 5)
        self.tick_table.setHorizontalHeaderLabels(["Symbol", "Bid", "Ask", "Spread", "Time"])
        header = self.tick_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        self.tick_table.verticalHeader().setVisible(False)
        for i, sym in enumerate(self.symbols):
            self.tick_table.setItem(i, 0, QTableWidgetItem(sym))
            self.tick_table.setItem(i, 1, QTableWidgetItem("-"))
            self.tick_table.setItem(i, 2, QTableWidgetItem("-"))
            self.tick_table.setItem(i, 3, QTableWidgetItem("-"))
            self.tick_table.setItem(i, 4, QTableWidgetItem("-"))
        tick_layout.addWidget(self.tick_table)
        center_layout.addWidget(tick_box)

        mtf_box = QGroupBox("MTF Trend Matrix")
        mtf_layout = QVBoxLayout(mtf_box)
        self.mtf_table = QTableWidget(1, 7)
        self.mtf_table.setHorizontalHeaderLabels(["Symbol", "M5", "M15", "M30", "H1", "H4", "Bias"])
        self.mtf_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.mtf_table.verticalHeader().setVisible(False)
        mtf_layout.addWidget(self.mtf_table)
        self.bias_label = QLabel("Bias: --")
        mtf_layout.addWidget(self.bias_label)
        center_layout.addWidget(mtf_box)

        splitter.addWidget(center_widget)

        # Right: Analysis card
        right_box = QGroupBox("Analysis Card")
        right_layout = QVBoxLayout(right_box)
        self.analysis_area = QTextEdit()
        self.analysis_area.setReadOnly(True)
        self.analysis_area.setPlaceholderText("Select a symbol to view analysis...")
        right_layout.addWidget(self.analysis_area)
        splitter.addWidget(right_box)

        splitter.setSizes([150, 400, 350])
        layout.addWidget(splitter)

        # select first
        if self.symbols:
            self.watchlist.setCurrentRow(0)

    def _init_timer(self):
        if not QT_AVAILABLE:
            return
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_timer)
        self.timer.start(1000)  # 1s updates

    def _on_timer(self):
        # update session clock
        now = datetime.now(UTC)
        info = self.session_clock.current_session(now)
        mins = int(info.time_remaining.total_seconds() // 60)
        self.session_label.setText(f"Session: {info.name} ({mins}m left)")

        # simulate tick updates if no real gateway
        self._update_tick_table()

    def _update_tick_table(self):
        import random

        now_str = datetime.now(UTC).strftime("%H:%M:%S")
        for i, sym in enumerate(self.symbols):
            # if ticks not set, generate synthetic
            if self.ticks[sym]["bid"] == 0:
                base = 1.08 if "EUR" in sym else 2000 if "XAU" in sym else 150 if "JPY" in sym else 1.25
                bid = base + random.uniform  # noqa: S311(-0.001, 0.001)
                ask = bid + random.uniform  # noqa: S311(0.0001, 0.0003)
            else:
                bid = self.ticks[sym]["bid"] + random.uniform  # noqa: S311(-0.0002, 0.0002)
                ask = bid + abs(self.ticks[sym]["ask"] - self.ticks[sym]["bid"])
            self.ticks[sym] = {"bid": bid, "ask": ask, "time": now_str}
            spread = ask - bid
            self.tick_table.item(i, 1).setText(f"{bid:.5f}")
            self.tick_table.item(i, 2).setText(f"{ask:.5f}")
            self.tick_table.item(i, 3).setText(f"{spread:.5f}")
            self.tick_table.item(i, 4).setText(now_str)

    def update_ticks(self, tick_dict: dict[str, dict]):
        """External update from MT5 gateway: {symbol: {bid, ask, time}}"""
        for sym, data in tick_dict.items():
            if sym in self.ticks:
                self.ticks[sym] = data
        if QT_AVAILABLE and hasattr(self, "tick_table"):
            for i, sym in enumerate(self.symbols):
                if sym in tick_dict:
                    d = tick_dict[sym]
                    self.tick_table.item(i, 1).setText(f"{d.get('bid', 0):.5f}")
                    self.tick_table.item(i, 2).setText(f"{d.get('ask', 0):.5f}")
                    spread = d.get("ask", 0) - d.get("bid", 0)
                    self.tick_table.item(i, 3).setText(f"{spread:.5f}")
                    self.tick_table.item(i, 4).setText(str(d.get("time", "")))

    def update_analysis(self, symbol: str, text: str, mtf_result=None):
        self.analysis_texts[symbol] = text
        if QT_AVAILABLE and self.watchlist.currentItem() and self.watchlist.currentItem().text() == symbol:
            self.analysis_area.setPlainText(text)
        if mtf_result and QT_AVAILABLE:
            self._update_mtf_display(symbol, mtf_result)

    def _update_mtf_display(self, symbol: str, mtf_result):
        # update MTF table row for symbol
        # find or create row
        rows = self.mtf_table.rowCount()
        target_row = None
        for r in range(rows):
            if self.mtf_table.item(r, 0) and self.mtf_table.item(r, 0).text() == symbol:
                target_row = r
                break
        if target_row is None:
            target_row = rows
            self.mtf_table.insertRow(target_row)
        self.mtf_table.setItem(target_row, 0, QTableWidgetItem(symbol))
        # we display M5-H4 + Bias (7 cols: Symbol, M5, M15, M30, H1, H4, Bias)
        display_tfs = ["M5", "M15", "M30", "H1", "H4"]
        per_tf = getattr(mtf_result, "per_tf", {}) if hasattr(mtf_result, "per_tf") else {}
        for col, tf in enumerate(display_tfs, start=1):
            if tf in per_tf:
                trend = per_tf[tf]
                txt = f"{trend.direction[:4]} ({trend.strength})"
            else:
                txt = "-"
            self.mtf_table.setItem(target_row, col, QTableWidgetItem(txt))
        bias = getattr(mtf_result, "bias_score", 0)
        self.mtf_table.setItem(target_row, 6, QTableWidgetItem(str(bias)))
        self.bias_label.setText(f"Bias: {bias} — {getattr(mtf_result, 'reason', '')}")

    def _on_symbol_selected(self, symbol: str):
        if not symbol:
            return
        text = self.analysis_texts.get(symbol, f"{symbol} — No analysis yet. Waiting for market data...")
        if QT_AVAILABLE:
            self.analysis_area.setPlainText(text)
