"""
Premium Settings Page — sectioned card layout, label + description + control rows,
updates card, logging card. Clean form spacing, 24px margins.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.ui.theme.tokens import FONT_SIZE, RADIUS, get_palette


def _card(theme: str) -> QFrame:
    f = QFrame()
    f.setObjectName("CardFrame")
    p = get_palette(theme)
    f.setStyleSheet(f"#CardFrame {{ background-color: {p.card}; border: 1px solid {p.border}; border-radius: {RADIUS.lg}px; }}")
    return f


def _setting_row(label: str, description: str, control: QWidget, theme: str) -> QWidget:
    p = get_palette(theme)
    row = QWidget()
    row.setStyleSheet("background: transparent; border: none;")
    lay = QHBoxLayout(row)
    lay.setContentsMargins(0, 12, 0, 12)
    lay.setSpacing(16)

    text_col = QVBoxLayout()
    text_col.setSpacing(2)
    lb = QLabel(label)
    lb.setStyleSheet(f"font-size: {FONT_SIZE.body}px; font-weight: 500; color: {p.text}; background: transparent; border: none;")
    desc = QLabel(description)
    desc.setWordWrap(True)
    desc.setStyleSheet(f"font-size: {FONT_SIZE.caption}px; color: {p.text_secondary}; background: transparent; border: none;")
    text_col.addWidget(lb)
    text_col.addWidget(desc)
    text_col.addStretch(1)

    lay.addLayout(text_col, 1)
    lay.addWidget(control, 0, Qt.AlignmentFlag.AlignTop)
    return row


def _divider(theme: str) -> QFrame:
    p = get_palette(theme)
    f = QFrame()
    f.setFixedHeight(1)
    f.setObjectName("Divider")
    f.setStyleSheet(f"#Divider {{ background-color: {p.border}; border: none; }}")
    return f


class SettingsPage(QWidget):
    themeChanged = Signal(str)
    checkUpdateRequested = Signal()
    debugModeToggled = Signal(bool)

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
        self._title = QLabel("Settings")
        self._title.setObjectName("PageTitle")
        self._subtitle = QLabel("Configure your workstation preferences")
        p = get_palette(self._theme)
        self._subtitle.setStyleSheet(f"font-size: {FONT_SIZE.body}px; color: {p.text_secondary}; background: transparent; border: none;")
        title_row.addWidget(self._title)
        title_row.addWidget(self._subtitle)
        title_row.addStretch(1)
        lay.addLayout(title_row)

        # — Appearance card —
        self._appearance_card = _card(self._theme)
        ac_lay = QVBoxLayout(self._appearance_card)
        ac_lay.setContentsMargins(20, 20, 20, 20)
        ac_lay.setSpacing(0)
        hdr = QLabel("APPEARANCE")
        hdr.setStyleSheet(
            f"font-size: {FONT_SIZE.caption}px; font-weight: 600; color: {p.text_tertiary}; letter-spacing: 0.08em; background: transparent; border: none; padding-bottom: 4px;"
        )
        ac_lay.addWidget(hdr)

        self._theme_combo = QComboBox()
        self._theme_combo.addItems(["Dark", "Light"])
        self._theme_combo.setFixedWidth(180)
        self._theme_combo.setCurrentText("Dark" if self._theme == "dark" else "Light")
        self._theme_combo.currentTextChanged.connect(lambda t: self.themeChanged.emit(t.lower()))
        ac_lay.addWidget(_setting_row("Theme", "Choose between premium dark and warm light appearance", self._theme_combo, self._theme))
        ac_lay.addWidget(_divider(self._theme))

        self._density_combo = QComboBox()
        self._density_combo.addItems(["Comfortable", "Compact"])
        self._density_combo.setFixedWidth(180)
        ac_lay.addWidget(_setting_row("Density", "Control spacing and padding throughout the app", self._density_combo, self._theme))
        ac_lay.addWidget(_divider(self._theme))

        self._lang_combo = QComboBox()
        self._lang_combo.addItems(["English", "فارسی"])
        self._lang_combo.setFixedWidth(180)
        ac_lay.addWidget(_setting_row("Language", "Interface language — affects dates and numbers", self._lang_combo, self._theme))
        lay.addWidget(self._appearance_card)

        # — Trading card —
        self._trading_card = _card(self._theme)
        tc_lay = QVBoxLayout(self._trading_card)
        tc_lay.setContentsMargins(20, 20, 20, 20)
        tc_lay.setSpacing(0)
        hdr2 = QLabel("TRADING")
        hdr2.setStyleSheet(
            f"font-size: {FONT_SIZE.caption}px; font-weight: 600; color: {p.text_tertiary}; letter-spacing: 0.08em; background: transparent; border: none; padding-bottom: 4px;"
        )
        tc_lay.addWidget(hdr2)

        self._confirm_check = QCheckBox("Confirm before placing orders")
        self._confirm_check.setChecked(True)
        tc_lay.addWidget(
            _setting_row(
                "Order confirmation",
                "Show a confirmation dialog before sending orders to MT5",
                self._confirm_check,
                self._theme,
            )
        )
        tc_lay.addWidget(_divider(self._theme))

        self._sound_check = QCheckBox("Play sound on fill")
        tc_lay.addWidget(_setting_row("Sound alerts", "Audible notification when an order is filled", self._sound_check, self._theme))
        lay.addWidget(self._trading_card)

        # — Updates card —
        self._updates_card = _card(self._theme)
        uc_lay = QVBoxLayout(self._updates_card)
        uc_lay.setContentsMargins(20, 20, 20, 20)
        uc_lay.setSpacing(12)
        hdr3 = QLabel("UPDATES")
        hdr3.setStyleSheet(f"font-size: {FONT_SIZE.caption}px; font-weight: 600; color: {p.text_tertiary}; letter-spacing: 0.08em; background: transparent; border: none;")
        uc_lay.addWidget(hdr3)

        ver_row = QHBoxLayout()
        ver_row.setSpacing(12)
        # version info — import the STRING, not the module
        try:
            from app.__version__ import __version__ as _ver
        except Exception:
            _ver = "0.0.0"
        self._version_label = QLabel(f"Version  {_ver}")
        self._version_label.setStyleSheet(
            f"font-family: 'JetBrains Mono', monospace; font-size: {FONT_SIZE.body}px; font-weight: 600; color: {p.text}; background: transparent; border: none; font-feature-settings: 'tnum';"  # noqa: E501
        )
        self._update_status = QLabel("You are up to date")
        self._update_status.setStyleSheet(f"font-size: {FONT_SIZE.caption}px; color: {p.profit}; background: transparent; border: none;")
        ver_row.addWidget(self._version_label)
        ver_row.addWidget(self._update_status)
        ver_row.addStretch(1)
        self._check_btn = QPushButton("Check for updates")
        self._check_btn.setObjectName("SecondaryButton")
        self._check_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._check_btn.clicked.connect(self.checkUpdateRequested.emit)
        ver_row.addWidget(self._check_btn)
        uc_lay.addLayout(ver_row)

        # banner
        self._update_banner = QFrame()
        self._update_banner.setStyleSheet(f"background-color: {p.accent_soft}; border: 1px solid {p.accent}30; border-radius: {RADIUS.md}px;")
        bl = QHBoxLayout(self._update_banner)
        bl.setContentsMargins(12, 10, 12, 10)
        bl.addWidget(QLabel("✦  Tip: Enable auto-updates to always stay on the latest version."))
        uc_lay.addWidget(self._update_banner)
        lay.addWidget(self._updates_card)

        # — Logging card —
        self._logging_card = _card(self._theme)
        lc_lay = QVBoxLayout(self._logging_card)
        lc_lay.setContentsMargins(20, 20, 20, 20)
        lc_lay.setSpacing(0)
        hdr4 = QLabel("LOGGING & DIAGNOSTICS")
        hdr4.setStyleSheet(
            f"font-size: {FONT_SIZE.caption}px; font-weight: 600; color: {p.text_tertiary}; letter-spacing: 0.08em; background: transparent; border: none; padding-bottom: 4px;"
        )
        lc_lay.addWidget(hdr4)

        # log dir row
        log_dir_wrap = QWidget()
        log_dir_wrap.setStyleSheet("background: transparent; border: none;")
        ld_lay = QHBoxLayout(log_dir_wrap)
        ld_lay.setContentsMargins(0, 0, 0, 0)
        ld_lay.setSpacing(8)
        self._log_dir_input = QLineEdit()
        self._log_dir_input.setPlaceholderText("/path/to/logs")
        self._log_dir_input.setFixedWidth(320)
        browse_btn = QPushButton("Browse…")
        browse_btn.setObjectName("SecondaryButton")
        browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_btn.clicked.connect(self._browse_log_dir)
        ld_lay.addWidget(self._log_dir_input, 1)
        ld_lay.addWidget(browse_btn)
        lc_lay.addWidget(_setting_row("Log directory", "Where log files are written on disk", log_dir_wrap, self._theme))
        lc_lay.addWidget(_divider(self._theme))

        self._log_level_combo = QComboBox()
        self._log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self._log_level_combo.setCurrentText("INFO")
        self._log_level_combo.setFixedWidth(180)
        lc_lay.addWidget(_setting_row("Log level", "Verbosity of file and console output", self._log_level_combo, self._theme))
        lc_lay.addWidget(_divider(self._theme))

        self._debug_check = QCheckBox("Enable debug mode")
        self._debug_check.toggled.connect(self.debugModeToggled.emit)
        lc_lay.addWidget(_setting_row("Debug mode", "Extra diagnostics — may impact performance", self._debug_check, self._theme))

        lay.addWidget(self._logging_card)
        lay.addStretch(1)

        scroll.setWidget(container)
        outer.addWidget(scroll)

    def _browse_log_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Select log directory")
        if d:
            self._log_dir_input.setText(d)

    def _apply_theme(self, theme: str):
        self._theme = theme
        p = get_palette(theme)
        self.setStyleSheet(f"#PageRoot {{ background-color: {p.bg}; }}")
        self._container.setStyleSheet(f"background-color: {p.bg};")
        self._title.setStyleSheet(f"font-size: {FONT_SIZE.hero}px; font-weight: 700; color: {p.text}; letter-spacing: -0.03em; background: transparent; border: none;")
        self._subtitle.setStyleSheet(f"font-size: {FONT_SIZE.body}px; color: {p.text_secondary}; background: transparent; border: none;")
        for card in (self._appearance_card, self._trading_card, self._updates_card, self._logging_card):
            card.setStyleSheet(f"#CardFrame {{ background-color: {p.card}; border: 1px solid {p.border}; border-radius: {RADIUS.lg}px; }}")
        self._update_banner.setStyleSheet(f"background-color: {p.accent_soft}; border: 1px solid {p.accent}30; border-radius: {RADIUS.md}px;")

    def set_theme(self, theme: str):
        self._apply_theme(theme)
        # re-apply row dividers etc. by rebuilding is heavy; just update palette for next paint
