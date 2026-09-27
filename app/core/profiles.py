"""Account profile config (pydantic v2)."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict


class Profile(BaseSettings):
    """Trading profile configuration."""

    name: str
    mt5_login: int | None = None
    mt5_server: str | None = None
    mt5_terminal_path: str | None = None
    mode: Literal["analysis", "paper", "semi_auto", "auto"] = "paper"
    is_real: bool = False
    risk_profile: Literal["conservative", "normal", "prop"] = "normal"

    model_config = SettingsConfigDict(extra="ignore")


def _profiles_dir() -> Path:
    return Path.home() / ".mt5tw" / "profiles"


def _profile_path(name: str) -> Path:
    safe = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in name)
    return _profiles_dir() / f"{safe}.yaml"


def load_profile(name: str) -> Profile:
    """Load a profile by name, returning a default if the file is missing."""
    path = _profile_path(name)
    if not path.exists():
        return Profile(name=name)
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        return Profile(name=name)
    # Ensure name is set from argument if not present in file
    data.setdefault("name", name)
    return Profile(**data)


def save_profile(profile: Profile) -> None:
    """Persist a profile to its yaml file."""
    path = _profile_path(profile.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = profile.model_dump()
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)


def list_profiles() -> list[str]:
    """List available profile names."""
    d = _profiles_dir()
    if not d.exists():
        return []
    names: list[str] = []
    for p in d.glob("*.yaml"):
        names.append(p.stem)
    names.sort()
    return names
