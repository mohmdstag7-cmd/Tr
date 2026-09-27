"""
Premium Main Window — 48px top bar, 220/56 sidebar, 32px status bar,
QStackedWidget with 24px margins, smooth page transitions, __version__ label.
"""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, Signal, Slot
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.ui.sidebar import Sidebar
from app.ui.status_bar import StatusBar
from app.ui.theme.qss import build_qss
from app.ui.theme.tokens import FONT_SIZE, RADIUS, get_palette

# Try to import version — must not be hardcoded
try:
    from app.__version__ import __version__
except Exception:
    __version__ = "0.0.0"


class TopBar(QFrame):
    themeToggled = Signal  # type: ignore[assignment]

    def __init__(self, theme: str = "dark", parent=None):
        # Use dynamic Signal creation to avoid circular import issues
        super().__init__(parent)
        self._theme = theme
        self.setObjectName("TopBarFrame")
        self.setFixedHeight(48)
        self._build_ui()
        self._apply_theme(theme)

    def _build_ui(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(12)

        # Left: app name + version
        self._app_name = QLabel("MT5 Trading Workstation")
        self._app_name.setStyleSheet("background: transparent; border: none;")
        self._version_label = QLabel(f"v{__version__}")
        self._version_label.setObjectName("VersionLabel")
        lay.addWidget(self._app_name)
        lay.addWidget(self._version_label)
        lay.addStretch(1)

        # Right: theme toggle + simple/advanced toggle
        self._mode_btn = QPushButton("Simple")
        self._mode_btn.setObjectName("SecondaryButton")
        self._mode_btn.setFixedHeight(32)
        self._mode_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._mode_btn.setCheckable(True)
        self._mode_btn.toggled.connect(self._on_mode_toggled)
        lay.addWidget(self._mode_btn)

        self._theme_btn = QPushButton("◐" if self._theme == "dark" else "◑")
        self._theme_btn.setObjectName("GhostButton")
        self._theme_btn.setFixedSize(36, 32)
        self._theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._theme_btn.setToolTip("Toggle theme")
        lay.addWidget(self._theme_btn)

    def _apply_theme(self, theme: str):
        self._theme = theme
        p = get_palette(theme)
        self.setStyleSheet(f"#TopBarFrame {{ background-color: {p.surface}; border-bottom: 1px solid {p.border}; border-left: none; border-right: none; border-top: none; }}")
        self._app_name.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {p.text}; letter-spacing: -0.02em; background: transparent; border: none;")
        self._version_label.setStyleSheet(
            f"font-size: {FONT_SIZE.caption}px; font-weight: 500; color: {p.text_tertiary}; "
            f"background-color: {p.bg}; border: 1px solid {p.border}; border-radius: {RADIUS.pill}px; padding: 2px 8px;"
        )
        self._theme_btn.setText("◐" if theme == "dark" else "◑")

    def set_theme(self, theme: str):
        self._apply_theme(theme)

    def _on_mode_toggled(self, checked: bool):
        self._mode_btn.setText("Advanced" if checked else "Simple")

    def set_version(self, version: str):
        self._version_label.setText(f"v{version}")


# Re-import Signal properly for TopBar
from PySide6.QtCore import Signal as _Signal  # noqa: E402

# Monkey-patch signals if not already defined (PySide needs class-level Signal)
if not hasattr(TopBar, "themeToggleRequested"):
    TopBar.themeToggleRequested = _Signal(str)  # type: ignore
    TopBar.modeToggleRequested = _Signal(bool)  # type: ignore
    # wire theme button after signal exists
    _orig_init = TopBar.__init__

    def _patched_init(self, theme="dark", parent=None):
        QFrame.__init__(self, parent)
        self._theme = theme
        self.setObjectName("TopBarFrame")
        self.setFixedHeight(48)
        # build manually to wire correctly
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(12)
        self._app_name = QLabel("MT5 Trading Workstation")
        self._version_label = QLabel(f"v{__version__}")
        self._version_label.setObjectName("VersionLabel")
        lay.addWidget(self._app_name)
        lay.addWidget(self._version_label)
        lay.addStretch(1)
        self._mode_btn = QPushButton("Simple")
        self._mode_btn.setObjectName("SecondaryButton")
        self._mode_btn.setFixedHeight(32)
        self._mode_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._mode_btn.setCheckable(True)
        self._mode_btn.toggled.connect(lambda c: self.modeToggleRequested.emit(c))
        self._mode_btn.toggled.connect(lambda c: self._mode_btn.setText("Advanced" if c else "Simple"))
        lay.addWidget(self._mode_btn)
        self._theme_btn = QPushButton("◐" if self._theme == "dark" else "◑")
        self._theme_btn.setObjectName("GhostButton")
        self._theme_btn.setFixedSize(36, 32)
        self._theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._theme_btn.setToolTip("Toggle theme")
        self._theme_btn.clicked.connect(lambda: self.themeToggleRequested.emit("light" if self._theme == "dark" else "dark"))
        lay.addWidget(self._theme_btn)
        self._apply_theme(theme)

    TopBar.__init__ = _patched_init  # type: ignore


class MainWindow(QMainWindow):
    def __init__(self, theme: str = "dark"):
        super().__init__()
        self._theme = theme
        self.setWindowTitle(f"MT5 Trading Workstation — v{__version__}")
        self.resize(1280, 800)
        self.setMinimumSize(1024, 640)

        # Apply global QSS
        self.setStyleSheet(build_qss(theme))

        # Central layout
        central = QWidget()
        central.setObjectName("PageRoot")
        self.setCentralWidget(central)
        root_lay = QVBoxLayout(central)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)

        # Top bar
        self.top_bar = TopBar(theme=theme)
        self.top_bar.themeToggleRequested.connect(self.toggle_theme)  # type: ignore
        root_lay.addWidget(self.top_bar)

        # Middle: sidebar + stacked pages
        mid = QWidget()
        mid.setStyleSheet("background: transparent; border: none;")
        mid_lay = QHBoxLayout(mid)
        mid_lay.setContentsMargins(0, 0, 0, 0)
        mid_lay.setSpacing(0)

        self.sidebar = Sidebar(collapsed=False)
        self.sidebar.navigationRequested.connect(self.navigate_to)
        self.sidebar.collapseToggled.connect(self._on_sidebar_collapsed)
        mid_lay.addWidget(self.sidebar)

        # Stacked pages
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background: transparent; border: none;")
        self._pages: dict[str, QWidget] = {}
        self._load_pages()
        mid_lay.addWidget(self.stack, 1)

        root_lay.addWidget(mid, 1)

        # Status bar (custom)
        self.status_bar = StatusBar(theme=theme)
        root_lay.addWidget(self.status_bar)

        # Opacity effect for page transitions
        self._opacity_effect = QGraphicsOpacityEffect(self.stack)
        self.stack.setGraphicsEffect(self._opacity_effect)
        self._fade_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_anim.setDuration(200)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def _load_pages(self):
        """Load all 14 pages — real ones if available, else placeholder."""
        import importlib

        page_modules = [
            "dashboard",
            "market",
            "signals",
            "positions",
            "analytics",
            "journal",
            "backtest",
            "model",
            "ai_lab",
            "strategies",
            "risk",
            "logs",
            "health",
            "settings",
        ]
        for name in page_modules:
            w = None
            try:
                mod = importlib.import_module(f"app.ui.pages.{name}")
                # try common class names
                for cls_name in [f"{name.capitalize()}Page", f"{name.title().replace('_','')}Page", "Page", "View"]:
                    if hasattr(mod, cls_name):
                        try:
                            w = getattr(mod, cls_name)(theme=self._theme)  # type: ignore
                            break
                        except TypeError:
                            try:
                                w = getattr(mod, cls_name)()  # type: ignore
                                break
                            except Exception:
                                continue
                if w is None:
                    # fallback: look for any QWidget subclass
                    for attr in dir(mod):
                        obj = getattr(mod, attr)
                        try:
                            if isinstance(obj, type) and issubclass(obj, QWidget) and obj is not QWidget:
                                try:
                                    w = obj(theme=self._theme)  # type: ignore
                                    break
                                except TypeError:
                                    w = obj()  # type: ignore
                                    break
                        except Exception:
                            continue
            except Exception:
                w = None

            if w is None:
                # placeholder card
                w = self._placeholder_page(name)

            self._pages[name] = w
            self.stack.addWidget(w)

        # default page
        if "dashboard" in self._pages:
            self.stack.setCurrentWidget(self._pages["dashboard"])

    def _placeholder_page(self, name: str) -> QWidget:
        p = get_palette(self._theme)
        w = QWidget()
        w.setObjectName("PageRoot")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(16)
        title = QLabel(name.replace("_", " ").title())
        title.setStyleSheet(f"font-size: {FONT_SIZE.hero}px; font-weight: 700; color: {p.text}; letter-spacing: -0.03em; background: transparent; border: none;")
        lay.addWidget(title)
        card = QFrame()
        card.setObjectName("CardFrame")
        card.setStyleSheet(f"#CardFrame {{ background-color: {p.card}; border: 1px solid {p.border}; border-radius: {RADIUS.lg}px; }}")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(32, 32, 32, 32)
        cl.setSpacing(12)
        icon = QLabel("◫")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(f"font-size: 32px; color: {p.text_tertiary}; background: transparent; border: none;")
        cl.addWidget(icon)
        msg = QLabel(f"{name.replace('_',' ').title()} — content coming soon")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setStyleSheet(f"font-size: {FONT_SIZE.body}px; color: {p.text_secondary}; background: transparent; border: none;")
        cl.addWidget(msg)
        lay.addWidget(card)
        lay.addStretch(1)
        return w

    # ── Navigation with fade ──
    @Slot(str)
    def navigate_to(self, route: str):
        if route not in self._pages:
            return
        target = self._pages[route]
        if self.stack.currentWidget() is target:
            return
        self.sidebar.set_active(route)

        # fade out → switch → fade in
        self._fade_anim.stop()
        self._fade_anim.setStartValue(1.0)
        self._fade_anim.setEndValue(0.0)

        def _on_fade_out():
            try:
                self._fade_anim.finished.disconnect(_on_fade_out)
            except Exception:
                pass
            self.stack.setCurrentWidget(target)
            self._fade_anim.setStartValue(0.0)
            self._fade_anim.setEndValue(1.0)
            self._fade_anim.start()

        self._fade_anim.finished.connect(_on_fade_out)
        self._fade_anim.start()

    def _on_sidebar_collapsed(self, collapsed: bool):
        # sidebar handles its own width animation
        pass

    @Slot(str)
    def toggle_theme(self, theme: str | None = None):
        if theme is None:
            theme = "light" if self._theme == "dark" else "dark"
        self._theme = theme
        self.setStyleSheet(build_qss(theme))
        self.top_bar.set_theme(theme)
        self.sidebar.set_theme(theme)
        self.status_bar.set_theme(theme)
        for w in self._pages.values():
            if hasattr(w, "set_theme"):
                try:
                    w.set_theme(theme)  # type: ignore
                except Exception:
                    pass

    def set_theme(self, theme: str):
        self.toggle_theme(theme)
