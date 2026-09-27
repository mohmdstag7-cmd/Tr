"""
Premium Sidebar — icon + label, 40px rows, accent left-border active state,
group labels, collapse animation, generous spacing.
"""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.ui.theme.tokens import FONT_SIZE, get_palette

# ── Navigation definition with Unicode icons ──
NAV_GROUPS: list[tuple[str, list[tuple[str, str, str]]]] = [
    (
        "MAIN",
        [
            ("dashboard", "◫", "Dashboard"),
            ("market", "◑", "Market"),
            ("signals", "✦", "Signals"),
            ("positions", "⇄", "Positions"),
            ("analytics", "▦", "Analytics"),
        ],
    ),
    (
        "TOOLS",
        [
            ("journal", "☰", "Journal"),
            ("backtest", "⌛", "Backtest"),
            ("model", "◊", "Model"),
            ("ai_lab", "♛", "AI Lab"),
            ("strategies", "♣", "Strategies"),
        ],
    ),
    (
        "SYSTEM",
        [
            ("risk", "⚠", "Risk"),
            ("logs", "📋", "Logs"),
            ("health", "♥", "Health"),
            ("settings", "⚙", "Settings"),
        ],
    ),
]

ALL_ROUTES = [r for _, items in NAV_GROUPS for r, _, _ in items]


class NavButton(QPushButton):
    """40px nav row with icon + label, active = accent soft + left border."""

    def __init__(self, route: str, icon: str, label: str, collapsed: bool = False, parent=None):
        super().__init__(parent)
        self.route = route
        self.icon_char = icon
        self.label_text = label
        self._collapsed = collapsed
        self.setCheckable(True)
        self.setObjectName("NavButton")
        self.setFixedHeight(40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._refresh_text()

    def set_collapsed(self, collapsed: bool):
        self._collapsed = collapsed
        self._refresh_text()

    def _refresh_text(self):
        if self._collapsed:
            self.setText(f"  {self.icon_char}  ")
            self.setToolTip(self.label_text)
        else:
            # icon + two spaces + label for breathing room
            self.setText(f"  {self.icon_char}    {self.label_text}")

    def sizeHint(self):
        s = super().sizeHint()
        s.setHeight(40)
        return s


class Sidebar(QFrame):
    navigationRequested = Signal(str)
    collapseToggled = Signal(bool)

    def __init__(self, parent=None, collapsed: bool = False):
        super().__init__(parent)
        self._collapsed = collapsed
        self._active_route: str = "dashboard"
        self._buttons: dict[str, NavButton] = {}
        self._group_labels: list[QLabel] = []
        self.setObjectName("SidebarFrame")
        self.setFixedWidth(56 if collapsed else 220)
        self._build_ui()
        self._apply_style()
        self.set_active("dashboard")

    # ── UI ──
    def _build_ui(self):
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(8, 12, 8, 12)
        self._layout.setSpacing(0)

        # — App logo / collapse row —
        top_row = QHBoxLayout()
        top_row.setContentsMargins(4, 0, 4, 8)
        top_row.setSpacing(8)

        self._logo_icon = QLabel("◫")
        self._logo_icon.setStyleSheet("font-size: 18px; font-weight: 700; background: transparent; border: none;")
        self._logo_label = QLabel("MT5 Workstation")
        self._logo_label.setStyleSheet("font-size: 13px; font-weight: 700; letter-spacing: -0.02em; background: transparent; border: none;")

        self._collapse_btn = QPushButton("◇" if not self._collapsed else "◫")
        self._collapse_btn.setFixedSize(32, 32)
        self._collapse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._collapse_btn.setObjectName("GhostButton")
        self._collapse_btn.setToolTip("Toggle sidebar")
        self._collapse_btn.clicked.connect(self._toggle_collapse)

        top_row.addWidget(self._logo_icon)
        top_row.addWidget(self._logo_label, 1)
        top_row.addWidget(self._collapse_btn)
        self._layout.addLayout(top_row)

        # Divider under logo
        div = QFrame()
        div.setFixedHeight(1)
        div.setObjectName("Divider")
        self._layout.addWidget(div)
        self._layout.addSpacing(12)

        # — Scrollable nav —
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")

        nav_container = QWidget()
        nav_container.setStyleSheet("background: transparent;")
        nav_layout = QVBoxLayout(nav_container)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(2)

        p = get_palette("dark")
        for group_name, items in NAV_GROUPS:
            lbl = QLabel(group_name)
            lbl.setStyleSheet(
                f"font-size: {FONT_SIZE.caption}px; font-weight: 600; "
                f"color: {p.text_tertiary}; letter-spacing: 0.08em; "
                f"background: transparent; border: none; padding: 16px 12px 6px 12px;"
            )
            self._group_labels.append(lbl)
            nav_layout.addWidget(lbl)
            for route, icon, label in items:
                btn = NavButton(route, icon, label, collapsed=self._collapsed)
                btn.clicked.connect(lambda checked, r=route: self._on_nav(r))
                self._buttons[route] = btn
                nav_layout.addWidget(btn)

        nav_layout.addStretch(1)
        scroll.setWidget(nav_container)
        self._layout.addWidget(scroll, 1)

        # — Bottom hint when collapsed —
        self._bottom_hint = QLabel("© MT5 WS")
        self._bottom_hint.setStyleSheet(f"font-size: {FONT_SIZE.caption}px; color: {p.text_tertiary}; background: transparent; border: none; padding: 8px 12px;")
        self._bottom_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._layout.addWidget(self._bottom_hint)

        self._sync_collapsed_visibility()

    def _apply_style(self):
        p = get_palette("dark")
        self.setStyleSheet(f"#SidebarFrame {{ background-color: {p.surface}; border-right: 1px solid {p.border}; border-top: none; border-bottom: none; border-left: none; }}")

    # ── Public API ──
    def set_active(self, route: str):
        if route not in self._buttons:
            return
        self._active_route = route
        for r, btn in self._buttons.items():
            btn.setChecked(r == route)

    def set_collapsed(self, collapsed: bool):
        if self._collapsed == collapsed:
            return
        self._collapsed = collapsed
        self._animate_width(56 if collapsed else 220)
        self._sync_collapsed_visibility()
        for btn in self._buttons.values():
            btn.set_collapsed(collapsed)
        self._collapse_btn.setText("◫" if collapsed else "◇")
        self.collapseToggled.emit(collapsed)

    def is_collapsed(self) -> bool:
        return self._collapsed

    # ── Internals ──
    def _sync_collapsed_visibility(self):
        show_full = not self._collapsed
        self._logo_label.setVisible(show_full)
        for lbl in self._group_labels:
            lbl.setVisible(show_full)
        self._bottom_hint.setVisible(show_full)

    def _toggle_collapse(self):
        self.set_collapsed(not self._collapsed)

    def _on_nav(self, route: str):
        self.set_active(route)
        self.navigationRequested.emit(route)

    def _animate_width(self, target: int):
        self._anim = QPropertyAnimation(self, b"minimumWidth")
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.setStartValue(self.width())
        self._anim.setEndValue(target)
        self._anim.start()
        self._anim2 = QPropertyAnimation(self, b"maximumWidth")
        self._anim2.setDuration(200)
        self._anim2.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim2.setStartValue(self.width())
        self._anim2.setEndValue(target)
        self._anim2.start()

    # Keep fixedWidth in sync after animation
    def set_theme(self, theme: str):
        p = get_palette(theme)
        self.setStyleSheet(f"#SidebarFrame {{ background-color: {p.surface}; border-right: 1px solid {p.border}; border-top: none; border-bottom: none; border-left: none; }}")
        for lbl in self._group_labels:
            lbl.setStyleSheet(
                f"font-size: {FONT_SIZE.caption}px; font-weight: 600; "
                f"color: {p.text_tertiary}; letter-spacing: 0.08em; "
                f"background: transparent; border: none; padding: 16px 12px 6px 12px;"
            )
        hint_color = p.text_tertiary
        self._bottom_hint.setStyleSheet(f"font-size: {FONT_SIZE.caption}px; color: {hint_color}; background: transparent; border: none; padding: 8px 12px;")
        logo_color = p.text
        self._logo_icon.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {logo_color}; background: transparent; border: none;")
        self._logo_label.setStyleSheet(f"font-size: 13px; font-weight: 700; letter-spacing: -0.02em; color: {logo_color}; background: transparent; border: none;")
