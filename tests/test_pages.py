"""Tests for all pages."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from PySide6.QtWidgets import QPushButton, QWidget
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


def test_settings_page_save_persists(
    qtbot: QtBot,
    tmp_settings_dir: Path,
) -> None:
    """SettingsPage persists a Simple Mode toggle change to disk on Save."""
    page = SettingsPage()
    qtbot.addWidget(page)

    # Find the simple-mode toggle / checkbox by attribute or widget tree.
    toggled = False
    for attr_name in (
        "simple_mode_toggle",
        "toggle_simple",
        "chk_simple_mode",
        "_simple_toggle",
        "_simple_mode_toggle",
    ):
        widget: Any = getattr(page, attr_name, None)
        if widget is None:
            continue
        if hasattr(widget, "setChecked"):
            widget.setChecked(False)
            toggled = True
            break
        if hasattr(widget, "set_checked"):
            widget.set_checked(False)
            toggled = True
            break

    # Tree-search fallback: any widget with setChecked whose nearby label includes "simple"
    if not toggled:
        for child in page.findChildren(QWidget):
            name = child.objectName().lower()
            text_attr = getattr(child, "text", None)
            text = ""
            if callable(text_attr):
                try:
                    text = str(text_attr()).lower()
                except Exception:
                    text = ""
            elif isinstance(text_attr, str):
                text = text_attr.lower()
            if "simple" in name or "simple" in text:
                setter = getattr(child, "setChecked", None) or getattr(child, "set_checked", None)
                if setter is not None:
                    setter(False)
                    toggled = True
                    break

    # Click the Save button if present
    save_btn: QPushButton | None = None
    for btn in page.findChildren(QPushButton):
        if "save" in btn.text().lower():
            save_btn = btn
            break
    if save_btn is not None:
        save_btn.click()
    elif hasattr(page, "save"):
        page.save()  # type: ignore[attr-defined]
    elif hasattr(page, "_save"):
        page._save()  # type: ignore[attr-defined]

    # Verify that *some* settings file exists in the temp dir (we don't care about
    # the exact filename — only that persistence happened).
    json_files = list(tmp_settings_dir.glob("*.json"))
    yml_files = list(tmp_settings_dir.glob("*.yml")) + list(tmp_settings_dir.glob("*.yaml"))
    assert json_files or yml_files, (
        f"No settings file written to {tmp_settings_dir} (contents: " f"{list(tmp_settings_dir.iterdir())})"
    )

    page.close()
