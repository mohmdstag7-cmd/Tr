"""Status bar widget — Phase 1."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.ui.i18n import tr
from app.ui.theme.tokens import get_tokens
from app.ui.widgets import Badge


class StatusBar(QFrame):
    """Rich status bar with simple-mode collapse."""

    kill_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("StatusBar")
        self._simple_mode = False
        self._connected = False

        tokens = get_tokens("dark")
        try:
            pad = int(getattr(getattr(tokens, "spacing", None), "sm", 8))  # type: ignore[arg-type]
        except Exception:
            pad = 8

        self.setFrameShape(QFrame.Shape.StyledPanel)

        self._stack_layout = QVBoxLayout(self)
        self._stack_layout.setContentsMargins(pad, 4, pad, 4)
        self._stack_layout.setSpacing(0)

        # --- Detailed mode container ---
        self._detailed = QFrame(self)
        self._detailed.setObjectName("StatusBarDetailed")
        d_layout = QHBoxLayout(self._detailed)
        d_layout.setContentsMargins(0, 0, 0, 0)
        d_layout.setSpacing(pad)

        # Connection dot
        self.dot = QLabel("●", self._detailed)
        self.dot.setObjectName("ConnectionDot")
        self.dot.setStyleSheet("color: #888; font-size: 10px;")
        self.dot.setToolTip(tr("status.disconnected", default="Disconnected"))
        d_layout.addWidget(self.dot)

        # DEMO/REAL badge
        self.badge_account = Badge(text="DEMO", parent=self._detailed)  # type: ignore[call-arg]
        d_layout.addWidget(self.badge_account)

        # Mode badge
        self.badge_mode = Badge(text="Paper", parent=self._detailed)  # type: ignore[call-arg]
        d_layout.addWidget(self.badge_mode)

        # Balance / Equity / Today P/L
        self.lbl_balance = QLabel(tr("status.balance", default="Balance: —"), self._detailed)
        self.lbl_balance.setObjectName("StatusBalance")
        self.lbl_balance.setStyleSheet("font-variant-numeric: tabular-nums;")
        d_layout.addWidget(self.lbl_balance)

        self.lbl_equity = QLabel(tr("status.equity", default="Equity: —"), self._detailed)
        self.lbl_equity.setObjectName("StatusEquity")
        self.lbl_equity.setStyleSheet("font-variant-numeric: tabular-nums;")
        d_layout.addWidget(self.lbl_equity)

        self.lbl_today = QLabel(tr("status.today_pnl", default="Today: —"), self._detailed)
        self.lbl_today.setObjectName("StatusTodayPnl")
        self.lbl_today.setStyleSheet("font-variant-numeric: tabular-nums;")
        d_layout.addWidget(self.lbl_today)

        # DD bar
        self.dd_bar = QProgressBar(self._detailed)
        self.dd_bar.setObjectName("StatusDdBar")
        self.dd_bar.setRange(0, 100)
        self.dd_bar.setValue(0)
        self.dd_bar.setFixedWidth(80)
        self.dd_bar.setFixedHeight(10)
        self.dd_bar.setTextVisible(False)
        self.dd_bar.setToolTip(tr("status.drawdown", default="Drawdown"))
        d_layout.addWidget(self.dd_bar)
        self.lbl_dd = QLabel("DD 0.0%", self._detailed)
        self.lbl_dd.setObjectName("StatusDdLabel")
        d_layout.addWidget(self.lbl_dd)

        self.lbl_risk = QLabel(tr("status.open_risk", default="Risk: —"), self._detailed)
        d_layout.addWidget(self.lbl_risk)

        self.lbl_bot = QLabel(tr("status.bot_stopped", default="Stopped"), self._detailed)
        self.lbl_bot.setObjectName("StatusBotState")
        d_layout.addWidget(self.lbl_bot)

        self.lbl_sync = QLabel("● " + tr("status.sync_idle", default="Idle"), self._detailed)
        self.lbl_sync.setObjectName("StatusSync")
        d_layout.addWidget(self.lbl_sync)

        self.lbl_clock = QLabel("--:--", self._detailed)
        self.lbl_clock.setObjectName("StatusClock")
        d_layout.addWidget(self.lbl_clock)

        self.lbl_news = QLabel(tr("status.no_news", default="No news"), self._detailed)
        self.lbl_news.setObjectName("StatusNews")
        d_layout.addWidget(self.lbl_news)

        d_layout.addStretch(1)

        self.btn_kill = QPushButton(tr("status.kill_switch", default="Kill switch"), self._detailed)
        self.btn_kill.setObjectName("KillSwitchButton")
        self.btn_kill.setStyleSheet("color: #c0392b; border: 1px solid #c0392b; padding: 2px 8px;")
        self.btn_kill.clicked.connect(self.kill_requested.emit)
        d_layout.addWidget(self.btn_kill)

        # --- Simple mode container ---
        self._simple = QFrame(self)
        self._simple.setObjectName("StatusBarSimple")
        s_layout = QHBoxLayout(self._simple)
        s_layout.setContentsMargins(0, 0, 0, 0)
        s_layout.setSpacing(pad)

        self.lbl_plain = QLabel(
            tr("plain_status_idle", default="Watching the market — no action needed."), self._simple
        )
        self.lbl_plain.setObjectName("StatusPlainLine")
        self.lbl_plain.setStyleSheet("font-weight: 500;")
        s_layout.addWidget(self.lbl_plain, 1)

        self.btn_stop_simple = QPushButton(tr("status.stop_trading_now", default="Stop trading now"), self._simple)
        self.btn_stop_simple.setObjectName("StopTradingButton")
        self.btn_stop_simple.setStyleSheet("color: #c0392b; border: 1px solid #c0392b; padding: 2px 8px;")
        self.btn_stop_simple.clicked.connect(self.kill_requested.emit)
        s_layout.addWidget(self.btn_stop_simple)

        self._stack_layout.addWidget(self._detailed)
        self._stack_layout.addWidget(self._simple)
        self._simple.setVisible(False)

    def set_simple_mode(self, simple: bool) -> None:
        """Collapse to plain-language line when simple is True."""
        self._simple_mode = simple
        self._detailed.setVisible(not simple)
        self._simple.setVisible(simple)

    @Slot(bool)
    def set_connected(self, connected: bool) -> None:
        """Set connection dot color."""
        self._connected = connected
        if connected:
            self.dot.setStyleSheet("color: #27ae60; font-size: 10px;")
            self.dot.setToolTip(tr("status.connected", default="Connected"))
        else:
            self.dot.setStyleSheet("color: #888; font-size: 10px;")
            self.dot.setToolTip(tr("status.disconnected", default="Disconnected"))

    def set_account_type(self, account_type: str) -> None:
        """Set DEMO/REAL/CONTEST badge."""
        text = account_type.upper()
        # Badge API may be setText or set_text
        try:
            self.badge_account.setText(text)  # type: ignore[attr-defined]
        except Exception:
            try:
                self.badge_account.set_text(text)  # type: ignore[attr-defined]
            except Exception:
                pass

    def set_mode(self, mode: str) -> None:
        """Set mode badge (Analysis/Paper/Semi/Auto)."""
        try:
            self.badge_mode.setText(mode)  # type: ignore[attr-defined]
        except Exception:
            try:
                self.badge_mode.set_text(mode)  # type: ignore[attr-defined]
            except Exception:
                pass

    def set_balance(self, value: float) -> None:
        """Set balance label with tabular numbers."""
        self.lbl_balance.setText(
            tr("status.balance_value", default="Balance: {value:.2f}").format(value=value)
            if "{value" in tr("status.balance_value", default="Balance: {value:.2f}")
            else f"Balance: {value:.2f}"
        )

    def set_equity(self, value: float) -> None:
        """Set equity label."""
        self.lbl_equity.setText(f"Equity: {value:.2f}")

    def set_today_pnl(self, value: float, pct: float) -> None:
        """Set today P/L with +/- text and icon — never color alone."""
        sign = "+" if value >= 0 else ""
        # Include arrow icon + text so color is not sole indicator
        arrow = "▲" if value >= 0 else "▼"
        color = "#27ae60" if value >= 0 else "#c0392b"
        self.lbl_today.setText(f"{arrow} {sign}{value:.2f} ({sign}{pct:.2f}%)")
        self.lbl_today.setStyleSheet(f"font-variant-numeric: tabular-nums; color: {color};")

    def set_drawdown_pct(self, pct: float) -> None:
        """Set drawdown bar and label."""
        clamped = max(0, min(100, int(round(pct))))
        self.dd_bar.setValue(clamped)
        self.lbl_dd.setText(f"DD {pct:.1f}%")

    def set_open_risk_pct(self, pct: float) -> None:
        """Set open risk label."""
        self.lbl_risk.setText(f"Risk: {pct:.1f}%")

    def set_bot_state(self, state: str) -> None:
        """Set bot state label (Running/Paused by limit/Stopped/Disconnected)."""
        self.lbl_bot.setText(state)

    def set_sync_state(self, state: str) -> None:
        """Set sync state indicator."""
        self.lbl_sync.setText(f"● {state}")

    def set_session_clock(self, text: str) -> None:
        """Set session clock label."""
        self.lbl_clock.setText(text)

    def set_next_news(self, title: str, dt: datetime | None) -> None:
        """Set next news label."""
        if dt is not None:
            self.lbl_news.setText(f"{title} @ {dt.strftime('%H:%M')}")
        else:
            self.lbl_news.setText(title if title else tr("status.no_news", default="No news"))

    def set_plain_status(self, key: str, *, default: str | None = None, **kwargs: object) -> None:
        """Set plain-language status line for simple mode."""
        self.lbl_plain.setText(tr(key, default=default, **kwargs))
