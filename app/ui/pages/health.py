"""Health page with checks, metrics, and debug bundle."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.observability.debug_bundle import create_debug_bundle
from app.observability.health import health_registry
from app.observability.metrics import metrics
from app.observability.watchdog import watchdog


class HealthPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("HealthPage")
        layout = QVBoxLayout(self)

        from app.ui.i18n import tr

        _title = QLabel(tr("health.title", default="Health"), self)
        _title.setObjectName("PageTitle")
        _title.setStyleSheet("font-size: 20px; font-weight: 700;")
        layout.addWidget(_title)

        # Top: health checks table
        layout.addWidget(QLabel("Health Checks"))
        self.checks_table = QTableWidget(0, 5)
        self.checks_table.setHorizontalHeaderLabels(["Check", "Status", "Message", "Last checked", "Value"])
        self.checks_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.checks_table)

        btn_row = QHBoxLayout()
        self.btn_run_checks = QPushButton("Run all checks now")
        self.btn_run_checks.clicked.connect(self._run_checks)
        btn_row.addWidget(self.btn_run_checks)

        self.btn_debug_bundle = QPushButton("Create debug bundle")
        self.btn_debug_bundle.setStyleSheet("color: red; border: 1px solid red; padding: 6px;")
        self.btn_debug_bundle.clicked.connect(self._on_debug_bundle)
        btn_row.addWidget(self.btn_debug_bundle)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Middle: performance metrics
        layout.addWidget(QLabel("Performance Metrics"))
        metrics_row = QHBoxLayout()
        self.cpu_bar = QProgressBar()
        self.cpu_bar.setRange(0, 100)
        self.cpu_bar.setFormat("CPU %p%")
        metrics_row.addWidget(QLabel("CPU%"))
        metrics_row.addWidget(self.cpu_bar)

        self.ram_bar = QProgressBar()
        self.ram_bar.setRange(0, 500)
        self.ram_bar.setFormat("%v MB / 500 MB")
        metrics_row.addWidget(QLabel("RAM"))
        metrics_row.addWidget(self.ram_bar)

        self.latency_label = QLabel("bar p50/p95: -/-")
        metrics_row.addWidget(self.latency_label)
        metrics_row.addStretch()
        layout.addLayout(metrics_row)

        self.mt5_table = QTableWidget(0, 4)
        self.mt5_table.setHorizontalHeaderLabels(["MT5 Action", "p50", "p95", "count"])
        layout.addWidget(self.mt5_table)

        # Bottom: worker status
        layout.addWidget(QLabel("Worker Status"))
        self.worker_table = QTableWidget(0, 4)
        self.worker_table.setHorizontalHeaderLabels(["Worker", "Last heartbeat", "Freeze s", "Alive"])
        layout.addWidget(self.worker_table)

        # Timers
        self._health_timer = QTimer(self)
        self._health_timer.setInterval(60000)
        self._health_timer.timeout.connect(self._run_checks)
        self._health_timer.start()

        self._metrics_timer = QTimer(self)
        self._metrics_timer.setInterval(5000)
        self._metrics_timer.timeout.connect(self._refresh_metrics)
        self._metrics_timer.start()

        self._worker_timer = QTimer(self)
        self._worker_timer.setInterval(5000)
        self._worker_timer.timeout.connect(self._refresh_workers)
        self._worker_timer.start()

        self._run_checks()
        self._refresh_metrics()
        self._refresh_workers()

    def _run_checks(self) -> None:
        results = health_registry.run_all()
        self.checks_table.setRowCount(len(results))
        for row, (_name, hc) in enumerate(results.items()):
            self.checks_table.setItem(row, 0, QTableWidgetItem(hc.name))
            status_item = QTableWidgetItem(hc.status)
            if hc.status == "ok":
                status_item.setBackground(Qt.GlobalColor.green)
            elif hc.status == "warning":
                status_item.setBackground(Qt.GlobalColor.yellow)
            elif hc.status == "error":
                status_item.setBackground(Qt.GlobalColor.red)
            elif hc.status == "unknown":
                status_item.setBackground(Qt.GlobalColor.gray)
            self.checks_table.setItem(row, 1, status_item)
            self.checks_table.setItem(row, 2, QTableWidgetItem(hc.message))
            last = hc.last_checked.strftime("%Y-%m-%d %H:%M:%S") if hc.last_checked else "-"
            self.checks_table.setItem(row, 3, QTableWidgetItem(last))
            self.checks_table.setItem(row, 4, QTableWidgetItem(str(hc.value) if hc.value is not None else "-"))

    def _refresh_metrics(self) -> None:
        snap = metrics.snapshot()
        cpu = snap.get("cpu_pct", 0)
        ram = snap.get("ram_mb", 0)
        self.cpu_bar.setValue(int(cpu))
        self.ram_bar.setValue(int(min(ram, 500)))
        bar = snap.get("bar_latency", {})
        self.latency_label.setText(f"bar p50/p95: {bar.get('p50', 0):.3f}/{bar.get('p95', 0):.3f}s")
        mt5_data = snap.get("mt5_latency", {})
        self.mt5_table.setRowCount(len(mt5_data))
        for row, (action, vals) in enumerate(mt5_data.items()):
            self.mt5_table.setItem(row, 0, QTableWidgetItem(action))
            self.mt5_table.setItem(row, 1, QTableWidgetItem(f"{vals.get('p50', 0):.3f}"))
            self.mt5_table.setItem(row, 2, QTableWidgetItem(f"{vals.get('p95', 0):.3f}"))
            self.mt5_table.setItem(row, 3, QTableWidgetItem(str(int(vals.get("count", 0)))))

    def _refresh_workers(self) -> None:
        statuses = watchdog.all_statuses()
        self.worker_table.setRowCount(len(statuses))
        for row, st in enumerate(statuses):
            self.worker_table.setItem(row, 0, QTableWidgetItem(st.name))
            hb = st.last_heartbeat.strftime("%H:%M:%S") if st.last_heartbeat else "-"
            self.worker_table.setItem(row, 1, QTableWidgetItem(hb))
            self.worker_table.setItem(row, 2, QTableWidgetItem(f"{st.freeze_seconds:.1f}"))
            alive_item = QTableWidgetItem("●" if st.is_alive else "○")
            alive_item.setForeground(Qt.GlobalColor.green if st.is_alive else Qt.GlobalColor.red)
            self.worker_table.setItem(row, 3, alive_item)

    def _on_debug_bundle(self) -> None:
        try:
            path = create_debug_bundle()
            QMessageBox.information(self, "Debug bundle", f"Created: {path}")
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))
