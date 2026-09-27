"""Status bar with real MT5 data."""

from __future__ import annotations

import datetime as dt

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from app.mt5.types import AccountInfo, TerminalInfo


class StatusBar(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)

        self.dot = QLabel("●")
        self.dot.setStyleSheet("color: red; font-size: 14px;")
        layout.addWidget(self.dot)

        self.badge = QLabel("DISCONNECTED")
        self.badge.setStyleSheet("background: #6c757d; color: white; padding: 2px 6px; border-radius: 4px;")
        layout.addWidget(self.badge)

        self.broker_label = QLabel("—")
        layout.addWidget(self.broker_label)

        self.balance_label = QLabel("Balance: —")
        layout.addWidget(self.balance_label)

        self.equity_label = QLabel("Equity: —")
        layout.addWidget(self.equity_label)

        self.pnl_label = QLabel("P/L: —")
        layout.addWidget(self.pnl_label)

        layout.addStretch()

        self.clock_utc = QLabel("UTC --:--:--")
        layout.addWidget(self.clock_utc)

        self.clock_broker = QLabel("Broker --:--:--")
        layout.addWidget(self.clock_broker)

        self.kill_btn = QPushButton("Kill Switch")
        self.kill_btn.setStyleSheet("background: #dc3545; color: white; font-weight: bold;")
        layout.addWidget(self.kill_btn)

        # clocks
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick_clock)
        self._timer.start()
        self._broker_offset: int = 0

    def _tick_clock(self) -> None:
        now = dt.datetime.now(tz=dt.UTC)
        self.clock_utc.setText(f"UTC {now.strftime('%H:%M:%S')}")
        broker_now = now + dt.timedelta(seconds=self._broker_offset)
        self.clock_broker.setText(f"Broker {broker_now.strftime('%H:%M:%S')}")

    def on_account_info(self, account: AccountInfo) -> None:
        atype = account.account_type.upper()
        colors = {"DEMO": "#17a2b8", "REAL": "#28a745", "CONTEST": "#ffc107"}
        color = colors.get(atype, "#6c757d")
        self.badge.setText(atype)
        self.badge.setStyleSheet(f"background: {color}; color: white; padding: 2px 6px; border-radius: 4px;")
        self.broker_label.setText(account.company or account.server)
        self.balance_label.setText(f"Balance: {account.balance:.2f} {account.currency}")
        self.equity_label.setText(f"Equity: {account.equity:.2f}")
        # P/L today placeholder
        self.pnl_label.setText("P/L: —")

    def on_terminal_info(self, terminal: TerminalInfo) -> None:
        if terminal.connected:
            self.dot.setStyleSheet("color: #28a745; font-size: 14px;")
            self.badge.setToolTip("Connected")
        else:
            self.dot.setStyleSheet("color: #dc3545; font-size: 14px;")

    def set_reconnecting(self) -> None:
        self.dot.setStyleSheet("color: #ffc107; font-size: 14px;")

    def set_broker_offset(self, offset: int) -> None:
        self._broker_offset = offset
