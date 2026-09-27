"""Design tokens for dark and light themes."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Tokens:
    """Token set for a theme."""

    bg: str
    surface: str
    card: str
    border: str
    text: str
    secondary: str
    accent: str
    profit: str
    loss: str
    warning: str
    radius_px: int = 12
    border_px: int = 1
    transition_ms: int = 180
    font_family_latin: str = "Inter, 'Segoe UI Variable', 'Segoe UI', Arial, sans-serif"
    font_family_cjk: str = "Vazirmatn, 'Segoe UI', sans-serif"


dark = Tokens(
    bg="#0B0D12",
    surface="#12151C",
    card="#171B24",
    border="#232836",
    text="#E6E8EE",
    secondary="#8A91A5",
    accent="#5B8CFF",
    profit="#22C55E",
    loss="#EF4444",
    warning="#F59E0B",
)

light = Tokens(
    bg="#FFFFFF",
    surface="#F8F9FB",
    card="#FFFFFF",
    border="#E5E8EE",
    text="#1A1D24",
    secondary="#6B7280",
    accent="#3B6FE0",
    profit="#16A34A",
    loss="#DC2626",
    warning="#D97706",
)


def get_tokens(theme: str = "dark") -> Tokens:
    """Return tokens for the given theme name."""
    if theme == "dark":
        return dark
    if theme == "light":
        return light
    msg = f"Unknown theme: {theme!r}. Expected 'dark' or 'light'."
    raise ValueError(msg)
