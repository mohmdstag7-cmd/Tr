"""Settings page — Phase 1 stub with basic form."""

from __future__ import annotations

from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import (
    QButtonGroup,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from app.core.config import save_settings
from app.ui.i18n import tr
from app.ui.theme.tokens import get_tokens
from app.ui.widgets import Toggle


class SettingsPage(QWidget):
    """Settings page with theme, language, and mode controls."""

    settings_saved = Signal(dict)
    theme_changed = Signal(str)
    language_changed = Signal(str)
    simple_mode_changed = Signal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("SettingsPage")
        tokens = get_tokens("dark")
        try:
            pad = int(getattr(getattr(tokens, "spacing", None), "md", 16))  # type: ignore[arg-type]
        except Exception:
            pad = 16

        root = QVBoxLayout(self)
        root.setContentsMargins(pad, pad, pad, pad)
        root.setSpacing(pad)

        title = QLabel(tr("settings.title", default="Settings"), self)
        title.setObjectName("PageTitle")
        title.setStyleSheet("font-size: 20px; font-weight: 700;")
        root.addWidget(title)

        form = QFormLayout()
        form.setSpacing(pad)

        # Theme radio group
        self.theme_group = QButtonGroup(self)
        theme_box = QGroupBox(tr("settings.theme", default="Theme"), self)
        theme_layout = QHBoxLayout(theme_box)
        self.radio_dark = QRadioButton(tr("settings.theme_dark", default="Dark"), theme_box)
        self.radio_light = QRadioButton(tr("settings.theme_light", default="Light"), theme_box)
        self.radio_dark.setChecked(True)
        self.theme_group.addButton(self.radio_dark, 0)
        self.theme_group.addButton(self.radio_light, 1)
        theme_layout.addWidget(self.radio_dark)
        theme_layout.addWidget(self.radio_light)
        form.addRow(theme_box)

        # Language radio group
        self.lang_group = QButtonGroup(self)
        lang_box = QGroupBox(tr("settings.language", default="Language"), self)
        lang_layout = QHBoxLayout(lang_box)
        self.radio_en = QRadioButton("EN", lang_box)
        self.radio_fa = QRadioButton("FA", lang_box)
        self.radio_en.setChecked(True)
        self.lang_group.addButton(self.radio_en, 0)
        self.lang_group.addButton(self.radio_fa, 1)
        lang_layout.addWidget(self.radio_en)
        lang_layout.addWidget(self.radio_fa)
        form.addRow(lang_box)

        # Simple mode toggle
        self.toggle_simple = Toggle(parent=self)  # type: ignore[call-arg]
        # Toggle API may use setChecked / set_checked
        try:
            self.toggle_simple.setChecked(False)  # type: ignore[attr-defined]
        except Exception:
            try:
                self.toggle_simple.set_checked(False)  # type: ignore[attr-defined]
            except Exception:
                pass
        simple_row = QHBoxLayout()
        simple_row.addWidget(QLabel(tr("settings.simple_mode", default="Simple Mode"), self))
        simple_row.addStretch(1)
        simple_row.addWidget(self.toggle_simple)
        simple_container = QWidget(self)
        simple_container.setLayout(simple_row)
        form.addRow(simple_container)

        # Check updates on startup toggle
        self.toggle_updates = Toggle(parent=self)  # type: ignore[call-arg]
        try:
            self.toggle_updates.setChecked(True)  # type: ignore[attr-defined]
        except Exception:
            try:
                self.toggle_updates.set_checked(True)  # type: ignore[attr-defined]
            except Exception:
                pass
        updates_row = QHBoxLayout()
        updates_row.addWidget(QLabel(tr("settings.check_updates", default="Check updates on startup"), self))
        updates_row.addStretch(1)
        updates_row.addWidget(self.toggle_updates)
        updates_container = QWidget(self)
        updates_container.setLayout(updates_row)
        form.addRow(updates_container)

        root.addLayout(form)

        self.btn_save = QPushButton(tr("common.save", default="Save"), self)
        self.btn_save.setObjectName("PrimaryButton")
        self.btn_save.clicked.connect(self._on_save)
        root.addWidget(self.btn_save)
        root.addStretch(1)

    @Slot()
    def _on_save(self) -> None:
        """Persist settings to JSON via app.core.config.save_settings."""
        theme = "light" if self.radio_light.isChecked() else "dark"
        language = "fa" if self.radio_fa.isChecked() else "en"

        # Read toggle states with fallback
        simple_mode = False
        try:
            simple_mode = bool(self.toggle_simple.isChecked())  # type: ignore[attr-defined]
        except Exception:
            try:
                simple_mode = bool(self.toggle_simple.is_checked())  # type: ignore[attr-defined]
            except Exception:
                simple_mode = False

        check_updates = True
        try:
            check_updates = bool(self.toggle_updates.isChecked())  # type: ignore[attr-defined]
        except Exception:
            try:
                check_updates = bool(self.toggle_updates.is_checked())  # type: ignore[attr-defined]
            except Exception:
                check_updates = True

        payload: dict[str, object] = {
            "theme": theme,
            "language": language,
            "simple_mode": simple_mode,
            "check_updates_on_startup": check_updates,
        }
        save_settings(payload)  # type: ignore[arg-type]
        self.settings_saved.emit(payload)
        self.theme_changed.emit(theme)
        self.language_changed.emit(language)
        self.simple_mode_changed.emit(simple_mode)

    def set_theme(self, theme: str) -> None:
        """Set theme radio selection."""
        if theme == "light":
            self.radio_light.setChecked(True)
        else:
            self.radio_dark.setChecked(True)

    def set_language(self, lang: str) -> None:
        """Set language radio selection."""
        if lang == "fa":
            self.radio_fa.setChecked(True)
        else:
            self.radio_en.setChecked(True)
