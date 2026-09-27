"""DataTable widget - styled QTableWidget wrapper."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from app.ui.theme.tokens import get_tokens


def _resolve_color(tokens: Any, name: str, fallback: str) -> str:
    try:
        if hasattr(tokens, "colors"):
            colors = tokens.colors
            if hasattr(colors, name):
                return str(getattr(colors, name))
            if isinstance(colors, dict) and name in colors:
                return str(colors[name])
        if isinstance(tokens, dict) and name in tokens:
            return str(tokens[name])
        if hasattr(tokens, name):
            return str(getattr(tokens, name))
    except Exception:
        pass
    return fallback


class DataTable(QTableWidget):
    """QTableWidget with sensible defaults and token-aware styling."""

    def __init__(
        self,
        columns: list[str],
        data: list[list[Any]] | None = None,
        hide_vertical_header: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._columns: list[str] = list(columns)
        self._tokens: Any = None
        try:
            self._tokens = get_tokens()
        except Exception:
            self._tokens = None

        self.setColumnCount(len(self._columns))
        self.setHorizontalHeaderLabels(self._columns)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setShowGrid(False)
        self.verticalHeader().setVisible(not hide_vertical_header)
        self.verticalHeader().setDefaultSectionSize(32)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setHighlightSections(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setWordWrap(False)

        # Enable tabular numbers for cells via font
        font: QFont = self.font()
        try:
            Tag = getattr(QFont, "Tag", None)
            if Tag is not None:
                try:
                    tag_val = Tag(b"tnum")  # type: ignore[call-arg]
                    font.setFeature(tag_val, 1)
                except Exception:
                    pass
            else:
                font.setFeature("tnum", 1)  # type: ignore[arg-type]
        except Exception:
            pass
        self.setFont(font)

        if data is not None:
            self.set_data(data)

        self.reapply_tokens(self._tokens)

    def set_data(self, rows: list[list[Any]]) -> None:
        self.setSortingEnabled(False)
        self.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c in range(len(self._columns)):
                val: Any = row[c] if c < len(row) else ""
                item = QTableWidgetItem(str(val))
                # Store raw value for accessor
                item.setData(Qt.ItemDataRole.UserRole, val)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.setItem(r, c, item)
        self.setSortingEnabled(True)

    def cell_value(self, row: int, col: int) -> Any:
        item = self.item(row, col)
        if item is None:
            return None
        data = item.data(Qt.ItemDataRole.UserRole)
        if data is not None:
            return data
        return item.text()

    def reapply_tokens(self, tokens: Any | None = None) -> None:
        if tokens is not None:
            self._tokens = tokens
        if self._tokens is None:
            try:
                self._tokens = get_tokens()
            except Exception:
                self._tokens = None

        bg = _resolve_color(self._tokens, "background", "#121214")
        surface = _resolve_color(self._tokens, "surface", "#1e1e24")
        card = _resolve_color(self._tokens, "card", "#1e1e24")
        border = _resolve_color(self._tokens, "border", "#2d2d36")
        text_primary = _resolve_color(self._tokens, "text_primary", "#f5f5f7")
        text_secondary = _resolve_color(self._tokens, "text_secondary", "#9aa0b2")
        accent = _resolve_color(self._tokens, "accent", "#7b61ff")

        self.setStyleSheet(
            f"""
            QTableWidget {{
                background-color: {card};
                color: {text_primary};
                border: 1px solid {border};
                border-radius: 12px;
                gridline-color: transparent;
                alternate-background-color: {surface};
                selection-background-color: {accent};
                selection-color: #ffffff;
            }}
            QHeaderView::section {{
                background-color: {surface};
                color: {text_secondary};
                padding: 8px;
                border: none;
                border-bottom: 1px solid {border};
                border-right: 1px solid {border};
                font-size: 11px;
                font-weight: 600;
                text-transform: uppercase;
            }}
            QHeaderView::section:last {{
                border-right: none;
            }}
            QTableWidget::item {{
                padding: 8px;
                border: none;
                border-bottom: 1px solid {border};
            }}
            QTableWidget::item:selected {{
                background-color: {accent};
                color: #ffffff;
            }}
            QScrollBar:vertical, QScrollBar:horizontal {{
                background: {bg};
                border: none;
                width: 8px;
                height: 8px;
            }}
            QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
                background: {border};
                border-radius: 4px;
                min-height: 24px;
            }}
            """
        )

    def set_tokens(self, tokens: Any) -> None:
        self.reapply_tokens(tokens)
