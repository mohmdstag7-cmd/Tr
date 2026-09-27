"""Account profiles — YAML + Windows Credential Manager via keyring."""

from __future__ import annotations

import pathlib
from typing import Any

import keyring
import yaml
from pydantic import BaseModel

from app.mt5.connection import detect_account_type


class AccountProfile(BaseModel):
    name: str
    login: int
    server: str
    terminal_path: str | None = None
    is_investor_password: bool = False
    is_real: bool = False

    def model_post_init(self, __context: Any) -> None:
        # derive is_real from login if not explicitly set
        atype = detect_account_type(self.login, self.server)
        object.__setattr__(self, "is_real", atype == "real")


class ProfileManager:
    """Persist profiles to ~/.mt5tw/profiles/<name>.yaml + keyring."""

    def __init__(self, base_dir: pathlib.Path | None = None) -> None:
        self.base_dir = base_dir or pathlib.Path.home() / ".mt5tw" / "profiles"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _yaml_path(self, name: str) -> pathlib.Path:
        return self.base_dir / f"{name}.yaml"

    def save(self, profile: AccountProfile, password: str | None = None) -> None:
        data = profile.model_dump()
        # never store password in yaml
        with open(self._yaml_path(profile.name), "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, sort_keys=False)
        if password is not None:
            keyring.set_password("mt5tw", f"account-{profile.login}", password)

    def load(self, name: str) -> tuple[AccountProfile, str | None]:
        with open(self._yaml_path(name), encoding="utf-8") as f:
            data = yaml.safe_load(f)
        profile = AccountProfile(**data)
        try:
            pwd = keyring.get_password("mt5tw", f"account-{profile.login}")
        except Exception:
            pwd = None
        return profile, pwd

    def list_profiles(self) -> list[str]:
        return [p.stem for p in self.base_dir.glob("*.yaml")]

    def delete(self, name: str) -> None:
        # need login to delete keyring entry
        try:
            profile, _ = self.load(name)
            try:
                keyring.delete_password("mt5tw", f"account-{profile.login}")
            except Exception:
                pass
        except Exception:
            pass
        try:
            self._yaml_path(name).unlink(missing_ok=True)
        except Exception:
            pass

    def set_default(self, name: str) -> None:
        (self.base_dir / "default.txt").write_text(name, encoding="utf-8")

    def get_default(self) -> str | None:
        p = self.base_dir / "default.txt"
        if p.exists():
            try:
                return p.read_text(encoding="utf-8").strip()
            except Exception:
                return None
        return None
