"""i18n lookup and language switching."""

from __future__ import annotations

from app.ui.i18n.en import TRANSLATIONS as en_dict
from app.ui.i18n.fa import TRANSLATIONS as fa_dict

_translations: dict[str, dict[str, str]] = {
    "en": en_dict,
    "fa": fa_dict,
}

_current: str = "en"


def tr(key: str, default: str | None = None, **kwargs: object) -> str:
    """Translate a key using the current language, with optional formatting.

    If the key is not found and ``default`` is provided, the default is used.
    Otherwise the key itself is returned (so callers can spot missing translations).
    """
    table = _translations.get(_current, {})
    if key in table:
        template = table[key]
    elif default is not None:
        template = default
    else:
        template = key
    if kwargs:
        try:
            return template.format(**kwargs)
        except Exception:
            return template
    return template


def set_language(lang: str) -> None:
    """Set the current language. Validates against supported languages."""
    if lang not in _translations:
        msg = f"Unsupported language: {lang!r}. Supported: {sorted(_translations.keys())}"
        raise ValueError(msg)
    global _current
    _current = lang


def current_language() -> str:
    """Return the current language code."""
    return _current
