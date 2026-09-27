"""Main window — composition root for Phase 1."""

from __future__ import annotations

from loguru import logger
from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.ui.command_palette import CommandPalette
from app.ui.i18n import tr
from app.ui.pages.ai_lab import AiLabPage
from app.ui.pages.analytics import AnalyticsPage
from app.ui.pages.backtest import BacktestPage
from app.ui.pages.dashboard import DashboardPage
from app.ui.pages.health import HealthPage
from app.ui.pages.journal import JournalPage
from app.ui.pages.logs import LogsPage
from app.ui.pages.market import MarketPage
from app.ui.pages.model import ModelPage
from app.ui.pages.positions_trades import PositionsTradesPage
from app.ui.pages.risk import RiskPage
from app.ui.pages.settings import SettingsPage
from app.ui.pages.signals import SignalsPage
from app.ui.pages.strategies import StrategiesPage
from app.ui.sidebar import Sidebar
from app.ui.status_bar import StatusBar
from app.ui.theme.qss import generate_qss
from app.ui.theme.tokens import get_tokens
from app.ui.widgets import ConfirmDialog, EmptyState, Toggle


class MainWindow(QMainWindow):
    """Main window holding sidebar, stacked pages, top bar, and status bar."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("MainWindow")
        self.setWindowTitle(tr("app.title", default="MT5 Trading Workstation"))
        # Ensure the title is exactly app_name + " " + version (single source of truth).
        from app.__version__ import __app_name__, __version__

        self.setWindowTitle(f"{__app_name__} {__version__}")
        self.resize(1280, 800)

        self._theme: str = "dark"
        self._simple_mode = True
        self._has_open_positions = False  # Phase 1: always False

        # Apply initial theme QSS
        self.reapply_theme(self._theme)

        # Top bar
        self.top_bar = QFrame(self)
        self.top_bar.setObjectName("TopBar")
        top_layout = QHBoxLayout(self.top_bar)
        top_layout.setContentsMargins(12, 6, 12, 6)
        top_layout.setSpacing(12)

        self.lbl_app = QLabel(tr("app.name", default="MT5 Trading Workstation"), self.top_bar)
        self.lbl_app.setObjectName("AppNameLabel")
        self.lbl_app.setStyleSheet("font-size: 14px; font-weight: 700;")
        top_layout.addWidget(self.lbl_app)

        self.lbl_version = QLabel("v0.1.0", self.top_bar)
        self.lbl_version.setObjectName("AppVersionLabel")
        self.lbl_version.setStyleSheet("opacity: 0.6; font-size: 11px;")
        top_layout.addWidget(self.lbl_version)

        top_layout.addStretch(1)

        self.lbl_simple = QLabel(tr("topbar.simple", default="Simple"), self.top_bar)
        top_layout.addWidget(self.lbl_simple)

        self.toggle_simple = Toggle(parent=self.top_bar)  # type: ignore[call-arg]
        self.toggle_simple.setObjectName("SimpleAdvancedToggle")
        try:
            self.toggle_simple.setChecked(False)  # type: ignore[attr-defined]
        except Exception:
            try:
                self.toggle_simple.set_checked(False)  # type: ignore[attr-defined]
            except Exception:
                pass
        # Toggle may emit toggled / checkedChanged
        try:
            self.toggle_simple.toggled.connect(self.set_simple_mode)  # type: ignore[attr-defined]
        except Exception:
            try:
                self.toggle_simple.checkedChanged.connect(self.set_simple_mode)  # type: ignore[attr-defined]
            except Exception:
                pass
        top_layout.addWidget(self.toggle_simple)

        self.lbl_advanced = QLabel(tr("topbar.advanced", default="Advanced"), self.top_bar)
        top_layout.addWidget(self.lbl_advanced)

        # Theme toggle button (dark/light)
        self.btn_theme = QLabel("◐", self.top_bar)
        self.btn_theme.setObjectName("ThemeToggle")
        self.btn_theme.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_theme.setToolTip(tr("topbar.toggle_theme", default="Toggle Dark/Light Theme"))
        top_layout.addWidget(self.btn_theme)

        # Central area: splitter with sidebar + stacked pages
        central = QWidget(self)
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        central_layout.addWidget(self.top_bar)

        self.splitter = QSplitter(Qt.Orientation.Horizontal, central)
        self.splitter.setObjectName("MainSplitter")

        self.sidebar = Sidebar(self.splitter)
        self.splitter.addWidget(self.sidebar)

        # Stacked pages container
        self.stack = QStackedWidget(self.splitter)
        self.stack.setObjectName("PageStack")

        # Instantiate all 14 pages
        self.page_dashboard = DashboardPage(self.stack)
        self.page_market = MarketPage(self.stack)
        self.page_signals = SignalsPage(self.stack)
        self.page_positions_trades = PositionsTradesPage(self.stack)
        self.page_analytics = AnalyticsPage(self.stack)
        self.page_journal = JournalPage(self.stack)
        self.page_backtest = BacktestPage(self.stack)
        self.page_model = ModelPage(self.stack)
        self.page_ai_lab = AiLabPage(self.stack)
        self.page_strategies = StrategiesPage(self.stack)
        self.page_risk = RiskPage(self.stack)
        self.page_logs = LogsPage(self.stack)
        self.page_health = HealthPage(self.stack)
        self.page_settings = SettingsPage(self.stack)

        self._page_order: list[tuple[str, QWidget]] = [
            ("dashboard", self.page_dashboard),
            ("market", self.page_market),
            ("signals", self.page_signals),
            ("positions_trades", self.page_positions_trades),
            ("analytics", self.page_analytics),
            ("journal", self.page_journal),
            ("backtest", self.page_backtest),
            ("model", self.page_model),
            ("ai_lab", self.page_ai_lab),
            ("strategies", self.page_strategies),
            ("risk", self.page_risk),
            ("logs", self.page_logs),
            ("health", self.page_health),
            ("settings", self.page_settings),
        ]
        self._page_index: dict[str, int] = {}
        for idx, (pid, widget) in enumerate(self._page_order):
            self.stack.addWidget(widget)
            self._page_index[pid] = idx

        # SimpleHome placeholder (shown only in simple mode)
        self.simple_home = QFrame(self.stack)
        self.simple_home.setObjectName("SimpleHome")
        sh_layout = QVBoxLayout(self.simple_home)
        sh_layout.setContentsMargins(24, 24, 24, 24)
        sh_title = QLabel(tr("simple_home.title", default="Trading Assistant"), self.simple_home)
        sh_title.setStyleSheet("font-size: 18px; font-weight: 700;")
        sh_layout.addWidget(sh_title)
        self.simple_empty = EmptyState(  # type: ignore[call-arg]
            headline=tr("simple_home.empty_title", default="No trade suggestion"),
            sub_headline=tr(
                "simple_home.empty_state",
                default="No trade suggestion right now. The app is watching the market.",
            ),
            parent=self.simple_home,
        )
        sh_layout.addWidget(self.simple_empty, 1)
        self.stack.addWidget(self.simple_home)
        self._simple_home_index = self.stack.count() - 1

        self.splitter.addWidget(self.stack)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([220, 1060])

        central_layout.addWidget(self.splitter, 1)

        # Status bar (custom, richer than QStatusBar)
        self.status_bar = StatusBar(central)
        central_layout.addWidget(self.status_bar)

        self.setCentralWidget(central)

        # Wire sidebar -> stack
        self.sidebar.page_requested.connect(self._on_page_requested)

        # Wire settings page signals
        self.page_settings.theme_changed.connect(self.reapply_theme)
        self.page_settings.simple_mode_changed.connect(self.set_simple_mode)

        # Command palette
        self.command_palette = CommandPalette(self)
        self.command_palette.command_executed.connect(self._on_command_executed)

        # Ctrl+K shortcut
        self.shortcut_palette = QShortcut(QKeySequence("Ctrl+K"), self)
        self.shortcut_palette.activated.connect(self._show_command_palette)

        # Also add QAction for menu discoverability
        self.action_palette = QAction(tr("command_palette.title", default="Command Palette"), self)
        self.action_palette.setShortcut(QKeySequence("Ctrl+K"))
        self.action_palette.triggered.connect(self._show_command_palette)
        self.addAction(self.action_palette)

        # Theme click handler
        # Use mousePressEvent on label via event filter
        self.btn_theme.mousePressEvent = lambda _e: self._toggle_theme()  # type: ignore[method-assign,assignment]

        # Default page
        self.stack.setCurrentIndex(self._page_index["dashboard"])

        # In-app auto-updater (Part J).
        # Wrapped in try/except so a missing optional dep (e.g., httpx not installed
        # in a stripped dev env) doesn't break the window construction.
        self.update_checker = None
        try:
            from app.updater.updater import UpdateChecker

            self.update_checker = UpdateChecker(parent=self)
            self.update_checker.update_available.connect(self._on_update_available)
            self.update_checker.no_update.connect(self._on_no_update)
            self.update_checker.error.connect(self._on_update_error)
            # Auto-check 5s after startup if the setting is on.
            try:
                from app.core.config import load_settings

                settings = load_settings()
                if settings.check_updates_on_startup and self.update_checker is not None:
                    QTimer.singleShot(5000, self.update_checker.start_check)
            except Exception:
                logger.exception("Failed to read update settings; skipping auto-check")
        except Exception:
            logger.exception("Failed to initialize UpdateChecker; updates disabled")

    @Slot(object)
    def _on_update_available(self, update_info: object) -> None:
        """Show a toast when an update is available."""
        try:
            version = getattr(update_info, "version", "new")
        except Exception:
            version = "new"
        logger.info(f"Update available: v{version}")
        # Show a small toast pointing to Settings.
        from app.ui.widgets.toast import Toast

        toast = Toast(self)
        toast.show_toast(
            tr("update.available_toast", default=f"v{version} available — see Settings"),
            kind="info",
            duration_ms=5000,
        )

    @Slot()
    def _on_no_update(self) -> None:
        logger.debug("Update check: already on latest version")

    @Slot(str)
    def _on_update_error(self, message: str) -> None:
        logger.warning(f"Update check error: {message}")

    def check_for_updates(self) -> None:
        """Public entry point for the Settings page and command palette."""
        if self.update_checker is not None:
            self.update_checker.start_check()

    @Slot(str)
    def _on_page_requested(self, page_id: str) -> None:
        idx = self._page_index.get(page_id)
        if idx is not None:
            # If in simple mode, exit simple mode when navigating via sidebar (sidebar hidden anyway)
            self.stack.setCurrentIndex(idx)
            self.sidebar.set_active_page(page_id)

    @Slot()
    def _show_command_palette(self) -> None:
        self.command_palette.open_palette()

    @Slot(str)
    def _on_command_executed(self, command_id: str) -> None:
        if command_id.startswith("go_"):
            page_map: dict[str, str] = {
                "go_dashboard": "dashboard",
                "go_market": "market",
                "go_signals": "signals",
                "go_positions_trades": "positions_trades",
                "go_analytics": "analytics",
                "go_journal": "journal",
                "go_backtest": "backtest",
                "go_model": "model",
                "go_ai_lab": "ai_lab",
                "go_strategies": "strategies",
                "go_risk": "risk",
                "go_logs": "logs",
                "go_health": "health",
                "go_settings": "settings",
            }
            page_id = page_map.get(command_id)
            if page_id is not None:
                idx = self._page_index.get(page_id)
                if idx is not None:
                    self.stack.setCurrentIndex(idx)
                    self.sidebar.set_active_page(page_id)
                    if self._simple_mode:
                        # Navigating via palette in simple mode should show the page
                        # but keep simple status bar; we temporarily show advanced stack
                        pass
        elif command_id == "toggle_simple":
            self.set_simple_mode(not self._simple_mode)
        elif command_id == "toggle_theme":
            self._toggle_theme()
        elif command_id == "toggle_language":
            # Toggle EN <-> FA by reading the AppSettings.language attribute.
            current = getattr(self.page_settings._settings, "language", "en")
            new_lang = "en" if current == "fa" else "fa"
            self.page_settings.set_language(new_lang)
        elif command_id == "kill_switch":
            self._confirm_kill()

    def _toggle_theme(self) -> None:
        new_theme = "light" if self._theme == "dark" else "dark"
        self.reapply_theme(new_theme)
        self.page_settings.set_theme(new_theme)

    def reapply_theme(self, theme: str) -> None:
        """Re-render tokens, regenerate QSS, and apply to QApplication and self."""
        self._theme = theme
        tokens = get_tokens(theme)
        qss = generate_qss(tokens)
        app = QApplication.instance()
        if app is not None and isinstance(app, QApplication):
            app.setStyleSheet(qss)
        self.setStyleSheet(qss)
        # Ensure children also get updated (guard for early-call during __init__).
        page_order = getattr(self, "_page_order", None)
        if page_order:
            for _, widget in page_order:
                widget.setStyleSheet(qss)
        simple_home = getattr(self, "simple_home", None)
        if simple_home is not None:
            simple_home.setStyleSheet(qss)

    @Slot(bool)
    def set_simple_mode(self, simple: bool) -> None:
        """Toggle simple/advanced mode."""
        self._simple_mode = simple
        # Sync toggle widget without recursion
        try:
            self.toggle_simple.blockSignals(True)
            try:
                self.toggle_simple.setChecked(simple)  # type: ignore[attr-defined]
            except Exception:
                try:
                    self.toggle_simple.set_checked(simple)  # type: ignore[attr-defined]
                except Exception:
                    pass
            self.toggle_simple.blockSignals(False)
        except Exception:
            pass

        self.status_bar.set_simple_mode(simple)
        if simple:
            self.sidebar.setVisible(False)
            self.stack.setCurrentIndex(self._simple_home_index)
        else:
            self.sidebar.setVisible(True)
            # Restore last active page or dashboard
            self.stack.setCurrentIndex(self._page_index["dashboard"])
            self.sidebar.set_active_page("dashboard")

    def _confirm_kill(self) -> None:
        dlg = ConfirmDialog(  # type: ignore[call-arg]
            title=tr("kill.confirm_title", default="Confirm Kill Switch"),
            message=tr("kill.confirm_message", default="Are you sure you want to stop all trading?"),
            parent=self,
        )
        # ConfirmDialog may have exec / exec_ / open
        try:
            dlg.exec()  # type: ignore[attr-defined]
        except Exception:
            try:
                dlg.exec_()  # type: ignore[attr-defined]
            except Exception:
                dlg.show()

    def closeEvent(self, event: QCloseEvent) -> None:  # type: ignore[override]
        """On close, show informational dialog if positions remain (Phase 1: always False)."""
        if self._has_open_positions:
            dlg = ConfirmDialog(  # type: ignore[call-arg]
                title=tr("close.positions_title", default="Positions Open"),
                message=tr(
                    "close.positions_message",
                    default="Positions remain protected by server-side SL.",
                ),
                parent=self,
            )
            try:
                dlg.exec()  # type: ignore[attr-defined]
            except Exception:
                try:
                    dlg.exec_()  # type: ignore[attr-defined]
                except Exception:
                    dlg.show()
        event.accept()
