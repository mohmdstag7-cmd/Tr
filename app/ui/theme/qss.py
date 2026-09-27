"""QSS generation from design tokens."""

from __future__ import annotations

from app.ui.theme.tokens import Tokens


def generate_qss(t: Tokens) -> str:
    """Generate the full QSS string for the application."""
    return f"""
/* Base */
QMainWindow {{
    background-color: {t.bg};
    color: {t.text};
}}
QWidget {{
    background-color: {t.bg};
    color: {t.text};
    font-family: {t.font_family_latin};
    font-size: 13px;
}}
QLabel {{
    background: transparent;
    color: {t.text};
    padding: 2px;
}}
QLabel[secondary="true"] {{
    color: {t.secondary};
}}

/* Card surface */
QFrame#CardFrame {{
    background-color: {t.card};
    border: {t.border_px}px solid {t.border};
    border-radius: {t.radius_px}px;
}}

/* Buttons */
QPushButton {{
    background-color: {t.accent};
    color: #FFFFFF;
    border: {t.border_px}px solid {t.accent};
    border-radius: {t.radius_px}px;
    padding: 8px 16px;
    font-weight: 600;
}}
QPushButton:hover {{
    background-color: {t.accent};
    border-color: {t.accent};
    opacity: 0.9;
}}
QPushButton:pressed {{
    background-color: {t.accent};
    padding-top: 9px;
    padding-bottom: 7px;
}}
QPushButton:disabled {{
    background-color: {t.surface};
    color: {t.secondary};
    border-color: {t.border};
}}
QPushButton[secondary="true"] {{
    background-color: {t.surface};
    color: {t.text};
    border: {t.border_px}px solid {t.border};
}}
QPushButton[secondary="true"]:hover {{
    background-color: {t.card};
    border-color: {t.secondary};
}}
QPushButton[danger="true"] {{
    background-color: {t.loss};
    border-color: {t.loss};
    color: #FFFFFF;
}}
QPushButton[success="true"] {{
    background-color: {t.profit};
    border-color: {t.profit};
    color: #FFFFFF;
}}

/* Inputs */
QLineEdit, QTextEdit {{
    background-color: {t.surface};
    color: {t.text};
    border: {t.border_px}px solid {t.border};
    border-radius: {t.radius_px}px;
    padding: 8px 10px;
    selection-background-color: {t.accent};
    selection-color: #FFFFFF;
}}
QLineEdit:focus, QTextEdit:focus {{
    border-color: {t.accent};
}}
QLineEdit:disabled, QTextEdit:disabled {{
    background-color: {t.bg};
    color: {t.secondary};
}}

/* ComboBox */
QComboBox {{
    background-color: {t.surface};
    color: {t.text};
    border: {t.border_px}px solid {t.border};
    border-radius: {t.radius_px}px;
    padding: 8px 10px;
    min-height: 20px;
}}
QComboBox:hover {{
    border-color: {t.secondary};
}}
QComboBox:focus {{
    border-color: {t.accent};
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox::down-arrow {{
    width: 12px;
    height: 12px;
}}
QComboBox QAbstractItemView {{
    background-color: {t.card};
    border: {t.border_px}px solid {t.border};
    selection-background-color: {t.accent};
    selection-color: #FFFFFF;
    padding: 4px;
}}

/* CheckBox */
QCheckBox {{
    spacing: 8px;
    background: transparent;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: {t.border_px}px solid {t.border};
    border-radius: 4px;
    background-color: {t.surface};
}}
QCheckBox::indicator:hover {{
    border-color: {t.secondary};
}}
QCheckBox::indicator:checked {{
    background-color: {t.accent};
    border-color: {t.accent};
}}
QCheckBox::indicator:disabled {{
    background-color: {t.bg};
    border-color: {t.border};
}}

/* Table */
QTableWidget {{
    background-color: {t.card};
    alternate-background-color: {t.surface};
    gridline-color: {t.border};
    border: {t.border_px}px solid {t.border};
    border-radius: {t.radius_px}px;
    padding: 4px;
}}
QTableWidget::item {{
    padding: 8px;
    border: none;
}}
QTableWidget::item:selected {{
    background-color: {t.accent};
    color: #FFFFFF;
}}
QHeaderView::section {{
    background-color: {t.surface};
    color: {t.secondary};
    padding: 8px 10px;
    border: none;
    border-bottom: {t.border_px}px solid {t.border};
    border-right: {t.border_px}px solid {t.border};
    font-weight: 600;
    font-size: 12px;
}}

/* ScrollBar */
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 0px;
}}
QScrollBar::handle:vertical {{
    background: {t.border};
    border-radius: 5px;
    min-height: 30px;
    margin: 2px;
}}
QScrollBar::handle:vertical:hover {{
    background: {t.secondary};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 0px;
}}
QScrollBar::handle:horizontal {{
    background: {t.border};
    border-radius: 5px;
    min-width: 30px;
    margin: 2px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {t.secondary};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: transparent;
}}

/* StatusBar & ToolBar */
QStatusBar {{
    background-color: {t.surface};
    color: {t.secondary};
    border-top: {t.border_px}px solid {t.border};
    padding: 4px 8px;
}}
QStatusBar::item {{
    border: none;
}}
QToolBar {{
    background-color: {t.surface};
    border: none;
    border-bottom: {t.border_px}px solid {t.border};
    spacing: 6px;
    padding: 6px;
}}
QToolBar::handle {{
    background: transparent;
}}

/* Splitter */
QSplitter::handle {{
    background-color: {t.border};
}}
QSplitter::handle:horizontal {{
    width: 1px;
}}
QSplitter::handle:vertical {{
    height: 1px;
}}

/* Menu */
QMenu {{
    background-color: {t.card};
    color: {t.text};
    border: {t.border_px}px solid {t.border};
    border-radius: {t.radius_px}px;
    padding: 6px;
}}
QMenu::item {{
    padding: 8px 16px;
    border-radius: 6px;
    margin: 1px 4px;
}}
QMenu::item:selected {{
    background-color: {t.surface};
    color: {t.text};
}}
QMenu::separator {{
    height: 1px;
    background: {t.border};
    margin: 6px 8px;
}}

/* TabBar */
QTabWidget::pane {{
    border: {t.border_px}px solid {t.border};
    border-radius: {t.radius_px}px;
    background-color: {t.card};
    top: -1px;
}}
QTabBar::tab {{
    background-color: transparent;
    color: {t.secondary};
    padding: 8px 16px;
    border: none;
    border-bottom: 2px solid transparent;
    margin-right: 4px;
}}
QTabBar::tab:selected {{
    color: {t.text};
    border-bottom-color: {t.accent};
    font-weight: 600;
}}
QTabBar::tab:hover {{
    color: {t.text};
}}

/* ProgressBar */
QProgressBar {{
    background-color: {t.surface};
    border: {t.border_px}px solid {t.border};
    border-radius: {t.radius_px}px;
    text-align: center;
    color: {t.text};
    height: 14px;
}}
QProgressBar::chunk {{
    background-color: {t.accent};
    border-radius: {t.radius_px}px;
}}

/* Frame & Separator */
QFrame {{
    border: none;
}}
QFrame[frameShape="4"], QFrame[frameShape="5"] {{
    border: 1px solid {t.border};
}}

/* Tooltip */
QToolTip {{
    background-color: {t.card};
    color: {t.text};
    border: {t.border_px}px solid {t.border};
    border-radius: 6px;
    padding: 6px 8px;
}}
"""
