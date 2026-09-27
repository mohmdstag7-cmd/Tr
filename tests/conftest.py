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


@pytest.fixture
def tmp_updates_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Provide a temp dir for the updater's previous_installer storage.

    Patches the data dir used by :class:`app.updater.installer.Installer` and
    the ``MT5_DATA_DIR`` env var so no real user data is touched.
    """
    updates_dir = tmp_path / "updates_data"
    updates_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("MT5_DATA_DIR", str(updates_dir))

    try:
        import app.updater.installer as inst_mod  # noqa: WPS433

        if hasattr(inst_mod, "_get_data_dir"):
            monkeypatch.setattr(inst_mod, "_get_data_dir", lambda: updates_dir)
    except ImportError:
        # Updater module not importable on this platform; skip.
        pass

    return updates_dir


@pytest.fixture
def tmp_log_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect loguru sinks to a tmp_path; configure_logging() is called by the test."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Reset loguru to defaults first so previous tests' sinks don't interfere.
    from loguru import logger

    logger.remove()

    # Patch the module-level _log_dir so get_log_dir() returns our tmp_path.
    import app.observability.logger as logger_mod  # noqa: WPS433

    monkeypatch.setattr(logger_mod, "_log_dir", log_dir, raising=False)

    yield log_dir

    # Teardown: remove all sinks and reset state.
    logger.remove()
    monkeypatch.setattr(logger_mod, "_log_dir", None, raising=False)


@pytest.fixture
def tmp_crash_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect crash handler to a tmp_path."""
    crash_dir = tmp_path / "crash_reports"
    crash_dir.mkdir(parents=True, exist_ok=True)

    import app.observability.crash_handler as crash_mod  # noqa: WPS433

    if hasattr(crash_mod, "_crash_dir"):
        monkeypatch.setattr(crash_mod, "_crash_dir", crash_dir, raising=False)
    if hasattr(crash_mod, "get_crash_dir"):
        monkeypatch.setattr(crash_mod, "get_crash_dir", lambda: crash_dir, raising=False)

    return crash_dir


@pytest.fixture
def tmp_audit_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect audit log to a tmp_path."""
    audit_dir = tmp_path / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)

    import app.observability.audit as audit_mod  # noqa: WPS433

    if hasattr(audit_mod, "_audit_dir"):
        monkeypatch.setattr(audit_mod, "_audit_dir", audit_dir, raising=False)

    # Re-create the singleton audit_log so it picks up the new dir.
    if hasattr(audit_mod, "audit_log") and hasattr(audit_mod.audit_log, "_dir"):
        monkeypatch.setattr(audit_mod.audit_log, "_dir", audit_dir, raising=False)

    return audit_dir


@pytest.fixture(autouse=True, scope="session")
def _configure_logging_for_session(tmp_path_factory: pytest.TempPathFactory) -> Any:
    """Configure logging ONCE per session so background threads (UpdateChecker,
    watchdog) don't crash when their log call hits a sink being torn down.

    Tests that need a fresh log dir use the ``tmp_log_dir`` fixture instead.
    """
    from loguru import logger

    logger.remove()
    log_dir = tmp_path_factory.mktemp("logs_session")

    import app.observability.logger as logger_mod  # noqa: WPS433

    logger_mod._log_dir = log_dir  # type: ignore[attr-defined]
    try:
        logger_mod.configure_logging(log_dir=log_dir, default_level="DEBUG")
    except Exception:
        pass

    yield log_dir

    logger.remove()
    logger_mod._log_dir = None  # type: ignore[attr-defined]


@pytest.fixture(autouse=True)
def _disable_auto_update_check_in_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    """Disable the 5-second auto-update-check QTimer in MainWindow during tests.

    Background: MainWindow reads ``AppSettings.check_updates_on_startup`` and
    schedules an UpdateChecker call 5s after construction. The UpdateChecker
    runs in a QThread and writes logs via loguru — which races with tests
    that call ``configure_logging()`` themselves and ``logger.remove()``.

    We patch ``QTimer.singleShot`` to a no-op so the auto-check never fires.
    """
    from PySide6.QtCore import QTimer

    def _no_op_single_shot(*args: object, **kwargs: object) -> None:  # noqa: ARG001
        return None

    monkeypatch.setattr(QTimer, "singleShot", _no_op_single_shot, raising=False)


# ----------------------------------------------------------------- Phase 3
@pytest.fixture
def fake_mt5() -> Any:
    """Return a configured FakeMT5 instance.

    The fake replaces the real ``MetaTrader5`` module everywhere it's imported,
    so tests can run on Linux CI where the real package isn't installable.
    """
    from tests.fakes.fake_mt5 import FakeMT5

    return FakeMT5()


@pytest.fixture
def mt5_gateway_with_fake(fake_mt5: Any, monkeypatch: pytest.MonkeyPatch, qapp: QApplication) -> Any:
    """Create an MT5Gateway wired to FakeMT5 via monkeypatching the import.

    Returns the gateway instance. Tests can then call gateway.initialize(...)
    with fake credentials.
    """
    import sys

    # Insert FakeMT5 as `MetaTrader5` so the gateway picks it up.
    monkeypatch.setitem(sys.modules, "MetaTrader5", fake_mt5)

    from app.mt5.gateway import MT5Gateway

    gateway = MT5Gateway(parent=qapp)
    yield gateway

    # Teardown: stop the worker thread cleanly.
    # The gateway's QThread must be quit + waited before the QObjects are destroyed,
    # otherwise Qt prints "QThread: Destroyed while thread is still running".
    try:
        gateway.close()
    except Exception:
        pass
    # Give the event loop a chance to process the quit signal.
    try:
        qapp.processEvents()
    except Exception:
        pass


@pytest.fixture
def gateway_with_connection(mt5_gateway_with_fake: Any) -> Any:
    """An MT5Gateway that has already been initialized with FakeMT5 credentials."""
    gateway = mt5_gateway_with_fake
    fut = gateway.initialize(path=None, login=12345, password="test", server="Demo")
    fut.result(timeout=10)
    return gateway
