"""Pydantic models for the auto-updater."""

from __future__ import annotations

import functools
import re
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

_SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-(.+))?$")


@functools.total_ordering
class SemVer(BaseModel):
    """Semantic version with optional prerelease."""

    major: int = Field(ge=0)
    minor: int = Field(ge=0)
    patch: int = Field(ge=0)
    prerelease: str | None = None

    @classmethod
    def from_string(cls, s: str) -> SemVer:
        """Parse ``MAJOR.MINOR.PATCH[-prerelease]``."""
        m = _SEMVER_RE.match(s.strip().lstrip("v"))
        if not m:
            raise ValueError(f"Invalid semver string: {s!r}")
        major, minor, patch, prerelease = m.groups()
        return cls(
            major=int(major),
            minor=int(minor),
            patch=int(patch),
            prerelease=prerelease,
        )

    def to_string(self) -> str:
        base = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            return f"{base}-{self.prerelease}"
        return base

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, SemVer):
            return NotImplemented  # type: ignore[return-value]
        if (self.major, self.minor, self.patch) != (
            other.major,
            other.minor,
            other.patch,
        ):
            return (self.major, self.minor, self.patch) < (
                other.major,
                other.minor,
                other.patch,
            )
        # Release version > prerelease with same core version
        if self.prerelease is None and other.prerelease is not None:
            return False
        if self.prerelease is not None and other.prerelease is None:
            return True
        if self.prerelease is None and other.prerelease is None:
            return False
        # Both have prerelease — lexical compare
        return self.prerelease < other.prerelease  # type: ignore[operator]

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SemVer):
            return NotImplemented  # type: ignore[return-value]
        return (
            self.major == other.major
            and self.minor == other.minor
            and self.patch == other.patch
            and self.prerelease == other.prerelease
        )

    def __hash__(self) -> int:  # type: ignore[override]
        return hash((self.major, self.minor, self.patch, self.prerelease))


class UpdateInfo(BaseModel):
    """Metadata for a single release fetched from ``latest.json``."""

    version: str = Field(description="Semver string, e.g. 0.2.0")
    notes_url: str
    installer_url: str
    installer_sha256: str
    portable_zip_url: str | None = None
    portable_zip_sha256: str | None = None
    published_at: datetime
    min_supported_version: str | None = None
    is_breaking: bool = False
    release_notes: str = ""

    @field_validator("version", "min_supported_version")
    @classmethod
    def _validate_semver(cls, v: str | None) -> str | None:
        if v is None:
            return None
        SemVer.from_string(v)
        return v

    @field_validator("installer_sha256", "portable_zip_sha256")
    @classmethod
    def _validate_sha256(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if not re.fullmatch(r"[0-9a-fA-F]{64}", v):
            raise ValueError(f"Invalid SHA-256: {v!r}")
        return v.lower()

    @field_validator("published_at")
    @classmethod
    def _ensure_utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            return v.replace(tzinfo=UTC)
        return v.astimezone(UTC)


UpdateState = Literal[
    "idle",
    "checking",
    "update_available",
    "no_update",
    "downloading",
    "verifying",
    "ready_to_install",
    "installing",
    "error",
    "paused",
]


class UpdateStatus(BaseModel):
    """Current state of the updater."""

    state: UpdateState = "idle"
    current_version: str
    latest_version: str | None = None
    download_progress_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    error_message: str | None = None
    update_info: UpdateInfo | None = None
