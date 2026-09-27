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
        Instead we:

        1. Query the GitHub Releases API for the latest published release.
        2. Read its ``tag_name`` (e.g. ``v0.1.0``).
        3. Fetch ``releases/download/{tag_name}/latest.json`` — the canonical
           release asset that release.yml uploads alongside the installer.
        4. Parse it as ``UpdateInfo``.

        If the API returns 404 (no releases yet) we raise ``ReleaseFeedError``.
        """
        # Step 1+2: discover the latest release tag via the API.
        try:
            log.info(f"Fetching latest release info from {self.api_latest_url}")
            resp = client.get(self.api_latest_url)
            if resp.status_code == 404:
                raise ReleaseFeedError(
                    "No GitHub Release found. The first release must be created before the "
                    "in-app updater can check for updates."
                )
            if resp.status_code != 200:
                raise ReleaseFeedError(f"GitHub API returned HTTP {resp.status_code}: {resp.text[:500]}")
            api_data = resp.json()
            tag_name = api_data.get("tag_name")
            if not tag_name:
                raise ReleaseFeedError("GitHub API response missing 'tag_name'")
        except httpx.RequestError as exc:
            raise ReleaseFeedError(f"Network error while fetching releases: {exc}") from exc
        except ReleaseFeedError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ReleaseFeedError(f"Failed to query GitHub API: {exc}") from exc

        # Step 3: fetch latest.json from the discovered release tag.
        latest_json_url = f"https://github.com/{self.repo}/releases/download/{tag_name}/latest.json"
        try:
            log.info(f"Fetching latest.json from {latest_json_url}")
            resp = client.get(latest_json_url)
            if resp.status_code != 200:
                raise ReleaseFeedError(
                    f"latest.json not found on release {tag_name} (HTTP {resp.status_code}). "
                    "Ensure the release.yml workflow uploaded latest.json as a release asset."
                )
            data = resp.json()
        except httpx.RequestError as exc:
            raise ReleaseFeedError(f"Network error while fetching latest.json: {exc}") from exc
        except ReleaseFeedError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ReleaseFeedError(f"Failed to fetch latest.json: {exc}") from exc

        # Step 4: parse.
        return self._parse_update_info(data)

    # ----------------------------------------------------------------- async
    async def fetch_latest(self) -> UpdateInfo:
        """Async fetch using ``httpx.AsyncClient``.

        Same logic as :meth:`fetch_latest_sync`: first query the API for the
        latest release tag, then fetch ``latest.json`` from that tag's assets.
        """
        headers = self._headers
        try:
            async with httpx.AsyncClient(timeout=30.0, headers=headers, follow_redirects=True) as client:
                # Step 1+2: API call to find the latest release tag.
                log.info(f"Fetching latest release info from {self.api_latest_url}")
                resp = await client.get(self.api_latest_url)
                if resp.status_code == 404:
                    raise ReleaseFeedError(
                        "No GitHub Release found. The first release must be created before the "
                        "in-app updater can check for updates."
                    )
                if resp.status_code != 200:
                    raise ReleaseFeedError(f"GitHub API returned HTTP {resp.status_code}: {resp.text[:500]}")
                api_data = resp.json()
                tag_name = api_data.get("tag_name")
                if not tag_name:
                    raise ReleaseFeedError("GitHub API response missing 'tag_name'")

                # Step 3: fetch latest.json from the discovered release tag.
                latest_json_url = f"https://github.com/{self.repo}/releases/download/{tag_name}/latest.json"
                log.info(f"Fetching latest.json from {latest_json_url}")
                resp = await client.get(latest_json_url)
                if resp.status_code != 200:
                    raise ReleaseFeedError(
                        f"latest.json not found on release {tag_name} (HTTP {resp.status_code}). "
                        "Ensure the release.yml workflow uploaded latest.json as a release asset."
                    )
                data = resp.json()
                return self._parse_update_info(data)
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
