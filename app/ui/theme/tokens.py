"""
Premium Design Tokens — Linear / Notion / TradingView inspired
Provides dark (premium charcoal) and light (warm) palettes,
spacing, typography, radius, shadows and elevation.
"""

from __future__ import annotations

from dataclasses import dataclass


# ── Spacing (8pt base, with 12/24 for generous layout) ──
@dataclass(frozen=True)
class Spacing:
    xs: int = 4
    sm: int = 8
    md: int = 12
    lg: int = 16
    xl: int = 24
    xxl: int = 32
    xxxl: int = 48


SPACING = Spacing()


# ── Radius ──
@dataclass(frozen=True)
class Radius:
    sm: int = 6
    md: int = 8
    lg: int = 12
    xl: int = 16
    pill: int = 999
    circle: int = 9999


RADIUS = Radius()


# ── Typography ──
@dataclass(frozen=True)
class FontSize:
    caption: int = 11
    body: int = 13
    subtitle: int = 15
    title: int = 20
    hero: int = 28
    kpi_value: int = 24


FONT_SIZE = FontSize()


@dataclass(frozen=True)
class FontWeight:
    regular: int = 400
    medium: int = 500
    semibold: int = 600
    bold: int = 700


FONT_WEIGHT = FontWeight()

FONT_STACK = "'Inter', 'Segoe UI Variable', 'Segoe UI', system-ui, -apple-system, sans-serif"
FONT_STACK_FA = "'Vazirmatn', 'Segoe UI', system-ui, sans-serif"
FONT_MONO = "'JetBrains Mono', 'Cascadia Code', 'Consolas', monospace"
TABULAR_NUMS = "tabular-nums"

# ── Elevation / Shadows ──
SHADOW_SM = "0 1px 2px rgba(0,0,0,0.08)"
SHADOW_MD = "0 4px 12px rgba(0,0,0,0.12)"
SHADOW_LG = "0 8px 24px rgba(0,0,0,0.16)"
SHADOW_CARD_DARK = "0 1px 3px rgba(0,0,0,0.4), 0 4px 12px rgba(0,0,0,0.3)"
SHADOW_CARD_LIGHT = "0 1px 3px rgba(0,0,0,0.06), 0 4px 12px rgba(0,0,0,0.04)"

# ── Animation ──
DURATION_FAST = 150
DURATION_NORMAL = 200
DURATION_SLOW = 300
EASING = "cubic-bezier(0.4, 0, 0.2, 1)"


# ── Palette ──
@dataclass(frozen=True)
class Palette:
    # surfaces
    bg: str
    surface: str
    card: str
    card_hover: str
    border: str
    border_hover: str
    border_strong: str
    # text
    text: str
    text_secondary: str
    text_tertiary: str
    text_inverse: str
    # accent
    accent: str
    accent_hover: str
    accent_soft: str
    accent_muted: str
    # semantic
    profit: str
    profit_soft: str
    loss: str
    loss_soft: str
    warning: str
    warning_soft: str
    info: str
    info_soft: str
    # overlay / shadow
    shadow: str
    shadow_card: str
    overlay: str
    # scrollbar
    scrollbar_thumb: str
    scrollbar_thumb_hover: str
    # focus
    focus_ring: str


DARK = Palette(
    bg="#0F1117",
    surface="#161922",
    card="#1C1F2A",
    card_hover="#212636",
    border="#252836",
    border_hover="#353A4E",
    border_strong="#2E3347",
    text="#E8EAF0",
    text_secondary="#8B92A8",
    text_tertiary="#5C6378",
    text_inverse="#0F1117",
    accent="#5B8CFF",
    accent_hover="#7BA3FF",
    accent_soft="#5B8CFF20",
    accent_muted="#5B8CFF14",
    profit="#22C55E",
    profit_soft="#22C55E18",
    loss="#EF4444",
    loss_soft="#EF444418",
    warning="#F59E0B",
    warning_soft="#F59E0B18",
    info="#38BDF8",
    info_soft="#38BDF818",
    shadow="rgba(0,0,0,0.4)",
    shadow_card="0 1px 3px rgba(0,0,0,0.4), 0 4px 12px rgba(0,0,0,0.3)",
    overlay="rgba(15,17,23,0.72)",
    scrollbar_thumb="#2E3347",
    scrollbar_thumb_hover="#3A405E",
    focus_ring="#5B8CFF66",
)

LIGHT = Palette(
    bg="#FAFBFC",
    surface="#FFFFFF",
    card="#FFFFFF",
    card_hover="#F8F9FB",
    border="#E5E8EE",
    border_hover="#D1D5DB",
    border_strong="#D1D5DB",
    text="#1A1D24",
    text_secondary="#6B7280",
    text_tertiary="#9CA3AF",
    text_inverse="#FFFFFF",
    accent="#3B6FE0",
    accent_hover="#5B8CFF",
    accent_soft="#3B6FE015",
    accent_muted="#3B6FE00C",
    profit="#16A34A",
    profit_soft="#16A34A14",
    loss="#DC2626",
    loss_soft="#DC262614",
    warning="#D97706",
    warning_soft="#D9770614",
    info="#0284C7",
    info_soft="#0284C714",
    shadow="rgba(0,0,0,0.08)",
    shadow_card="0 1px 3px rgba(0,0,0,0.06), 0 4px 12px rgba(0,0,0,0.04)",
    overlay="rgba(250,251,252,0.72)",
    scrollbar_thumb="#D1D5DB",
    scrollbar_thumb_hover="#9CA3AF",
    focus_ring="#3B6FE040",
)

PALETTES: dict[str, Palette] = {
    "dark": DARK,
    "light": LIGHT,
}


def get_palette(theme: str = "dark") -> Palette:
    """Return palette for theme name (dark/light). Falls back to dark."""
    return PALETTES.get(theme.lower(), DARK)


def is_dark(theme: str) -> bool:
    return theme.lower() == "dark"


# Backwards compatibility — some legacy code imports TOKENS / ThemeTokens
@dataclass(frozen=True)
class ThemeTokens:
    palette: Palette
    spacing: Spacing
    radius: Radius
    font_size: FontSize

    @property
    def bg(self) -> str:
        return self.palette.bg

    @property
    def surface(self) -> str:
        return self.palette.surface

    @property
    def card(self) -> str:
        return self.palette.card

    @property
    def border(self) -> str:
        return self.palette.border

    @property
    def text(self) -> str:
        return self.palette.text

    @property
    def text_secondary(self) -> str:
        return self.palette.text_secondary

    @property
    def accent(self) -> str:
        return self.palette.accent


def get_tokens(theme: str = "dark") -> ThemeTokens:
    return ThemeTokens(
        palette=get_palette(theme),
        spacing=SPACING,
        radius=RADIUS,
        font_size=FONT_SIZE,
    )


# Legacy alias
TOKENS = get_tokens("dark")
DARK_TOKENS = get_tokens("dark")
LIGHT_TOKENS = get_tokens("light")
