"""Diagnostics page."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHeaderView,
    QInputDialog,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.mt5.diagnostics import ConnectionDiagnostics
from app.mt5.gateway import MT5Gateway
from app.mt5.profiles import AccountProfile, ProfileManager


class DiagnosticsPage(QWidget):
    def __init__(self, gateway: MT5Gateway | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.gateway = gateway
        self._last_checks: dict = {}
        self._last_report: str = ""

        layout = QVBoxLayout(self)

        self.run_btn = QPushButton("Run all checks now")
        self.run_btn.clicked.connect(self._run_checks)
        layout.addWidget(self.run_btn)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Check", "Status", "Detail"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        self.report_view = QPlainTextEdit()
        self.report_view.setReadOnly(True)
        self.report_view.setPlaceholderText("Report will appear here...")
        layout.addWidget(self.report_view)

        self.copy_btn = QPushButton("Copy report")
        self.copy_btn.clicked.connect(self._copy_report)
        layout.addWidget(self.copy_btn)

        self.save_profile_btn = QPushButton("Save profile")
        self.save_profile_btn.setEnabled(False)
        self.save_profile_btn.clicked.connect(self._save_profile)
        layout.addWidget(self.save_profile_btn)

    def set_gateway(self, gateway: MT5Gateway) -> None:
        self.gateway = gateway

    def _run_checks(self) -> None:
        if self.gateway is None:
            QMessageBox.warning(self, "No gateway", "MT5 gateway not initialized")
            return
        diag = ConnectionDiagnostics(self.gateway, self)
        checks = diag.run_all_checks()
        self._last_checks = checks
        self._last_report = diag.generate_text_report(checks)
        self.report_view.setPlainText(self._last_report)
        self.table.setRowCount(len(checks))
        for i, (name, chk) in enumerate(checks.items()):
            self.table.setItem(i, 0, QTableWidgetItem(name))
            item = QTableWidgetItem(chk.status)
            if chk.status == "ok":
                item.setBackground(Qt.GlobalColor.green)
            elif chk.status == "warning":
                item.setBackground(Qt.GlobalColor.yellow)
            elif chk.status == "error":
                item.setBackground(Qt.GlobalColor.red)
            self.table.setItem(i, 1, item)
            self.table.setItem(i, 2, QTableWidgetItem(chk.detail))
        # enable save if account ok
        acc_ok = checks.get("account") and checks["account"].status == "ok"
        self.save_profile_btn.setEnabled(bool(acc_ok))

    def _copy_report(self) -> None:
        from PySide6.QtWidgets import QApplication

        QApplication.clipboard().setText(self.report_view.toPlainText())

    def _save_profile(self) -> None:
        if self.gateway is None:
            return
        try:
            acc = self.gateway.account_info().result(timeout=5)
            term = self.gateway.terminal_info().result(timeout=5)
        except Exception:
            return
        if acc is None:
            return
        name, ok = QInputDialog.getText(self, "Save profile", "Profile name:", text=str(acc.login))
        if not ok or not name:
            return
        pm = ProfileManager()
        prof = AccountProfile(name=name, login=acc.login, server=acc.server, terminal_path=term.path if term else None)
        pm.save(prof)
        pm.set_default(name)
        QMessageBox.information(self, "Saved", f"Profile '{name}' saved")
