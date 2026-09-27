"""Fetch ``latest.json`` from GitHub Releases — rate-limit-free via versions.json."""

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

    Three strategies, in order:
    1. versions.json index (raw.githubusercontent.com — NO rate limit)
    2. GitHub Releases API (rate-limited to 60 req/hour unauthenticated)
    3. Direct version-probe (tries known version tags directly)
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
    def versions_json_url(self) -> str:
        return f"https://raw.githubusercontent.com/{self.repo}/main/versions.json"

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
        """Fetch using three strategies, best-first."""

        # Strategy 1: versions.json index (no rate limit!)
        try:
            log.info(f"Fetching versions.json from {self.versions_json_url}")
            resp = client.get(self.versions_json_url)
            if resp.status_code == 200:
                versions_data = resp.json()
                latest_tag = versions_data.get("latest_tag", "")
                if latest_tag:
                    latest_json_url = f"https://github.com/{self.repo}/releases/download/{latest_tag}/latest.json"
                    log.info(f"Fetching latest.json from {latest_json_url}")
                    resp = client.get(latest_json_url)
                    if resp.status_code == 200:
                        return self._parse_update_info(resp.json())
                    log.warning(f"latest.json returned HTTP {resp.status_code} for {latest_tag}")
            log.warning(f"versions.json returned HTTP {resp.status_code}, trying API")
        except Exception as exc:  # noqa: BLE001
            log.warning(f"versions.json fetch failed: {exc}, trying API")

        # Strategy 2: GitHub Releases API (rate-limited)
        try:
            log.info(f"Fetching latest release from API: {self.api_latest_url}")
            resp = client.get(self.api_latest_url)
            if resp.status_code == 200:
                api_data = resp.json()
                tag_name = api_data.get("tag_name", "")
                if tag_name:
                    latest_json_url = f"https://github.com/{self.repo}/releases/download/{tag_name}/latest.json"
                    log.info(f"Fetching latest.json from {latest_json_url}")
                    resp = client.get(latest_json_url)
                    if resp.status_code == 200:
                        return self._parse_update_info(resp.json())
            elif resp.status_code == 403:
                log.warning("GitHub API rate-limited (403), trying version probe")
            elif resp.status_code == 404:
                raise ReleaseFeedError("No GitHub Release found.")
            else:
                log.warning(f"GitHub API HTTP {resp.status_code}, trying version probe")
        except ReleaseFeedError:
            raise
        except Exception as exc:  # noqa: BLE001
            log.warning(f"GitHub API failed: {exc}, trying version probe")

        # Strategy 3: direct version-probe
        return self._fallback_version_probe(client)

    def _fallback_version_probe(self, client: httpx.Client) -> UpdateInfo:
        """Try known version tags directly."""
        from app.__version__ import __version__ as app_version

        candidates: list[str] = []
        try:
            parts = app_version.split(".")
            if len(parts) == 3:
                major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
                candidates.append(f"v{major}.{minor}.{patch + 1}")
                candidates.append(f"v{major}.{minor + 1}.0")
                candidates.append(f"v{major + 1}.0.0")
        except Exception:
            pass
        candidates.extend(
            [
                "v0.5.0",
                "v0.4.2",
                "v0.4.1",
                "v0.4.0",
                "v0.3.0",
                "v0.2.0",
                "v0.1.0",
            ]
        )

        for tag in candidates:
            url = f"https://github.com/{self.repo}/releases/download/{tag}/latest.json"
            try:
                log.info(f"Fallback: trying {url}")
                resp = client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
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
                        return info
            except Exception:
                continue

        raise ReleaseFeedError("Could not fetch latest.json via any strategy. " "Check your network connection or try again later.")

    # ----------------------------------------------------------------- async
    async def fetch_latest(self) -> UpdateInfo:
        """Async fetch using ``httpx.AsyncClient``."""
        headers = self._headers
        try:
            async with httpx.AsyncClient(timeout=30.0, headers=headers, follow_redirects=True) as client:
                # Strategy 1: versions.json
                log.info(f"Fetching versions.json from {self.versions_json_url}")
                resp = await client.get(self.versions_json_url)
                if resp.status_code == 200:
                    versions_data = resp.json()
                    latest_tag = versions_data.get("latest_tag", "")
                    if latest_tag:
                        latest_json_url = f"https://github.com/{self.repo}/releases/download/{latest_tag}/latest.json"
                        resp = await client.get(latest_json_url)
                        if resp.status_code == 200:
                            return self._parse_update_info(resp.json())

                # Strategy 2: API
                log.info(f"Fetching latest release from API: {self.api_latest_url}")
                resp = await client.get(self.api_latest_url)
                if resp.status_code == 200:
                    api_data = resp.json()
                    tag_name = api_data.get("tag_name", "")
                    if tag_name:
                        latest_json_url = f"https://github.com/{self.repo}/releases/download/{tag_name}/latest.json"
                        resp = await client.get(latest_json_url)
                        if resp.status_code == 200:
                            return self._parse_update_info(resp.json())

                # Strategy 3: version probe (sync fallback)
                sync_client = httpx.Client(timeout=30.0, headers=headers, follow_redirects=True)
                try:
                    return self._fallback_version_probe(sync_client)
                finally:
                    sync_client.close()
        except ReleaseFeedError:
            raise
        except httpx.RequestError as exc:
            raise ReleaseFeedError(f"Network error: {exc}") from exc
        except Exception as exc:  # noqa: BLE001
            raise ReleaseFeedError(f"Failed to parse release feed: {exc}") from exc

    # ---------------------------------------------------------------- helpers
    def _parse_update_info(self, data: dict[str, Any]) -> UpdateInfo:
        try:
            if isinstance(data.get("published_at"), str):
                raw = data["published_at"]
                if raw.endswith("Z"):
                    data = dict(data)
                    data["published_at"] = raw.replace("Z", "+00:00")
            return UpdateInfo.model_validate(data)
        except Exception as exc:  # noqa: BLE001
            raise ReleaseFeedError(f"Invalid latest.json payload: {exc}") from exc
