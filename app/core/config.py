"""App-level settings (pydantic v2 BaseSettings)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Global application settings."""

    model_config = SettingsConfigDict(
        env_prefix="MT5TW_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    theme: Literal["dark", "light"] = "dark"
    language: Literal["en", "fa"] = "en"
    simple_mode: bool = True
    check_updates_on_startup: bool = True
    pause_updates_during_auto: bool = True
    update_repo: str = "mohmdstag7-cmd/Tr"
    # Supabase connection (Phase 4 will use these; added now so the health
    # check ``_check_supabase`` has a real URL to probe instead of always
    # returning "unknown" — Phase 1-3 audit M2).
    supabase_url: str | None = None
    supabase_anon_key: str | None = None
    # LLM "Ask AI" integration (Phase 13) — declared here so the masking
    # filter has the field name available early.
    llm_api_key: str | None = None
    llm_endpoint: str | None = None
    llm_model: str | None = None

    def save(self) -> None:
        """Persist these settings to disk as JSON (calls save_settings(self))."""
        save_settings(self)


def _config_path() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA")
        if base:
            return Path(base) / "MT5TradingWorkstation" / "config.json"
    return Path.home() / ".mt5tw" / "config.json"


def load_settings() -> AppSettings:
    """Load settings from disk, falling back to defaults."""
    path = _config_path()
    if not path.exists():
        return AppSettings()
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return AppSettings()
        return AppSettings(**data)
    except Exception:
        return AppSettings()


def save_settings(settings: AppSettings | dict[str, object]) -> None:
    """Persist settings to disk as JSON.

    Accepts either an :class:`AppSettings` instance or a plain ``dict``. A dict is
    filtered so only keys that are valid :class:`AppSettings` fields are persisted;
    unknown keys are dropped silently (this matches the ``extra="ignore"`` policy).
    """
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(settings, AppSettings):
        data: dict[str, object] = settings.model_dump()
    elif isinstance(settings, dict):
        valid_fields = set(AppSettings.model_fields.keys())
        data = {k: v for k, v in settings.items() if k in valid_fields}
    else:
        msg = f"save_settings: expected AppSettings or dict, got {type(settings).__name__}"
        raise TypeError(msg)

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
