"""Sidebar navigation widget — Phase 1."""

from __future__ import annotations

from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import QButtonGroup, QFrame, QLabel, QPushButton, QVBoxLayout, QWidget

from app.ui.i18n import tr
from app.ui.theme.tokens import get_tokens


class Sidebar(QFrame):
    """Vertical navigation sidebar with collapsible groups."""

    page_requested = Signal(str)
    collapsed_changed = Signal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self._collapsed = False
        self._buttons: dict[str, QPushButton] = {}
        self._group_labels: list[QLabel] = []

        tokens = get_tokens("dark")
        try:
            pad = int(getattr(getattr(tokens, "spacing", None), "sm", 8))  # type: ignore[arg-type]
        except Exception:
            pad = 8

        self.setFrameShape(QFrame.Shape.StyledPanel)

        root = QVBoxLayout(self)
        root.setContentsMargins(pad, pad, pad, pad)
        root.setSpacing(pad)

        # Collapse / expand button at top
        self.btn_collapse = QPushButton(tr("sidebar.collapse", default="⟨"), self)
        self.btn_collapse.setObjectName("SidebarCollapseButton")
        self.btn_collapse.setCheckable(False)
        self.btn_collapse.setToolTip(tr("sidebar.toggle_collapse", default="Collapse sidebar"))
        self.btn_collapse.clicked.connect(self.toggle_collapsed)
        root.addWidget(self.btn_collapse)

        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)

        # Define groups
        groups: list[tuple[str, list[tuple[str, str]]]] = [
            (
                tr("sidebar.group_trade", default="Trade"),
                [
                    ("dashboard", tr("nav.dashboard", default="Dashboard")),
                    ("market", tr("nav.market", default="Market")),
                    ("signals", tr("nav.signals", default="Signals")),
                    ("positions_trades", tr("nav.positions_trades", default="Positions & Trades")),
                ],
            ),
            (
                tr("sidebar.group_analyze", default="Analyze"),
                [
                    ("analytics", tr("nav.analytics", default="Analytics")),
                    ("journal", tr("nav.journal", default="Journal")),
                    ("backtest", tr("nav.backtest", default="Backtest")),
                    ("model", tr("nav.model", default="Model")),
                    ("ai_lab", tr("nav.ai_lab", default="AI Lab")),
                ],
            ),
            (
                tr("sidebar.group_system", default="System"),
                [
                    ("strategies", tr("nav.strategies", default="Strategies")),
                    ("risk", tr("nav.risk", default="Risk")),
                    ("logs", tr("nav.logs", default="Logs")),
                    ("health", tr("nav.health", default="Health")),
                    ("settings", tr("nav.settings", default="Settings")),
                ],
            ),
        ]

        for section_label, items in groups:
            lbl = QLabel(section_label, self)
            lbl.setObjectName("SidebarSectionLabel")
            lbl.setStyleSheet("font-size: 11px; font-weight: 600; opacity: 0.7; text-transform: uppercase;")
            self._group_labels.append(lbl)
            root.addWidget(lbl)
            for page_id, page_label in items:
                btn = QPushButton(page_label, self)
                btn.setObjectName(f"SidebarButton_{page_id}")
                btn.setCheckable(True)
                btn.setProperty("page_id", page_id)
                # Store full label for expand/collapse
                btn.setProperty("full_label", page_label)
                # Icon-only fallback: first letter
                btn.setProperty("icon_label", page_label[:2].upper())
                self._button_group.addButton(btn)
                btn.clicked.connect(self._on_button_clicked)
                self._buttons[page_id] = btn
                root.addWidget(btn)

        root.addStretch(1)

        # Select first page by default
        if "dashboard" in self._buttons:
            self._buttons["dashboard"].setChecked(True)

        self.setFixedWidth(220)

    @Slot()
    def _on_button_clicked(self) -> None:
        sender = self.sender()
        if isinstance(sender, QPushButton):
            page_id = str(sender.property("page_id"))
            self.page_requested.emit(page_id)

    @Slot()
    def toggle_collapsed(self) -> None:
        """Toggle collapsed state."""
        self.set_collapsed(not self._collapsed)

    def set_collapsed(self, collapsed: bool) -> None:
        """Set collapsed state explicitly."""
        self._collapsed = collapsed
        if collapsed:
            self.setFixedWidth(56)
            self.btn_collapse.setText(tr("sidebar.expand", default="⟩"))
            for lbl in self._group_labels:
                lbl.setVisible(False)
            for btn in self._buttons.values():
                icon_label = str(btn.property("icon_label"))
                btn.setText(icon_label)
        else:
            self.setFixedWidth(220)
            self.btn_collapse.setText(tr("sidebar.collapse", default="⟨"))
            for lbl in self._group_labels:
                lbl.setVisible(True)
            for btn in self._buttons.values():
                full_label = str(btn.property("full_label"))
                btn.setText(full_label)
        self.collapsed_changed.emit(collapsed)

    def is_collapsed(self) -> bool:
        """Return collapsed state."""
        return self._collapsed

    def set_active_page(self, page_id: str) -> None:
        """Programmatically set active page button."""
        btn = self._buttons.get(page_id)
        if btn is not None:
            btn.setChecked(True)
