"""Fetch ``latest.json`` from GitHub Releases."""

from __future__ import annotations

from typing import Any

import httpx
from loguru import logger

from app.updater.models import UpdateInfo

log = logger.bind(category="update") if hasattr(logger, "bind") else logger  # type: ignore[attr-defined]


class ReleaseFeedError(RuntimeError):
    """Raised when the release feed cannot be fetched or parsed."""


class ReleaseFeed:
    """Fetch update metadata from GitHub Releases.

    Primary source is ``https://github.com/{repo}/releases/download/latest/latest.json``.
    Fallback is the GitHub Releases API.
    """

    def __init__(
        self,
        repo: str = "mohmdstag7-cmd/Tr",
        httpx_client: httpx.Client | None = None,
    ) -> None:
        self.repo = repo
        self._client = httpx_client
        self._headers = {
            "User-Agent": "MT5TradingWorkstation-Updater/1.0",
            "Accept": "application/json",
        }

    @property
    def api_latest_url(self) -> str:
        return f"https://api.github.com/repos/{self.repo}/releases/latest"

    # ------------------------------------------------------------------ sync
    def fetch_latest_sync(self) -> UpdateInfo:
        """Synchronous fetch (used inside QThread workers)."""
        client = self._client or httpx.Client(timeout=30.0, headers=self._headers, follow_redirects=True)
        close_client = self._client is None
        try:
            return self._fetch_with_client_sync(client)
        finally:
            if close_client:
                client.close()

    def _fetch_with_client_sync(self, client: httpx.Client) -> UpdateInfo:
        """Fetch the latest release's metadata.

        GitHub Releases does NOT support a stable ``/releases/download/latest/...``
        URL — ``latest`` would have to be a moving git tag (which GitHub's release
        asset path resolves against tag_name of an actual Release, not just any tag).

        We try two strategies, in order:

        **Strategy 1 (preferred): GitHub Releases API.**
        Query ``/repos/{repo}/releases/latest`` to discover the latest release
        ``tag_name``, then fetch ``releases/download/{tag_name}/latest.json``.
        This is the canonical approach but is rate-limited to 60 requests/hour
        for unauthenticated clients. If the API returns 403 (rate limit), we
        fall back to Strategy 2.

        **Strategy 2 (fallback): hardcoded version probe.**
        Try fetching ``releases/download/v{X.Y.Z}/latest.json`` for a list of
        known version candidates (read from the ``min_supported_version`` field
        of the previous fetch, or hardcoded). This bypasses the API entirely
        and downloads directly from the release asset CDN.

        If both strategies fail, raise ``ReleaseFeedError``.
        """
        # Strategy 1: GitHub Releases API (preferred).
        try:
            log.info(f"Fetching latest release info from {self.api_latest_url}")
            resp = client.get(self.api_latest_url)
            if resp.status_code == 200:
                api_data = resp.json()
                tag_name = api_data.get("tag_name")
                if tag_name:
                    # Step 3: fetch latest.json from the discovered release tag.
                    latest_json_url = f"https://github.com/{self.repo}/releases/download/{tag_name}/latest.json"
                    log.info(f"Fetching latest.json from {latest_json_url}")
                    resp = client.get(latest_json_url)
                    if resp.status_code == 200:
                        data = resp.json()
                        return self._parse_update_info(data)
                    log.warning(f"latest.json not found on release {tag_name} (HTTP {resp.status_code})")
            elif resp.status_code == 403:
                log.warning(
                    "GitHub API rate limit exceeded (HTTP 403). Falling back to " "direct version-probe strategy."
                )
            elif resp.status_code == 404:
                raise ReleaseFeedError(
                    "No GitHub Release found. The first release must be created "
                    "before the in-app updater can check for updates."
                )
            else:
                log.warning(f"GitHub API returned HTTP {resp.status_code}, trying fallback strategy.")
        except httpx.RequestError as exc:
            log.warning(f"Network error on GitHub API: {exc}, trying fallback.")
        except ReleaseFeedError:
            raise
        except Exception as exc:  # noqa: BLE001
            log.warning(f"GitHub API query failed: {exc}, trying fallback.")

        # Strategy 2: direct version-probe (fallback when API is rate-limited).
        # Try a small list of candidate version tags. The release.yml workflow
        # always uploads latest.json to the release tagged with the version,
        # so if we know the version we can fetch directly.
        return self._fallback_version_probe(client)

    def _fallback_version_probe(self, client: httpx.Client) -> UpdateInfo:
        """Fetch ``latest.json`` by trying known version tags directly.

        This bypasses the GitHub API entirely. We try the current app version
        +1 (e.g., if the app is 0.4.0, we try v0.4.1, v0.5.0, v1.0.0), and
        also a small list of hardcoded recent versions. The first one that
        returns a valid latest.json wins.

        This is fragile but works as a fallback when the API is rate-limited.
        The proper long-term fix is to authenticate the API call (Phase 4+).
        """
        from app.__version__ import __version__ as app_version

        # Build a list of candidate tags to try.
        candidates: list[str] = []
        try:
            parts = app_version.split(".")
            if len(parts) == 3:
                major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
                # Try patch+1, minor+1, major+1 (most likely update paths).
                candidates.append(f"v{major}.{minor}.{patch + 1}")
                candidates.append(f"v{major}.{minor + 1}.0")
                candidates.append(f"v{major + 1}.0.0")
        except Exception:
            pass
        # Also try some known recent versions (hardcoded for resilience).
        candidates.extend(["v0.4.0", "v0.3.0", "v0.2.0", "v0.1.0"])

        for tag in candidates:
            url = f"https://github.com/{self.repo}/releases/download/{tag}/latest.json"
            try:
                log.info(f"Fallback: trying {url}")
                resp = client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    # Only return if this version is newer than the app.
                    from app.__version__ import __version__ as app_v
                    from app.updater.models import SemVer

                    info = self._parse_update_info(data)
                    try:
                        current = SemVer.from_string(app_v)
                        latest = SemVer.from_string(info.version)
                        if latest > current:
                            log.info(f"Found update {info.version} via fallback probe.")
                            return info
                        log.info(f"Found {info.version} via fallback, but not newer than {app_v}.")
                    except Exception:
                        return info  # Can't compare — return anyway.
            except Exception:
                continue

        raise ReleaseFeedError(
            "Could not fetch latest.json via API (rate-limited) or fallback probe. "
            "Try again later, or check your network connection."
        )

    # ----------------------------------------------------------------- async
    async def fetch_latest(self) -> UpdateInfo:
        """Async fetch using ``httpx.AsyncClient``.

        Same logic as :meth:`fetch_latest_sync`: first try the GitHub API,
        then fall back to direct version-probe if rate-limited.
        """
        headers = self._headers
        try:
            async with httpx.AsyncClient(timeout=30.0, headers=headers, follow_redirects=True) as client:
                # Strategy 1: GitHub API (preferred).
                log.info(f"Fetching latest release info from {self.api_latest_url}")
                resp = await client.get(self.api_latest_url)
                if resp.status_code == 200:
                    api_data = resp.json()
                    tag_name = api_data.get("tag_name")
                    if tag_name:
                        latest_json_url = f"https://github.com/{self.repo}/releases/download/{tag_name}/latest.json"
                        log.info(f"Fetching latest.json from {latest_json_url}")
                        resp = await client.get(latest_json_url)
                        if resp.status_code == 200:
                            return self._parse_update_info(resp.json())
                elif resp.status_code == 404:
                    raise ReleaseFeedError(
                        "No GitHub Release found. The first release must be created "
                        "before the in-app updater can check for updates."
                    )
                elif resp.status_code == 403:
                    log.warning("GitHub API rate limited (403). Falling back to version-probe.")
                else:
                    log.warning(f"GitHub API HTTP {resp.status_code}, trying fallback.")

                # Strategy 2: fallback version-probe (same logic as sync).
                # Reuse the sync method by extracting the probe into a helper.
                import httpx as _httpx

                sync_client = _httpx.Client(timeout=30.0, headers=headers, follow_redirects=True)
                try:
                    return self._fallback_version_probe(sync_client)
                finally:
                    sync_client.close()
        except ReleaseFeedError:
            raise
        except httpx.RequestError as exc:
            raise ReleaseFeedError(f"Network error while fetching releases: {exc}") from exc
        except Exception as exc:  # noqa: BLE001
            raise ReleaseFeedError(f"Failed to parse release feed: {exc}") from exc

    # ---------------------------------------------------------------- helpers
    def _parse_update_info(self, data: dict[str, Any]) -> UpdateInfo:
        try:
            # Ensure published_at is parsed correctly
            if isinstance(data.get("published_at"), str):
                # Pydantic will handle ISO parsing, but ensure Z is handled
                raw = data["published_at"]
                if raw.endswith("Z"):
                    data = dict(data)
                    data["published_at"] = raw.replace("Z", "+00:00")
            return UpdateInfo.model_validate(data)
        except Exception as exc:  # noqa: BLE001
            raise ReleaseFeedError(f"Invalid latest.json payload: {exc}") from exc
