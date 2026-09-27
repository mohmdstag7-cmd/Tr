"""Dashboard page — Phase 1 stub."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app.ui.i18n import tr
from app.ui.theme.tokens import get_tokens
from app.ui.widgets import EmptyState, KpiCard


class DashboardPage(QWidget):
    """Dashboard overview page (Phase 1 stub)."""

    refresh_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("DashboardPage")
        tokens = get_tokens("dark")

        root = QVBoxLayout(self)
        # Use tokens for spacing if available, fallback to 16
        try:
            pad = int(getattr(getattr(tokens, "spacing", None), "md", 16))  # type: ignore[arg-type]
        except Exception:
            pad = 16
        root.setContentsMargins(pad, pad, pad, pad)
        root.setSpacing(pad)

        title = QLabel(tr("dashboard.title", default="Dashboard"), self)
        title.setObjectName("PageTitle")
        title.setStyleSheet("font-size: 20px; font-weight: 700;")
        root.addWidget(title)

        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(pad)
        self.kpi_balance = KpiCard(title=tr("dashboard.kpi.balance", default="Balance"), value="—", parent=self)  # type: ignore[call-arg]
        self.kpi_today = KpiCard(title=tr("dashboard.kpi.today_pnl", default="Today P/L"), value="—", parent=self)  # type: ignore[call-arg]
        self.kpi_risk = KpiCard(title=tr("dashboard.kpi.open_risk", default="Open Risk"), value="—", parent=self)  # type: ignore[call-arg]
        kpi_row.addWidget(self.kpi_balance)
        kpi_row.addWidget(self.kpi_today)
        kpi_row.addWidget(self.kpi_risk)
        root.addLayout(kpi_row)

        self.empty = EmptyState(  # type: ignore[call-arg]
            headline=tr("common.empty_title", default="No data yet"),
            sub_headline=tr(
                "dashboard.empty_state",
                default="Connect your MT5 account to see live data.",
            ),
            parent=self,
        )
        # Fallback for widgets that expect `message` param
        try:
            _ = self.empty
        except Exception:
            self.empty = EmptyState(parent=self)  # type: ignore[call-arg]

        root.addWidget(self.empty, 1)

    def refresh_data(self) -> None:
        """Stub: refresh dashboard data (Phase 2+)."""
        self.refresh_requested.emit()
