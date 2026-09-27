"""Tests for the auto-updater."""

from __future__ import annotations

import hashlib
from pathlib import Path

import httpx
import pytest

from app.__version__ import __version__ as current_version
from app.updater.downloader import ChecksumMismatchError, Downloader
from app.updater.models import SemVer, UpdateInfo, UpdateStatus
from app.updater.release_feed import ReleaseFeed


def test_semver_parsing() -> None:
    v1 = SemVer.from_string("0.1.0")
    assert v1.major == 0 and v1.minor == 1 and v1.patch == 0
    assert v1.prerelease is None

    v2 = SemVer.from_string("1.2.3")
    assert v2.major == 1 and v2.minor == 2 and v2.patch == 3

    v3 = SemVer.from_string("0.1.0-rc1")
    assert v3.prerelease == "rc1"

    # With leading v
    v4 = SemVer.from_string("v0.2.0")
    assert v4.major == 0 and v4.minor == 2 and v4.patch == 0

    assert v1.to_string() == "0.1.0"
    assert v3.to_string() == "0.1.0-rc1"


def test_semver_comparison() -> None:
    a = SemVer.from_string("0.1.0")
    b = SemVer.from_string("0.1.1")
    c = SemVer.from_string("0.2.0")
    d = SemVer.from_string("1.0.0")
    assert a < b < c < d
    assert not d < a
    assert a == SemVer.from_string("0.1.0")
    assert a <= b
    assert d >= c
    # Prerelease < release
    pre = SemVer.from_string("1.0.0-rc1")
    rel = SemVer.from_string("1.0.0")
    assert pre < rel
    assert rel > pre


def test_update_info_parsing() -> None:
    data = {
        "version": "0.2.0",
        "notes_url": "https://github.com/mohmdstag7-cmd/Tr/releases/tag/v0.2.0",
        "installer_url": "https://github.com/mohmdstag7-cmd/Tr/releases/download/v0.2.0/MT5TradingWorkstation-Setup-0.2.0.exe",
        "installer_sha256": "a" * 64,
        "portable_zip_url": "https://github.com/mohmdstag7-cmd/Tr/releases/download/v0.2.0/MT5TradingWorkstation-0.2.0-portable.zip",
        "portable_zip_sha256": "b" * 64,
        "published_at": "2025-01-01T00:00:00Z",
        "min_supported_version": "0.1.0",
        "is_breaking": False,
        "release_notes": "Bug fixes",
    }
    info = UpdateInfo.model_validate(data)
    assert info.version == "0.2.0"
    assert info.installer_sha256 == "a" * 64
    assert info.published_at.tzinfo is not None


def test_update_status_initial() -> None:
    s = UpdateStatus(current_version="0.1.0")
    assert s.state == "idle"
    assert s.current_version == "0.1.0"
    assert s.download_progress_pct == 0.0
    assert s.error_message is None


def test_release_feed_uses_correct_url(monkeypatch: pytest.MonkeyPatch) -> None:
    called_urls: list[str] = []

    class FakeResp:
        def __init__(self, payload: dict) -> None:
            self.status_code = 200
            self._payload = payload

        def json(self) -> dict:
            return self._payload

    # The API call returns a GitHub Releases response (with tag_name + assets).
    api_payload = {
        "tag_name": "v0.2.0",
        "assets": [
            {
                "name": "latest.json",
                "browser_download_url": ("https://github.com/mohmdstag7-cmd/Tr/releases/download/v0.2.0/latest.json"),
            },
        ],
    }
    # The latest.json asset returns the canonical update manifest.
    latest_json_payload = {
        "version": "0.2.0",
        "notes_url": "https://github.com/mohmdstag7-cmd/Tr/releases/tag/v0.2.0",
        "installer_url": ("https://github.com/mohmdstag7-cmd/Tr/releases/download/v0.2.0/" "MT5TradingWorkstation-Setup-0.2.0.exe"),
        "installer_sha256": "a" * 64,
        "published_at": "2025-01-01T00:00:00Z",
        "is_breaking": False,
        "release_notes": "notes",
    }

    def fake_get(self: httpx.Client, url: str, **kwargs) -> FakeResp:  # type: ignore[no-untyped-def]
        called_urls.append(url)
        if url.startswith("https://api.github.com/"):
            return FakeResp(api_payload)
        return FakeResp(latest_json_payload)

    monkeypatch.setattr(httpx.Client, "get", fake_get)

    feed = ReleaseFeed(repo="mohmdstag7-cmd/Tr")
    info = feed.fetch_latest_sync()
    assert info.version == "0.2.0"
    assert any("latest.json" in u for u in called_urls)
    # The first call should be the API discovery call.
    assert "raw.githubusercontent.com" in called_urls[0]


def test_downloader_checksum_mismatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Mock httpx.Client.stream to return wrong content
    content = b"wrong content"

    class FakeStreamResp:
        headers = {"content-length": str(len(content))}

        def __enter__(self) -> FakeStreamResp:
            return self

        def __exit__(self, *args: object) -> None:
            pass

        def raise_for_status(self) -> None:
            pass

        def iter_bytes(self, chunk_size: int = 65536):  # type: ignore[no-untyped-def]
            yield content

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
            pass

        def __enter__(self) -> FakeClient:
            return self

        def __exit__(self, *args: object) -> None:
            pass

        def stream(self, *args, **kwargs) -> FakeStreamResp:  # type: ignore[no-untyped-def]
            return FakeStreamResp()

    monkeypatch.setattr(httpx, "Client", FakeClient)

    dl = Downloader()
    dest = tmp_path / "installer.exe"
    expected = hashlib.sha256(b"correct content").hexdigest()
    with pytest.raises(ChecksumMismatchError):
        dl.download_sync("https://example.com/installer.exe", dest, expected)
    assert not dest.exists()


def test_downloader_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    content = b"hello world installer"
    expected = hashlib.sha256(content).hexdigest()

    class FakeStreamResp:
        headers = {"content-length": str(len(content))}

        def __enter__(self) -> FakeStreamResp:
            return self

        def __exit__(self, *args: object) -> None:
            pass

        def raise_for_status(self) -> None:
            pass

        def iter_bytes(self, chunk_size: int = 65536):  # type: ignore[no-untyped-def]
            yield content

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
            pass

        def __enter__(self) -> FakeClient:
            return self

        def __exit__(self, *args: object) -> None:
            pass

        def stream(self, *args, **kwargs) -> FakeStreamResp:  # type: ignore[no-untyped-def]
            return FakeStreamResp()

    monkeypatch.setattr(httpx, "Client", FakeClient)

    dl = Downloader()
    dest = tmp_path / "installer.exe"
    result = dl.download_sync("https://example.com/installer.exe", dest, expected)
    assert result == dest
    assert dest.read_bytes() == content


def test_update_checker_no_update(monkeypatch: pytest.MonkeyPatch, qtbot) -> None:  # type: ignore[no-untyped-def]
    from app.updater.models import UpdateInfo
    from app.updater.updater import UpdateChecker

    # Mock ReleaseFeed to return same version as current
    fake_info = UpdateInfo(
        version=current_version,
        notes_url="https://github.com/mohmdstag7-cmd/Tr/releases/tag/v0.1.0",
        installer_url="https://github.com/mohmdstag7-cmd/Tr/releases/download/v0.1.0/MT5TradingWorkstation-Setup-0.1.0.exe",
        installer_sha256="a" * 64,
        published_at="2025-01-01T00:00:00Z",
        is_breaking=False,
        release_notes="same version",
    )

    monkeypatch.setattr(
        "app.updater.update_worker.ReleaseFeed.fetch_latest_sync",
        lambda self: fake_info,
    )

    checker = UpdateChecker()
    with qtbot.waitSignal(checker.no_update, timeout=5000):
        checker.start_check()
    # Also verify status_changed emitted no_update state
    # Give thread time to finish
    qtbot.wait(500)
    checker.shutdown()
