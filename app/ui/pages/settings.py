"""Settings page with Updates section and updater integration."""

from __future__ import annotations

# Type-only imports to avoid circular imports at module load time.
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app import __version__
from app.core.config import AppSettings
from app.ui.i18n import tr
from app.ui.widgets.update_banner import UpdateBanner
from app.updater.models import UpdateInfo

if TYPE_CHECKING:
    from app.ui.dialogs.update_dialog import UpdateDialog
    from app.updater.updater import UpdateChecker


class SettingsPage(QWidget):
    """Application settings page."""

    # Emitted when the user changes the theme via this page. The MainWindow
    # listens and re-applies the QSS.
    theme_changed = Signal(str)
    # Emitted when the user toggles Simple Mode. The MainWindow listens and
    # switches the central stack.
    simple_mode_changed = Signal(bool)
    # Emitted when the user changes the language. The MainWindow listens and
    # re-translates the visible UI.
    language_changed = Signal(str)

    def __init__(self, parent=None) -> None:  # type: ignore[no-untyped-def]
        super().__init__(parent)
        self.setObjectName("SettingsPage")
        self._settings = AppSettings()
        self._update_checker: UpdateChecker | None = None  # type: ignore[assignment]
        self._update_dialog: UpdateDialog | None = None  # type: ignore[assignment]

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # ---- Updates section (top) ----
        updates_group = QGroupBox(tr("settings.updates.title", default="Updates"), self)
        updates_layout = QVBoxLayout(updates_group)

        self._version_label = QLabel(f"Current version: v{__version__}", self)
        self._version_label.setObjectName("VersionLabel")
        updates_layout.addWidget(self._version_label)

        self._banner = UpdateBanner(self)
        updates_layout.addWidget(self._banner)
        self._banner.update_requested.connect(self._on_update_requested)
        self._banner.dismissed.connect(lambda: None)

        self._check_updates_btn = QPushButton(tr("settings.updates.check_now", default="Check for updates now"), self)
        self._check_updates_btn.setObjectName("CheckUpdatesButton")
        self._check_updates_btn.clicked.connect(self._on_check_updates_clicked)
        updates_layout.addWidget(self._check_updates_btn)

        self._check_on_startup_cb = QCheckBox(
            tr("settings.updates.check_on_startup", default="Check for updates on startup"),
            self,
        )
        self._check_on_startup_cb.setChecked(self._settings.check_updates_on_startup)
        self._check_on_startup_cb.toggled.connect(self._on_check_on_startup_toggled)
        updates_layout.addWidget(self._check_on_startup_cb)

        self._pause_during_auto_cb = QCheckBox(
            tr(
                "settings.updates.pause_during_auto",
                default="Pause updates during Auto mode",
            ),
            self,
        )
        self._pause_during_auto_cb.setChecked(self._settings.pause_updates_during_auto)
        self._pause_during_auto_cb.toggled.connect(self._on_pause_during_auto_toggled)
        updates_layout.addWidget(self._pause_during_auto_cb)

        self._update_status_label = QLabel("", self)
        self._update_status_label.setObjectName("UpdateStatusLabel")
        self._update_status_label.setWordWrap(True)
        updates_layout.addWidget(self._update_status_label)

        layout.addWidget(updates_group)

        # ---- Appearance ----
        appearance_group = QGroupBox(tr("settings.appearance.title", default="Appearance"), self)
        appearance_form = QFormLayout(appearance_group)

        self._theme_combo = QComboBox(self)
        self._theme_combo.addItems(["Light", "Dark", "System"])
        # Try to restore theme from settings if available
        current_theme = getattr(self._settings, "theme", "System")
        idx = self._theme_combo.findText(str(current_theme), Qt.MatchFlag.MatchFixedString)
        if idx >= 0:
            self._theme_combo.setCurrentIndex(idx)
        self._theme_combo.currentTextChanged.connect(self._on_theme_changed)
        appearance_form.addRow(tr("settings.appearance.theme", default="Theme"), self._theme_combo)

        layout.addWidget(appearance_group)

        # ---- Language ----
        lang_group = QGroupBox(tr("settings.language.title", default="Language"), self)
        lang_form = QFormLayout(lang_group)
        self._lang_combo = QComboBox(self)
        self._lang_combo.addItems(["English", "中文", "日本語"])
        current_lang = getattr(self._settings, "language", "English")
        idx = self._lang_combo.findText(str(current_lang), Qt.MatchFlag.MatchFixedString)
        if idx >= 0:
            self._lang_combo.setCurrentIndex(idx)
        self._lang_combo.currentTextChanged.connect(self._on_language_changed)
        lang_form.addRow(tr("settings.language.label", default="Language"), self._lang_combo)
        layout.addWidget(lang_group)

        # ---- General ----
        general_group = QGroupBox(tr("settings.general.title", default="General"), self)
        general_layout = QVBoxLayout(general_group)

        self._simple_mode_cb = QCheckBox(tr("settings.general.simple_mode", default="Simple mode"), self)
        self._simple_mode_cb.setChecked(bool(getattr(self._settings, "simple_mode", False)))
        self._simple_mode_cb.toggled.connect(self._on_simple_mode_toggled)
        general_layout.addWidget(self._simple_mode_cb)

        layout.addWidget(general_group)

        # ---- Logging section (Phase 2) ----
        from app.observability.categories import LOG_CATEGORIES
        from app.observability.logger import get_log_dir, set_level

        logging_group = QGroupBox(tr("settings.logging.title", default="Logging"), self)
        logging_layout = QVBoxLayout(logging_group)

        # Log dir row
        dir_row = QHBoxLayout()
        dir_row.addWidget(QLabel(tr("settings.logging.dir", default="Log directory:")))
        self._log_dir_label = QLabel(str(get_log_dir()), self)
        self._log_dir_label.setObjectName("LogDirLabel")
        dir_row.addWidget(self._log_dir_label, 1)
        self._open_logs_btn = QPushButton(tr("settings.logging.open_folder", default="Open folder"), self)
        self._open_logs_btn.clicked.connect(self._on_open_logs_folder)
        dir_row.addWidget(self._open_logs_btn)
        logging_layout.addLayout(dir_row)

        # Debug mode toggle
        self._debug_mode_btn = QPushButton(
            tr("settings.logging.debug_mode", default="Enable debug mode (30 min)"), self
        )
        self._debug_mode_btn.clicked.connect(self._on_enable_debug_mode)
        logging_layout.addWidget(self._debug_mode_btn)

        # Per-category level dropdowns
        levels_form = QFormLayout()
        self._level_combos: dict[str, QComboBox] = {}
        for cat in LOG_CATEGORIES:
            combo = QComboBox(self)
            combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
            combo.setCurrentText("INFO")
            combo.currentTextChanged.connect(lambda lvl, c=cat: set_level(c, lvl))
            levels_form.addRow(f"{cat}", combo)
            self._level_combos[cat] = combo
        logging_layout.addLayout(levels_form)

        # Create debug bundle button
        self._debug_bundle_btn = QPushButton(tr("settings.logging.create_bundle", default="Create debug bundle"), self)
        self._debug_bundle_btn.clicked.connect(self._on_create_debug_bundle)
        logging_layout.addWidget(self._debug_bundle_btn)

        layout.addWidget(logging_group)

        layout.addStretch(1)

    # ------------------------------------------------------------------ slots
    @Slot(bool)
    def _on_check_on_startup_toggled(self, checked: bool) -> None:
        self._settings.check_updates_on_startup = checked
        try:
            # Persist if AppSettings supports save
            if hasattr(self._settings, "save"):
                self._settings.save()  # type: ignore[attr-defined]
        except Exception:
            pass

    @Slot(bool)
    def _on_pause_during_auto_toggled(self, checked: bool) -> None:
        self._settings.pause_updates_during_auto = checked
        try:
            if hasattr(self._settings, "save"):
                self._settings.save()  # type: ignore[attr-defined]
        except Exception:
            pass

    @Slot(str)
    def _on_theme_changed(self, theme: str) -> None:
        if hasattr(self._settings, "theme"):
            self._settings.theme = theme  # type: ignore[assignment,attr-defined]
            try:
                if hasattr(self._settings, "save"):
                    self._settings.save()  # type: ignore[attr-defined]
            except Exception:
                pass
        # Notify the MainWindow to re-apply QSS.
        self.theme_changed.emit(theme.lower())

    @Slot(str)
    def _on_language_changed(self, lang: str) -> None:
        if hasattr(self._settings, "language"):
            self._settings.language = lang  # type: ignore[assignment,attr-defined]
            try:
                if hasattr(self._settings, "save"):
                    self._settings.save()  # type: ignore[attr-defined]
            except Exception:
                pass
        self.language_changed.emit(lang.lower())

    @Slot(bool)
    def _on_simple_mode_toggled(self, checked: bool) -> None:
        if hasattr(self._settings, "simple_mode"):
            self._settings.simple_mode = checked  # type: ignore[attr-defined]
            try:
                if hasattr(self._settings, "save"):
                    self._settings.save()  # type: ignore[attr-defined]
            except Exception:
                pass
        self.simple_mode_changed.emit(checked)

    def set_theme(self, theme: str) -> None:
        """Programmatically set the theme combo (called by MainWindow on toggle)."""
        for i in range(self._theme_combo.count()):
            if self._theme_combo.itemText(i).lower() == theme.lower():
                self._theme_combo.setCurrentIndex(i)
                return

    def set_language(self, lang: str) -> None:
        """Programmatically set the language combo (called by MainWindow on toggle)."""
        for i in range(self._lang_combo.count()):
            if self._lang_combo.itemText(i).lower() == lang.lower():
                self._lang_combo.setCurrentIndex(i)
                return

    @Slot()
    def _on_check_updates_clicked(self) -> None:
        self._update_status_label.setText(tr("settings.updates.checking", default="Checking for updates..."))
        self._check_updates_btn.setEnabled(False)
        self._ensure_update_checker()
        if self._update_checker is None:  # type: ignore[truthy-bool]
            return  # Updater init failed; logged elsewhere.
        self._update_checker.start_check()

    def _ensure_update_checker(self) -> None:
        if self._update_checker is not None:
            return
        from app.updater.updater import UpdateChecker

        self._update_checker = UpdateChecker(self, settings=self._settings)
        self._update_checker.update_available.connect(self._on_update_available)
        self._update_checker.no_update.connect(self._on_no_update)
        self._update_checker.error.connect(self._on_update_error)
        self._update_checker.status_changed.connect(self._on_status_changed)

    @Slot(object)
    def _on_update_available(self, info: UpdateInfo) -> None:
        self._banner.set_update_info(info)
        self._update_status_label.setText(tr("settings.updates.available", default=f"Update v{info.version} available"))
        self._check_updates_btn.setEnabled(True)

    @Slot()
    def _on_no_update(self) -> None:
        self._update_status_label.setText(tr("settings.updates.no_update", default="You are on the latest version."))
        self._check_updates_btn.setEnabled(True)

    @Slot(str)
    def _on_update_error(self, msg: str) -> None:
        self._update_status_label.setText(msg)
        self._check_updates_btn.setEnabled(True)

    @Slot(object)
    def _on_status_changed(self, status: object) -> None:
        # Enable button again if not checking/downloading
        from app.updater.models import UpdateStatus

        if isinstance(status, UpdateStatus):
            if status.state not in ("checking", "downloading", "verifying"):
                self._check_updates_btn.setEnabled(True)

    @Slot(object)
    def _on_update_requested(self, info: UpdateInfo) -> None:
        # Open UpdateDialog and start download
        from PySide6.QtCore import QThread

        from app.ui.dialogs.update_dialog import UpdateDialog
        from app.updater.update_worker import UpdateWorker

        self._ensure_update_checker()
        if self._update_checker is None:  # type: ignore[truthy-bool]
            return  # Updater init failed; logged elsewhere.

        # Create a dedicated worker/thread for download so dialog can show progress
        thread = QThread(self)
        worker = UpdateWorker(repo=self._settings.update_repo)
        worker.moveToThread(thread)

        dialog = UpdateDialog(info, worker=worker, parent=self)
        self._update_dialog = dialog

        # Wire install request to checker
        def _do_install(path: object) -> None:
            from pathlib import Path as _Path

            p = _Path(str(path)) if not isinstance(path, _Path) else path
            # Use worker to install
            worker.install_and_relaunch(p)

        dialog.install_requested.connect(_do_install)

        # Start download when dialog is shown
        thread.started.connect(lambda: worker.download_and_verify(info))
        thread.start()

        dialog.exec()
        # Cleanup thread after dialog closes
        try:
            thread.quit()
            thread.wait(2000)
        except RuntimeError:
            pass

    # ----------------------------------------------------------- logging slots
    @Slot()
    def _on_open_logs_folder(self) -> None:
        """Open the log directory in the OS file explorer."""
        import subprocess
        import sys

        from app.observability.logger import get_log_dir

        log_dir = get_log_dir()
        try:
            if sys.platform == "win32":
                # pylint: disable=consider-using-with
                subprocess.Popen(["explorer", str(log_dir)])  # noqa: S603,S607
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(log_dir)])  # noqa: S603,S607
            else:
                subprocess.Popen(["xdg-open", str(log_dir)])  # noqa: S603,S607
        except Exception:
            # Fallback: show the path in a message box
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.information(self, "Log directory", str(log_dir))

    @Slot()
    def _on_enable_debug_mode(self) -> None:
        """Enable debug mode for 30 minutes (auto-reverts)."""
        from app.observability.logger import enable_debug_mode

        enable_debug_mode(30)
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.information(
            self,
            tr("settings.logging.debug_mode_title", default="Debug mode"),
            tr(
                "settings.logging.debug_mode_msg",
                default="Debug mode enabled for 30 minutes. All categories now log at DEBUG level.",
            ),
        )

    @Slot()
    def _on_create_debug_bundle(self) -> None:
        """Create a debug bundle zip and show the path."""
        from app.observability.debug_bundle import create_debug_bundle

        try:
            path = create_debug_bundle()
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.information(
                self,
                tr("settings.logging.bundle_created", default="Debug bundle created"),
                tr(
                    "settings.logging.bundle_path",
                    default="Debug bundle saved to:\n{path}",
                    path=str(path),
                ),
            )
        except Exception as exc:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.critical(
                self,
                tr("settings.logging.bundle_failed", default="Failed to create debug bundle"),
                str(exc),
            )
