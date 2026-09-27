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
    def latest_json_url(self) -> str:
        return f"https://github.com/{self.repo}/releases/download/latest/latest.json"

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
        # Try static latest.json first
        try:
            log.info(f"Fetching latest.json from {self.latest_json_url}")
            resp = client.get(self.latest_json_url)
            if resp.status_code == 200:
                data = resp.json()
                return self._parse_update_info(data)
            log.info(f"latest.json returned {resp.status_code}, trying API fallback")
        except Exception as exc:  # noqa: BLE001
            log.warning(f"Failed to fetch latest.json: {exc}, trying API fallback")

        # Fallback: GitHub API
        try:
            log.info(f"Fetching GitHub API {self.api_latest_url}")
            resp = client.get(self.api_latest_url)
            if resp.status_code != 200:
                raise ReleaseFeedError(f"GitHub API returned HTTP {resp.status_code}: {resp.text[:500]}")
            api_data = resp.json()
            return self._parse_api_response(api_data)
        except httpx.RequestError as exc:
            raise ReleaseFeedError(f"Network error while fetching releases: {exc}") from exc
        except ReleaseFeedError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ReleaseFeedError(f"Failed to parse release feed: {exc}") from exc

    # ----------------------------------------------------------------- async
    async def fetch_latest(self) -> UpdateInfo:
        """Async fetch using ``httpx.AsyncClient``."""
        headers = self._headers
        try:
            async with httpx.AsyncClient(timeout=30.0, headers=headers, follow_redirects=True) as client:
                # Try static latest.json
                try:
                    log.info(f"Fetching latest.json from {self.latest_json_url}")
                    resp = await client.get(self.latest_json_url)
                    if resp.status_code == 200:
                        data = resp.json()
                        return self._parse_update_info(data)
                    log.info(f"latest.json returned {resp.status_code}, trying API fallback")
                except Exception as exc:  # noqa: BLE001
                    log.warning(f"Failed to fetch latest.json: {exc}, trying API fallback")

                # Fallback API
                resp = await client.get(self.api_latest_url)
                if resp.status_code != 200:
                    raise ReleaseFeedError(f"GitHub API returned HTTP {resp.status_code}: {resp.text[:500]}")
                api_data = resp.json()
                return self._parse_api_response(api_data)
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

    def _parse_api_response(self, data: dict[str, Any]) -> UpdateInfo:
        """Construct UpdateInfo from GitHub Releases API response."""
        try:
            tag = data.get("tag_name", "")
            tag.lstrip("v")
            assets: list[dict[str, Any]] = data.get("assets", [])
            installer_url = ""

            for asset in assets:
                name: str = asset.get("name", "")
                url: str = asset.get("browser_download_url", "")
                lname = name.lower()
                if "setup" in lname and lname.endswith(".exe"):
                    installer_url = url
                elif "portable" in lname and lname.endswith(".zip"):
                    pass
                elif name == "latest.json":
                    # If API response somehow includes latest.json, prefer it
                    pass

            # Try to fetch checksums.txt to extract sha256 if not in API
            # For now, require installer_url; sha256 may be empty -> error
            if not installer_url:
                # Fallback: first exe asset
                for asset in assets:
                    if asset.get("name", "").endswith(".exe"):
                        installer_url = asset["browser_download_url"]
                        break

            if not installer_url:
                raise ReleaseFeedError("No installer asset found in GitHub release")

            # If checksums not available, we cannot verify — raise
            # Attempt to keep installer_sha256 empty as error case
            # The caller will fail verification; we raise here for clarity
            # Try to find sha from asset metadata or leave placeholder
            # We set a dummy that will fail verification if not provided
            # Instead, try to parse body for sha? For Phase 1, require latest.json
            raise ReleaseFeedError(
                "GitHub API fallback requires latest.json asset; "
                "direct API parsing without checksums is not supported. "
                "Please ensure latest.json is attached to the release."
            )
        except ReleaseFeedError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ReleaseFeedError(f"Failed to parse GitHub API response: {exc}") from exc
