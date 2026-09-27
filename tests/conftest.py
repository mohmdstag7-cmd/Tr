"""Common fixtures for MT5 Trading Workstation tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from PySide6.QtWidgets import QApplication

from app.core.event_bus import EventBus
from app.ui.theme.tokens import get_tokens


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    """Return a QApplication instance, reusing existing one if present."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    assert isinstance(app, QApplication)
    return app


@pytest.fixture
def tokens_dark() -> Any:
    """Return dark theme tokens."""
    return get_tokens("dark")


@pytest.fixture
def tokens_light() -> Any:
    """Return light theme tokens."""
    return get_tokens("light")


@pytest.fixture
def event_bus_clean() -> EventBus:
    """Return a fresh EventBus instance for test isolation."""
    return EventBus()


@pytest.fixture
def tmp_settings_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Monkeypatch app.core.config so reads/writes go to a temp directory."""
    import app.core.config as config_module  # noqa: WPS433

    config_file = tmp_path / "config.json"

    # The module exposes a _config_path() helper; redirect it to our temp file.
    monkeypatch.setattr(config_module, "_config_path", lambda: config_file, raising=False)

    # Also redirect legacy attribute names in case future phases add them.
    monkeypatch.setattr(config_module, "SETTINGS_DIR", tmp_path, raising=False)
    monkeypatch.setattr(config_module, "SETTINGS_PATH", config_file, raising=False)
    monkeypatch.setattr(config_module, "CONFIG_DIR", tmp_path, raising=False)
    monkeypatch.setattr(config_module, "CONFIG_PATH", config_file, raising=False)

    if hasattr(config_module, "get_settings_dir"):

        def _get_dir() -> Path:
            return tmp_path

        monkeypatch.setattr(config_module, "get_settings_dir", _get_dir, raising=False)

    if hasattr(config_module, "get_settings_path"):

        def _get_path() -> Path:
            return config_file

        monkeypatch.setattr(config_module, "get_settings_path", _get_path, raising=False)

    if hasattr(config_module, "get_config_dir"):

        def _get_config_dir() -> Path:
            return tmp_path

        monkeypatch.setattr(config_module, "get_config_dir", _get_config_dir, raising=False)

    return tmp_path
