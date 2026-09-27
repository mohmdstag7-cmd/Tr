"""
Premium QSS Generator — covers every widget with Linear/Notion polish.
Generous spacing, subtle borders, elevation, tabular numbers, focus rings.
"""

from __future__ import annotations

from .tokens import FONT_MONO, FONT_SIZE, FONT_STACK, RADIUS, get_palette


def build_qss(theme: str = "dark") -> str:
    p = get_palette(theme)
    is_dark = theme.lower() == "dark"

    return f"""
/* ── Global ── */
QMainWindow, QWidget {{
    background-color: {p.bg};
    color: {p.text};
    font-family: {FONT_STACK};
    font-size: {FONT_SIZE.body}px;
    selection-background-color: {p.accent};
    selection-color: #FFFFFF;
}}
QWidget#PageRoot {{
    background-color: {p.bg};
}}

/* ── Typography helpers ── */
QLabel#PageTitle {{
    font-size: {FONT_SIZE.title}px;
    font-weight: 600;
    color: {p.text};
    letter-spacing: -0.02em;
    padding: 0;
}}
QLabel#SectionTitle {{
    font-size: {FONT_SIZE.subtitle}px;
    font-weight: 600;
    color: {p.text};
    letter-spacing: -0.01em;
}}
QLabel#Caption {{
    font-size: {FONT_SIZE.caption}px;
    font-weight: 500;
    color: {p.text_secondary};
    text-transform: uppercase;
    letter-spacing: 0.06em;
}}
QLabel#Mono {{
    font-family: {FONT_MONO};
    font-feature-settings: 'tnum';
}}

/* ── Card ── */
QFrame#CardFrame {{
    background-color: {p.card};
    border: 1px solid {p.border};
    border-radius: {RADIUS.lg}px;
}}
QFrame#CardFrame:hover {{
    border: 1px solid {p.border_hover};
}}
QFrame#SectionCard {{
    background-color: {p.card};
    border: 1px solid {p.border};
    border-radius: {RADIUS.lg}px;
}}

/* ── Buttons — Primary ── */
QPushButton {{
    font-family: {FONT_STACK};
    font-size: {FONT_SIZE.body}px;
    font-weight: 500;
    border-radius: {RADIUS.md}px;
    padding: 8px 16px;
    outline: none;
}}
QPushButton#PrimaryButton {{
    background-color: {p.accent};
    color: #FFFFFF;
    border: 1px solid {p.accent};
    font-weight: 600;
}}
QPushButton#PrimaryButton:hover {{
    background-color: {p.accent_hover};
    border: 1px solid {p.accent_hover};
}}
QPushButton#PrimaryButton:pressed {{
    background-color: {p.accent};
    padding-top: 9px;
    padding-bottom: 7px;
}}
QPushButton#PrimaryButton:disabled {{
    background-color: {p.border};
    color: {p.text_tertiary};
    border: 1px solid {p.border};
}}

/* Secondary */
QPushButton#SecondaryButton {{
    background-color: {p.surface};
    color: {p.text};
    border: 1px solid {p.border};
}}
QPushButton#SecondaryButton:hover {{
    background-color: {p.card_hover};
    border: 1px solid {p.border_hover};
    color: {p.text};
}}
QPushButton#SecondaryButton:pressed {{
    background-color: {p.border};
}}
QPushButton#SecondaryButton:disabled {{
    color: {p.text_tertiary};
    border: 1px solid {p.border};
}}

/* Ghost */
QPushButton#GhostButton {{
    background-color: transparent;
    color: {p.text_secondary};
    border: 1px solid transparent;
}}
QPushButton#GhostButton:hover {{
    background-color: {p.accent_soft};
    color: {p.text};
    border: 1px solid transparent;
}}
QPushButton#GhostButton:pressed {{
    background-color: {p.accent_muted};
}}

/* Danger / Kill switch */
QPushButton#DangerButton {{
    background-color: transparent;
    color: {p.loss};
    border: 1px solid {p.loss}60;
    border-radius: {RADIUS.md}px;
    font-weight: 600;
    padding: 6px 14px;
}}
QPushButton#DangerButton:hover {{
    background-color: {p.loss_soft};
    border: 1px solid {p.loss};
    color: {p.loss};
}}
QPushButton#DangerButton:pressed {{
    background-color: {p.loss};
    color: #FFFFFF;
}}

/* Nav button — handled inline for active state, base here */
QPushButton#NavButton {{
    text-align: left;
    padding: 0 12px;
    border-radius: {RADIUS.md}px;
    border: 1px solid transparent;
    border-left: 3px solid transparent;
    font-size: {FONT_SIZE.body}px;
    font-weight: 500;
    color: {p.text_secondary};
    background-color: transparent;
}}
QPushButton#NavButton:hover {{
    background-color: {p.surface};
    color: {p.text};
    border: 1px solid transparent;
}}
QPushButton#NavButton:checked {{
    background-color: {p.accent_soft};
    color: {p.accent if is_dark else p.accent};
    border-left: 3px solid {p.accent};
    font-weight: 600;
}}

/* ── Inputs ── */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {p.surface};
    border: 1px solid {p.border};
    border-radius: {RADIUS.md}px;
    padding: 8px 12px;
    color: {p.text};
    selection-background-color: {p.accent};
    font-size: {FONT_SIZE.body}px;
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 1px solid {p.accent};
    background-color: {p.card};
}}
QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {{
    background-color: {p.bg};
    color: {p.text_tertiary};
    border: 1px solid {p.border};
}}
QLineEdit#SearchInput {{
    border-radius: {RADIUS.pill}px;
    padding: 7px 14px 7px 32px;
    background-color: {p.surface};
}}

/* ── ComboBox ── */
QComboBox {{
    background-color: {p.surface};
    border: 1px solid {p.border};
    border-radius: {RADIUS.md}px;
    padding: 7px 12px;
    color: {p.text};
    min-height: 18px;
}}
QComboBox:hover {{
    border: 1px solid {p.border_hover};
    background-color: {p.card};
}}
QComboBox:focus {{
    border: 1px solid {p.accent};
}}
QComboBox::drop-down {{
    border: none;
    width: 28px;
}}
QComboBox::down-arrow {{
    width: 10px;
    height: 10px;
}}
QComboBox QAbstractItemView {{
    background-color: {p.card};
    border: 1px solid {p.border};
    border-radius: {RADIUS.md}px;
    selection-background-color: {p.accent_soft};
    selection-color: {p.text};
    padding: 4px;
    outline: none;
}}

/* ── Table ── */
QTableWidget {{
    background-color: {p.card};
    border: 1px solid {p.border};
    border-radius: {RADIUS.lg}px;
    gridline-color: {p.border};
    outline: none;
    alternate-background-color: {p.surface if is_dark else "#F9FAFB"};
}}
QTableWidget::item {{
    padding: 10px 12px;
    border-bottom: 1px solid {p.border};
    color: {p.text};
}}
QTableWidget::item:selected {{
    background-color: {p.accent_soft};
    color: {p.text};
}}
QHeaderView::section {{
    background-color: {p.surface};
    color: {p.text_secondary};
    font-size: {FONT_SIZE.caption}px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    padding: 10px 12px;
    border: none;
    border-bottom: 1px solid {p.border};
    border-right: 1px solid {p.border};
}}
QHeaderView::section:last {{
    border-right: none;
}}
QTableCornerButton::section {{
    background-color: {p.surface};
    border: none;
}}

/* ── ScrollBar — thin modern ── */
QScrollBar:vertical {{
    background-color: transparent;
    width: 8px;
    margin: 2px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background-color: {p.scrollbar_thumb};
    border-radius: 4px;
    min-height: 32px;
    margin: 2px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: {p.scrollbar_thumb_hover};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
    background: none;
    border: none;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}
QScrollBar:horizontal {{
    background-color: transparent;
    height: 8px;
    margin: 2px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal {{
    background-color: {p.scrollbar_thumb};
    border-radius: 4px;
    min-width: 32px;
}}
QScrollBar::handle:horizontal:hover {{
    background-color: {p.scrollbar_thumb_hover};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
    background: none;
}}

/* ── StatusBar ── */
QStatusBar {{
    background-color: {p.surface};
    border-top: 1px solid {p.border};
    color: {p.text_secondary};
    font-size: {FONT_SIZE.caption}px;
    padding: 0 4px;
}}
QStatusBar::item {{
    border: none;
}}

/* ── ProgressBar — slim modern ── */
QProgressBar {{
    background-color: {p.surface};
    border: 1px solid {p.border};
    border-radius: {RADIUS.pill}px;
    height: 6px;
    text-visible: false;
}}
QProgressBar::chunk {{
    background-color: {p.accent};
    border-radius: {RADIUS.pill}px;
}}
QProgressBar#ProfitBar::chunk {{
    background-color: {p.profit};
}}
QProgressBar#LossBar::chunk {{
    background-color: {p.loss};
}}
QProgressBar#WarningBar::chunk {{
    background-color: {p.warning};
}}

/* ── CheckBox ── */
QCheckBox {{
    spacing: 8px;
    color: {p.text};
    font-size: {FONT_SIZE.body}px;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 1.5px solid {p.border_hover};
    background-color: {p.surface};
}}
QCheckBox::indicator:hover {{
    border: 1.5px solid {p.accent};
    background-color: {p.card};
}}
QCheckBox::indicator:checked {{
    background-color: {p.accent};
    border: 1.5px solid {p.accent};
    image: none;
}}
QCheckBox::indicator:checked:hover {{
    background-color: {p.accent_hover};
}}
QCheckBox::indicator:disabled {{
    background-color: {p.bg};
    border: 1.5px solid {p.border};
}}

/* ── Tabs — pill style ── */
QTabWidget::pane {{
    border: 1px solid {p.border};
    border-radius: {RADIUS.lg}px;
    background-color: {p.card};
    margin-top: -1px;
    padding: 16px;
}}
QTabBar::tab {{
    background-color: transparent;
    color: {p.text_secondary};
    padding: 8px 16px;
    margin-right: 4px;
    border-radius: {RADIUS.pill}px;
    border: 1px solid transparent;
    font-weight: 500;
    font-size: {FONT_SIZE.body}px;
}}
QTabBar::tab:hover {{
    background-color: {p.surface};
    color: {p.text};
}}
QTabBar::tab:selected {{
    background-color: {p.accent};
    color: #FFFFFF;
    border: 1px solid {p.accent};
    font-weight: 600;
}}
QTabBar::tab:!selected:hover {{
    background-color: {p.accent_soft};
}}

/* ── Splitter ── */
QSplitter::handle {{
    background-color: {p.border};
}}
QSplitter::handle:horizontal {{
    width: 1px;
}}
QSplitter::handle:vertical {{
    height: 1px;
}}
QSplitter::handle:hover {{
    background-color: {p.accent}60;
}}

/* ── Menu ── */
QMenu {{
    background-color: {p.card};
    border: 1px solid {p.border};
    border-radius: {RADIUS.lg}px;
    padding: 6px;
    color: {p.text};
}}
QMenu::item {{
    padding: 8px 14px;
    border-radius: {RADIUS.md}px;
    font-size: {FONT_SIZE.body}px;
}}
QMenu::item:selected {{
    background-color: {p.accent_soft};
    color: {p.text};
}}
QMenu::separator {{
    height: 1px;
    background-color: {p.border};
    margin: 6px 8px;
}}
QMenu::indicator {{
    width: 16px;
    height: 16px;
}}

/* ── GroupBox — card-like ── */
QGroupBox {{
    background-color: {p.card};
    border: 1px solid {p.border};
    border-radius: {RADIUS.lg}px;
    margin-top: 12px;
    padding-top: 20px;
    font-weight: 600;
    font-size: {FONT_SIZE.subtitle}px;
    color: {p.text};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 10px;
    margin-left: 12px;
    background-color: {p.card};
    color: {p.text};
    border-radius: {RADIUS.sm}px;
}}

/* ── ListWidget ── */
QListWidget {{
    background-color: {p.card};
    border: 1px solid {p.border};
    border-radius: {RADIUS.lg}px;
    padding: 4px;
    outline: none;
}}
QListWidget::item {{
    padding: 10px 12px;
    border-radius: {RADIUS.md}px;
    color: {p.text_secondary};
    margin: 1px 2px;
}}
QListWidget::item:hover {{
    background-color: {p.surface};
    color: {p.text};
}}
QListWidget::item:selected {{
    background-color: {p.accent_soft};
    color: {p.accent};
    font-weight: 600;
}}

/* ── Tooltip ── */
QToolTip {{
    background-color: {p.text};
    color: {p.bg};
    border: none;
    border-radius: {RADIUS.md}px;
    padding: 6px 10px;
    font-size: {FONT_SIZE.caption}px;
}}

/* ── Badge / Pill ── */
QLabel#Badge {{
    border-radius: {RADIUS.pill}px;
    padding: 2px 8px;
    font-size: {FONT_SIZE.caption}px;
    font-weight: 600;
    letter-spacing: 0.04em;
}}
QLabel#BadgeDemo {{
    background-color: {p.warning_soft};
    color: {p.warning};
    border: 1px solid {p.warning}30;
}}
QLabel#BadgeReal {{
    background-color: {p.profit_soft};
    color: {p.profit};
    border: 1px solid {p.profit}30;
}}

/* ── Skeleton shimmer placeholder ── */
QFrame#Skeleton {{
    background-color: {p.surface};
    border: 1px solid {p.border};
    border-radius: {RADIUS.md}px;
}}

/* ── Divider ── */
QFrame#Divider {{
    background-color: {p.border};
    border: none;
}}
QFrame#VDivider {{
    background-color: {p.border};
    border: none;
}}

/* ── Focus ring for keyboard nav ── */
QPushButton:focus, QLineEdit:focus, QComboBox:focus, QCheckBox:focus {{
    outline: none;
}}
"""


def get_qss(theme: str = "dark") -> str:
    """Alias for build_qss — backwards compat."""
    return build_qss(theme)


# Legacy export name some code may import
QSS_TEMPLATE = build_qss("dark")
