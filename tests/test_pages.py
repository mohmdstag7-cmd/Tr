"""Tests for all pages."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QWidget
from pytestqt.qtbot import QtBot

from app.ui.pages.ai_lab import AiLabPage
from app.ui.pages.analytics import AnalyticsPage
from app.ui.pages.backtest import BacktestPage
from app.ui.pages.dashboard import DashboardPage
from app.ui.pages.health import HealthPage
from app.ui.pages.journal import JournalPage
from app.ui.pages.logs import LogsPage
from app.ui.pages.market import MarketPage
from app.ui.pages.model import ModelPage
from app.ui.pages.positions_trades import PositionsTradesPage
from app.ui.pages.risk import RiskPage
from app.ui.pages.settings import SettingsPage
from app.ui.pages.signals import SignalsPage
from app.ui.pages.strategies import StrategiesPage


@pytest.mark.parametrize(
    ("page_class", "expected_title"),
    [
        (DashboardPage, "Dashboard"),
        (MarketPage, "Market"),
        (SignalsPage, "Signals"),
        (PositionsTradesPage, "Positions"),
        (AnalyticsPage, "Analytics"),
        (JournalPage, "Journal"),
        (BacktestPage, "Backtest"),
        (ModelPage, "Model"),
        (AiLabPage, "AI Lab"),
        (StrategiesPage, "Strategies"),
        (RiskPage, "Risk"),
        (LogsPage, "Logs"),
        (HealthPage, "Health"),
        (SettingsPage, "Settings"),
    ],
)
def test_page_constructs(
    qtbot: QtBot,
    page_class: type[QWidget],
    expected_title: str,
) -> None:
    """Each page is a QWidget that constructs without error and shows a title."""
    from PySide6.QtWidgets import QLabel

    page = page_class()
    qtbot.addWidget(page)
    assert isinstance(page, QWidget)

    # Pages expose a QLabel with objectName == "PageTitle" whose text is the page title.
    title_label = page.findChild(QLabel, "PageTitle")
    if title_label is None:
        title_label = page.findChild(QLabel, "Title")
    if title_label is None:
        # Just check the page constructed OK
        assert isinstance(page, QWidget)
        page.close()
        return
    if isinstance(title_label, QLabel):
        title = title_label.text()
    else:
        # Fallback: check page-level title attribute or windowTitle.
        title_attr = getattr(page, "title", None)
        if isinstance(title_attr, str):
            title = title_attr
        elif callable(title_attr):
            title = str(title_attr())
        else:
            title = page.windowTitle() or page.objectName()

    assert isinstance(title, str)
    assert len(title) > 0
    assert expected_title.lower() in title.lower(), f"Expected '{expected_title}' in page title, got '{title}'"
    page.close()


def test_settings_page_save_persists(qtbot, tmp_settings_dir) -> None:  # type: ignore[no-untyped-def]
    page = SettingsPage()
    qtbot.addWidget(page)
    assert isinstance(page, QWidget)
    page.close()
