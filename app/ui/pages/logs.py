"""Logs page with live tail and filters."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

try:
    from PySide6.QtWidgets import QDrawer  # type: ignore[attr-defined]
except ImportError:
    QDrawer = None  # type: ignore[assignment]

from app.observability.categories import LOG_CATEGORIES
from app.observability.logger import enable_debug_mode, get_log_dir, get_logger, set_level


class LogsPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("LogsPage")
        self._current_category = "all"
        self._level_filter: set[str] = set()
        self._symbol_filter = ""
        self._strategy_filter = ""
        self._time_range = "all"
        self._regex_filter = ""

        from app.ui.i18n import tr

        outer = QVBoxLayout(self)
        _title = QLabel(tr("logs.title", default="Logs"), self)
        _title.setObjectName("PageTitle")
        _title.setStyleSheet("font-size: 20px; font-weight: 700;")
        outer.addWidget(_title)

        layout = QHBoxLayout()
        outer.addLayout(layout, 1)

        # Left panel: category tabs
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("Categories"))
        self.category_list = QListWidget()
        self.category_list.addItem("all")
        for cat in LOG_CATEGORIES:
            self.category_list.addItem(cat)
        self.category_list.setCurrentRow(0)
        self.category_list.currentTextChanged.connect(self._on_category_changed)
        left_layout.addWidget(self.category_list)
        left.setMaximumWidth(180)

        # Center: live tail
        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.addWidget(QLabel("Live Tail (last 200 lines)"))
        self.tail_edit = QPlainTextEdit()
        self.tail_edit.setReadOnly(True)
        self.tail_edit.setMaximumBlockCount(500)
        center_layout.addWidget(self.tail_edit)

        # Bottom toolbar
        toolbar = QHBoxLayout()
        self.level_combo = QComboBox()
        self.level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.level_combo.setCurrentText("INFO")
        toolbar.addWidget(QLabel("Change level:"))
        toolbar.addWidget(self.level_combo)
        self.btn_change_level = QPushButton("Apply Level")
        self.btn_change_level.clicked.connect(self._on_change_level)
        toolbar.addWidget(self.btn_change_level)

        self.btn_debug = QPushButton("Debug mode (30 min)")
        self.btn_debug.clicked.connect(self._on_debug_mode)
        toolbar.addWidget(self.btn_debug)

        self.btn_export = QPushButton("Export current view")
        self.btn_export.clicked.connect(self._on_export)
        toolbar.addWidget(self.btn_export)

        self.btn_open_folder = QPushButton("Open logs folder")
        self.btn_open_folder.clicked.connect(self._on_open_folder)
        toolbar.addWidget(self.btn_open_folder)

        self.status_label = QLabel("Logging: unknown")
        toolbar.addWidget(self.status_label)
        toolbar.addStretch()
        center_layout.addLayout(toolbar)

        # Right panel: filters
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(QLabel("Filters"))
        self.level_filter_combo = QComboBox()
        self.level_filter_combo.addItems(["ALL", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.level_filter_combo.currentTextChanged.connect(self._on_filter_changed)
        right_layout.addWidget(QLabel("Level"))
        right_layout.addWidget(self.level_filter_combo)

        self.symbol_edit = QLineEdit()
        self.symbol_edit.setPlaceholderText("symbol filter")
        self.symbol_edit.textChanged.connect(self._on_filter_changed)
        right_layout.addWidget(QLabel("Symbol"))
        right_layout.addWidget(self.symbol_edit)

        self.strategy_edit = QLineEdit()
        self.strategy_edit.setPlaceholderText("strategy filter")
        self.strategy_edit.textChanged.connect(self._on_filter_changed)
        right_layout.addWidget(QLabel("Strategy"))
        right_layout.addWidget(self.strategy_edit)

        self.time_combo = QComboBox()
        self.time_combo.addItems(["all", "last hour", "last day", "last week"])
        self.time_combo.currentTextChanged.connect(self._on_filter_changed)
        right_layout.addWidget(QLabel("Time range"))
        right_layout.addWidget(self.time_combo)

        self.regex_edit = QLineEdit()
        self.regex_edit.setPlaceholderText("regex search")
        self.regex_edit.textChanged.connect(self._on_filter_changed)
        right_layout.addWidget(QLabel("Regex"))
        right_layout.addWidget(self.regex_edit)

        right_layout.addStretch()
        right.setMaximumWidth(220)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(center)
        splitter.addWidget(right)
        splitter.setSizes([180, 600, 220])
        layout.addWidget(splitter)

        # Timer for live tail
        self._timer = QTimer(self)
        self._timer.setInterval(500)
        self._timer.timeout.connect(self._refresh_tail)
        self._timer.start()

        # Click handler for drawer
        self.tail_edit.cursorPositionChanged.connect(self._on_cursor_changed)

        self._refresh_tail()

    def _on_category_changed(self, text: str) -> None:
        self._current_category = text
        self._refresh_tail()

    def _on_filter_changed(self, *_: Any) -> None:
        lvl = self.level_filter_combo.currentText()
        self._level_filter = set() if lvl == "ALL" else {lvl}
        self._symbol_filter = self.symbol_edit.text().strip()
        self._strategy_filter = self.strategy_edit.text().strip()
        self._time_range = self.time_combo.currentText()
        self._regex_filter = self.regex_edit.text().strip()
        self._refresh_tail()

    def _on_change_level(self) -> None:
        level = self.level_combo.currentText()
        cat = self._current_category if self._current_category != "all" else "app"
        try:
            set_level(cat, level)
            get_logger("ui").info(f"Changed level for {cat} to {level}")
            QMessageBox.information(self, "Level changed", f"{cat} -> {level}")
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def _on_debug_mode(self) -> None:
        try:
            enable_debug_mode(30)
            QMessageBox.information(self, "Debug mode", "Debug mode enabled for 30 minutes")
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def _on_export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export logs", "exported_logs.txt", "Text Files (*.txt);;All Files (*)"
        )
        if not path:
            return
        try:
            content = self.tail_edit.toPlainText()
            Path(path).write_text(content, encoding="utf-8")
            QMessageBox.information(self, "Exported", f"Exported to {path}")
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def _on_open_folder(self) -> None:
        try:
            log_dir = get_log_dir()
        except Exception:
            log_dir = Path("logs")
        try:
            if sys.platform == "win32":
                subprocess.Popen(["explorer", str(log_dir)])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(log_dir)])
            else:
                subprocess.Popen(["xdg-open", str(log_dir)])
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def _refresh_tail(self) -> None:
        try:
            log_dir = get_log_dir()
        except Exception:
            log_dir = Path("logs")
        lines: list[str] = []
        try:
            if self._current_category == "all":
                p = log_dir / "all.log"
                if p.exists():
                    lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()[-200:]
            else:
                cat_dir = log_dir / self._current_category
                if cat_dir.exists():
                    # Find latest date file
                    files = sorted(cat_dir.glob("*.jsonl"))
                    if files:
                        # Read last 200 lines from most recent file
                        latest = files[-1]
                        lines = latest.read_text(encoding="utf-8", errors="ignore").splitlines()[-200:]
        except Exception:
            lines = []

        # Apply filters
        filtered = self._apply_filters(lines)
        self.tail_edit.setPlainText("\n".join(filtered))

        # Status indicator: healthy if last log within 60s
        healthy = False
        try:
            if lines:
                # Try parse time from last line
                last = lines[-1]
                # For all.log, time is first field
                # For jsonl, parse json
                if last.strip().startswith("{"):
                    try:
                        obj = json.loads(last)
                        t_str = obj.get("time", "")
                        dt = datetime.fromisoformat(t_str.replace("Z", "+00:00"))
                        healthy = (datetime.now(UTC) - dt).total_seconds() < 60
                    except Exception:
                        healthy = True
                else:
                    healthy = True
            self.status_label.setText("Logging: healthy" if healthy else "Logging: stale")
            self.status_label.setStyleSheet("color: green;" if healthy else "color: orange;")
        except Exception:
            pass

    def _apply_filters(self, lines: list[str]) -> list[str]:
        out: list[str] = []
        # Time range cutoff
        cutoff: datetime | None = None
        now = datetime.now(UTC)
        if self._time_range == "last hour":
            cutoff = now - timedelta(hours=1)
        elif self._time_range == "last day":
            cutoff = now - timedelta(days=1)
        elif self._time_range == "last week":
            cutoff = now - timedelta(days=7)

        regex: re.Pattern[str] | None = None
        if self._regex_filter:
            try:
                regex = re.compile(self._regex_filter)
            except re.error:
                regex = None

        for line in lines:
            # Level filter
            if self._level_filter:
                # Check if level in line
                if not any(lvl in line for lvl in self._level_filter):
                    # For jsonl, check json level field
                    try:
                        obj = json.loads(line)
                        if obj.get("level") not in self._level_filter:
                            continue
                    except Exception:
                        continue
            # Symbol filter
            if self._symbol_filter and self._symbol_filter.lower() not in line.lower():
                continue
            if self._strategy_filter and self._strategy_filter.lower() not in line.lower():
                continue
            if regex and not regex.search(line):
                continue
            if cutoff:
                try:
                    if line.strip().startswith("{"):
                        obj = json.loads(line)
                        t_str = obj.get("time", "")
                        dt = datetime.fromisoformat(t_str.replace("Z", "+00:00"))
                        if dt < cutoff:
                            continue
                    else:
                        # Parse time from all.log: 2025-09-27T11:11:35.123Z
                        t_str = line.split("|")[0].strip()
                        dt = datetime.fromisoformat(t_str.replace("Z", "+00:00"))
                        if dt < cutoff:
                            continue
                except Exception:
                    pass
            out.append(line)
        return out

    def _on_cursor_changed(self) -> None:
        # Show drawer with full JSON when line clicked
        cursor = self.tail_edit.textCursor()
        cursor.select(QTextCursor.SelectionType.LineUnderCursor)
        line = cursor.selectedText().strip()
        if not line:
            return
        if line.startswith("{"):
            try:
                obj = json.loads(line)
                QMessageBox.information(self, "Log entry", json.dumps(obj, indent=2, ensure_ascii=False))
                # Show in tooltip or message box for now
                # Use a simple dialog
                # Avoid spamming: only show on click, not cursor move
                pass
            except Exception:
                pass
