"""Command palette dialog — Phase 1."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import QDialog, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from app.ui.i18n import tr
from app.ui.theme.tokens import get_tokens


class CommandPalette(QDialog):
    """Modal command palette opened with Ctrl+K."""

    command_executed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("CommandPalette")
        self.setModal(True)
        self.setWindowTitle(tr("command_palette.title", default="Command Palette"))
        self.resize(520, 380)

        tokens = get_tokens("dark")
        try:
            pad = int(getattr(getattr(tokens, "spacing", None), "md", 16))  # type: ignore[arg-type]
        except Exception:
            pad = 16

        layout = QVBoxLayout(self)
        layout.setContentsMargins(pad, pad, pad, pad)
        layout.setSpacing(pad)

        self.search = QLineEdit(self)
        self.search.setObjectName("CommandPaletteSearch")
        self.search.setPlaceholderText(tr("command_palette.placeholder", default="Type a command…"))
        self.search.textChanged.connect(self._on_filter)
        layout.addWidget(self.search)

        self.list = QListWidget(self)
        self.list.setObjectName("CommandPaletteList")
        self.list.itemActivated.connect(self._on_activated)
        self.list.itemClicked.connect(self._on_activated)
        layout.addWidget(self.list, 1)

        # Phase 1 stub commands: (id, label)
        self._commands: list[tuple[str, str]] = [
            ("go_dashboard", tr("command.go_dashboard", default="Go to Dashboard")),
            ("go_market", tr("command.go_market", default="Go to Market")),
            ("go_signals", tr("command.go_signals", default="Go to Signals")),
            (
                "go_positions_trades",
                tr("command.go_positions_trades", default="Go to Positions & Trades"),
            ),
            ("go_analytics", tr("command.go_analytics", default="Go to Analytics")),
            ("go_journal", tr("command.go_journal", default="Go to Journal")),
            ("go_backtest", tr("command.go_backtest", default="Go to Backtest")),
            ("go_model", tr("command.go_model", default="Go to Model")),
            ("go_ai_lab", tr("command.go_ai_lab", default="Go to AI Lab")),
            ("go_strategies", tr("command.go_strategies", default="Go to Strategies")),
            ("go_risk", tr("command.go_risk", default="Go to Risk")),
            ("go_logs", tr("command.go_logs", default="Go to Logs")),
            ("go_health", tr("command.go_health", default="Go to Health")),
            ("go_settings", tr("command.go_settings", default="Go to Settings")),
            ("toggle_simple", tr("command.toggle_simple", default="Toggle Simple/Advanced")),
            ("toggle_theme", tr("command.toggle_theme", default="Toggle Dark/Light Theme")),
            ("toggle_language", tr("command.toggle_language", default="Toggle Language (EN/FA)")),
            ("kill_switch", tr("command.kill_switch", default="Kill switch (with confirm)")),
        ]
        self._populate(self._commands)

        # Enter triggers first visible item
        self.search.returnPressed.connect(self._on_enter)

    def _populate(self, commands: list[tuple[str, str]]) -> None:
        self.list.clear()
        for cmd_id, label in commands:
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, cmd_id)
            self.list.addItem(item)
        if self.list.count() > 0:
            self.list.setCurrentRow(0)

    @Slot(str)
    def _on_filter(self, text: str) -> None:
        needle = text.strip().lower()
        if not needle:
            self._populate(self._commands)
            return
        filtered = [(cid, lbl) for cid, lbl in self._commands if needle in lbl.lower() or needle in cid.lower()]
        self._populate(filtered)

    @Slot(QListWidgetItem)
    def _on_activated(self, item: QListWidgetItem) -> None:
        cmd_id = str(item.data(Qt.ItemDataRole.UserRole))
        self.command_executed.emit(cmd_id)
        self.accept()

    @Slot()
    def _on_enter(self) -> None:
        item = self.list.currentItem()
        if item is None and self.list.count() > 0:
            item = self.list.item(0)
        if item is not None:
            self._on_activated(item)

    def open_palette(self) -> None:
        """Open and focus the palette."""
        self.search.clear()
        self._populate(self._commands)
        self.search.setFocus()
        self.show()
        self.raise_()
        self.activateWindow()
