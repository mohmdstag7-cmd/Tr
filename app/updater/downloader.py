"""Streaming downloader with SHA-256 verification."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from pathlib import Path

import httpx
from loguru import logger

log = logger.bind(category="update") if hasattr(logger, "bind") else logger  # type: ignore[attr-defined]


class ChecksumMismatchError(RuntimeError):
    """Raised when the downloaded file's SHA-256 does not match expected."""

    def __init__(self, expected: str, actual: str, path: Path) -> None:
        super().__init__(f"Checksum mismatch for {path}: expected {expected}, got {actual}")
        self.expected = expected
        self.actual = actual
        self.path = path


class Downloader:
    """Download a file with progress and SHA-256 verification."""

    def __init__(self, timeout: float = 30.0) -> None:
        self.timeout = timeout
        self._headers = {"User-Agent": "MT5TradingWorkstation-Updater/1.0"}

    # ------------------------------------------------------------------ async
    async def download(
        self,
        url: str,
        dest_path: Path,
        expected_sha256: str,
        progress_callback: Callable[[float], None] | None = None,
    ) -> Path:
        """Stream *url* to *dest_path*, verify SHA-256, return path.

        Args:
            url: Remote file URL.
            dest_path: Local destination (parent dirs are created).
            expected_sha256: Lowercase hex digest (64 chars).
            progress_callback: Called with 0..1 float progress.
        """
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        expected_sha256 = expected_sha256.lower()

        hasher = hashlib.sha256()
        total: int | None = None
        downloaded = 0

        async with httpx.AsyncClient(timeout=self.timeout, headers=self._headers, follow_redirects=True) as client:
            async with client.stream("GET", url) as resp:
                resp.raise_for_status()
                total = int(resp.headers.get("content-length", 0)) or None
                with dest_path.open("wb") as f:
                    async for chunk in resp.aiter_bytes(chunk_size=64 * 1024):
                        if not chunk:
                            continue
                        f.write(chunk)
                        hasher.update(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total:
                            progress_callback(min(downloaded / total, 1.0))
                        elif progress_callback and not total:
                            # Indeterminate — emit 0.5 while downloading
                            progress_callback(0.5)

        actual = hasher.hexdigest()
        if actual != expected_sha256:
            try:
                dest_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise ChecksumMismatchError(expected_sha256, actual, dest_path)

        if progress_callback:
            progress_callback(1.0)
        log.info(f"Downloaded and verified {dest_path} ({downloaded} bytes)")
        return dest_path

    # ------------------------------------------------------------------- sync
    def download_sync(
        self,
        url: str,
        dest_path: Path,
        expected_sha256: str,
        progress_callback: Callable[[float], None] | None = None,
    ) -> Path:
        """Synchronous variant for QThread workers."""
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        expected_sha256 = expected_sha256.lower()
        hasher = hashlib.sha256()
        downloaded = 0
        total: int | None = None

        with httpx.Client(timeout=self.timeout, headers=self._headers, follow_redirects=True) as client:
            with client.stream("GET", url) as resp:
                resp.raise_for_status()
                total = int(resp.headers.get("content-length", 0)) or None
                with dest_path.open("wb") as f:
                    for chunk in resp.iter_bytes(chunk_size=64 * 1024):
                        if not chunk:
                            continue
                        f.write(chunk)
                        hasher.update(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total:
                            progress_callback(min(downloaded / total, 1.0))
                        elif progress_callback:
                            progress_callback(0.5)

        actual = hasher.hexdigest()
        if actual != expected_sha256:
            try:
                dest_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise ChecksumMismatchError(expected_sha256, actual, dest_path)

        if progress_callback:
            progress_callback(1.0)
        log.info(f"Downloaded and verified {dest_path} ({downloaded} bytes)")
        return dest_path
