"""Badge widget - small pill with dot indicator."""

from __future__ import annotations

from typing import Any, Literal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QWidget

from app.ui.theme.tokens import get_tokens

BadgeKind = Literal["demo", "real", "contest", "info", "success", "warning", "error"]


def _resolve_color(tokens: Any, name: str, fallback: str) -> str:
    try:
        if hasattr(tokens, "colors"):
            colors = tokens.colors
            if hasattr(colors, name):
                return str(getattr(colors, name))
            if isinstance(colors, dict) and name in colors:
                return str(colors[name])
        if isinstance(tokens, dict) and name in tokens:
            return str(tokens[name])
        if hasattr(tokens, name):
            return str(getattr(tokens, name))
    except Exception:
        pass
    return fallback


_KIND_MAP: dict[str, tuple[str, str]] = {
    # kind -> (bg_token_name, fallback_bg)
    "demo": ("secondary", "#6c7086"),
    "real": ("warning", "#f1c40f"),
    "contest": ("accent", "#7b61ff"),
    "info": ("accent", "#7b61ff"),
    "success": ("profit", "#2ecc71"),
    "warning": ("warning", "#f1c40f"),
    "error": ("loss", "#e74c3c"),
}


class Badge(QLabel):
    """Small pill badge with dot indicator."""

    def __init__(
        self,
        kind: BadgeKind = "info",
        text: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("Badge")
        self._kind: BadgeKind = kind
        self._raw_text: str = text if text is not None else kind.capitalize()
        self._tokens: Any = None
        try:
            self._tokens = get_tokens()
        except Exception:
            self._tokens = None

        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setText(f"● {self._raw_text}")
        self.setContentsMargins(8, 2, 8, 2)
        self.reapply_tokens(self._tokens)

    @property
    def kind(self) -> BadgeKind:
        return self._kind

    @kind.setter
    def kind(self, value: BadgeKind) -> None:
        self._kind = value
        self.setText(f"● {self._raw_text}")
        self.reapply_tokens(self._tokens)

    def setText(self, text: str) -> None:  # type: ignore[override]
        # Ensure dot indicator is present
        if not text.startswith("●"):
            text = f"● {text.lstrip('● ').strip()}"
        super().setText(text)

    def reapply_tokens(self, tokens: Any | None = None) -> None:
        if tokens is not None:
            self._tokens = tokens
        if self._tokens is None:
            try:
                self._tokens = get_tokens()
            except Exception:
                self._tokens = None

        bg_token, fallback_bg = _KIND_MAP.get(self._kind, ("accent", "#7b61ff"))
        bg = _resolve_color(self._tokens, bg_token, fallback_bg)
        # Foreground: choose white or dark based on bg brightness heuristic
        # For warning (yellow) use dark text, otherwise white
        if self._kind == "real" or self._kind == "warning":
            fg = _resolve_color(self._tokens, "text_inverse", "#1a1a1e")
            if fg == "#1a1a1e" and bg.lower() in ("#f1c40f", "#f39c12"):
                fg = "#1a1a1e"
        else:
            fg = "#ffffff"

        border = _resolve_color(self._tokens, "border", "#2d2d36")

        self.setStyleSheet(
            f"""
            #Badge {{
                background-color: {bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 12px;
                padding: 2px 8px;
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 0.3px;
            }}
            """
        )

    def set_tokens(self, tokens: Any) -> None:
        self.reapply_tokens(tokens)
