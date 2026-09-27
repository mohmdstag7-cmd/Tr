"""First-run wizard dialog."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.mt5.connection_wizard import ConnectionWizard
from app.mt5.gateway import MT5Gateway
from app.mt5.terminal_discovery import find_terminals


class ConnectionWizardDialog(QDialog):
    connected = Signal(object)

    def __init__(self, gateway: MT5Gateway, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.gateway = gateway
        self.setWindowTitle("MT5 Connection Wizard")
        self.resize(600, 500)
        self._wizard = ConnectionWizard(gateway, self)
        self._wizard.connection_progress.connect(self._on_progress)
        self._wizard.connection_success.connect(self._on_success)
        self._wizard.connection_failed.connect(self._on_failed)
        self._wizard.investor_mode.connect(self._on_investor)

        layout = QVBoxLayout(self)

        # Step 1: terminal picker
        layout.addWidget(QLabel("Step 1: Select Terminal"))
        row1 = QHBoxLayout()
        self.terminal_combo = QComboBox()
        self._terminals = find_terminals()
        for t in self._terminals:
            self.terminal_combo.addItem(f"{t.broker_name} — {t.path}", str(t.path))
        if not self._terminals:
            self.terminal_combo.addItem("(No terminals found — browse manually)", "")
        row1.addWidget(self.terminal_combo, 1)
        self.browse_btn = QPushButton("Browse…")
        self.browse_btn.clicked.connect(self._browse)
        row1.addWidget(self.browse_btn)
        layout.addLayout(row1)

        # Step 2: account details
        layout.addWidget(QLabel("Step 2: Account Details"))
        form = QFormLayout()
        self.login_edit = QLineEdit()
        self.login_edit.setPlaceholderText("12345678")
        form.addRow("Login:", self.login_edit)
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Password:", self.password_edit)
        self.server_edit = QComboBox()
        self.server_edit.setEditable(True)
        self.server_edit.addItems(["", "MetaQuotes-Demo", "ICMarkets-Demo", "ICMarkets-Live"])
        form.addRow("Server:", self.server_edit)
        layout.addLayout(form)

        # Step 3: connect
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self._connect)
        layout.addWidget(self.connect_btn)

        # checklist
        layout.addWidget(QLabel("Progress:"))
        self.checklist_layout = QVBoxLayout()
        self._check_labels: dict[str, QLabel] = {}
        for step in [
            "terminal_found",
            "login_ok",
            "account_info_loaded",
            "algo_trading_on",
            "trading_allowed",
            "symbols_available",
            "live_quotes",
            "history_available",
        ]:
            lbl = QLabel(f"● {step}: pending")
            lbl.setStyleSheet("color: gray;")
            self._check_labels[step] = lbl
            self.checklist_layout.addWidget(lbl)
        layout.addLayout(self.checklist_layout)

        self.investor_banner = QLabel("Investor password detected — Analysis-only mode enabled")
        self.investor_banner.setStyleSheet(
            "background: #fff3cd; color: #856404; padding: 6px; border: 1px solid #ffeaa7;"
        )
        self.investor_banner.setVisible(False)
        layout.addWidget(self.investor_banner)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select terminal64.exe", "", "Executable (terminal64.exe)")
        if path:
            self.terminal_combo.addItem(path, path)
            self.terminal_combo.setCurrentIndex(self.terminal_combo.count() - 1)

    def _connect(self) -> None:
        try:
            login = int(self.login_edit.text().strip())
        except ValueError:
            self.status_label.setText("Invalid login — must be integer")
            return
        password = self.password_edit.text()
        server = self.server_edit.currentText().strip()
        if not password or not server:
            self.status_label.setText("Password and server required")
            return
        terminal_path = self.terminal_combo.currentData()
        if not terminal_path:
            terminal_path = None
        self.status_label.setText("Connecting…")
        self.connect_btn.setEnabled(False)
        for lbl in self._check_labels.values():
            lbl.setText(lbl.text().replace("pending", "pending"))
            lbl.setStyleSheet("color: gray;")
        self._wizard.start(terminal_path, login, password, server)

    def _on_progress(self, step: str, status: str) -> None:
        lbl = self._check_labels.get(step)
        if lbl:
            color = {"pending": "gray", "ok": "green", "warning": "#b58900", "error": "red"}.get(status, "gray")
            dot = {"pending": "●", "ok": "✔", "warning": "⚠", "error": "✘"}.get(status, "●")
            lbl.setText(f"{dot} {step}: {status}")
            lbl.setStyleSheet(f"color: {color};")

    def _on_success(self, account: object, terminal: object) -> None:  # type: ignore[no-untyped-def]
        self.status_label.setText("Connected successfully!")
        self.status_label.setStyleSheet("color: green;")
        self.connect_btn.setEnabled(True)
        self.connected.emit(account)
        self.accept()

    def _on_failed(self, step: str, error: str) -> None:
        self.status_label.setText(f"Failed at {step}: {error}")
        self.status_label.setStyleSheet("color: red;")
        self.connect_btn.setEnabled(True)
        self.connect_btn.setText("Try again")

    def _on_investor(self) -> None:
        self.investor_banner.setVisible(True)
