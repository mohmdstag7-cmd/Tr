#!/usr/bin/env python3
"""
Force-update script — downloads and installs the latest MT5 Trading Workstation.

Usage (on Windows):
    python force_update.py

Or just double-click if Python is installed.
This script bypasses the in-app auto-updater entirely.
"""

import hashlib
import json
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

REPO = "mohmdstag7-cmd/Tr"
API_URL = f"https://api.github.com/repos/{REPO}/releases/latest"


def get_latest_release():
    """Fetch the latest release info from GitHub API."""
    req = urllib.request.Request(
        API_URL,
        headers={
            "User-Agent": "MT5TradingWorkstation-Updater",
            "Accept": "application/vnd.github+json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    return data


def download_file(url, dest_path, expected_sha256=None):
    """Download a file with progress indication."""
    print(f"  Downloading from: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "MT5TradingWorkstation-Updater"})

    with urllib.request.urlopen(req, timeout=300) as resp:
        total = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        chunk_size = 1024 * 1024  # 1MB

        with open(dest_path, "wb") as f:
            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if total > 0:
                    pct = downloaded * 100 // total
                    print(f"\r  {downloaded // (1024*1024)} MB / {total // (1024*1024)} MB ({pct}%)", end="", flush=True)
        print()

    if expected_sha256:
        print("  Verifying SHA-256 checksum...", end=" ", flush=True)
        h = hashlib.sha256()
        with open(dest_path, "rb") as f:
            while True:
                chunk = f.read(1024 * 1024)
                if not chunk:
                    break
                h.update(chunk)
        actual = h.hexdigest()
        if actual.lower() != expected_sha256.lower():
            print("FAILED!")
            print(f"  Expected: {expected_sha256}")
            print(f"  Actual:   {actual}")
            return False
        print("OK")
    return True


def main():
    print("=" * 60)
    print("  MT5 Trading Workstation — Force Update")
    print("=" * 60)
    print()

    # Step 1: Get latest release info
    print("[1/4] Fetching latest release info from GitHub...")
    try:
        release = get_latest_release()
    except Exception as e:
        print(f"  ERROR: Could not fetch release info: {e}")
        print("  Trying direct version probe (bypassing API)...")
        # Fallback: try known versions directly
        for version in ["v0.5.0", "v0.4.2", "v0.4.1"]:
            url = f"https://github.com/{REPO}/releases/download/{version}/latest.json"
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "MT5TradingWorkstation-Updater"})
                with urllib.request.urlopen(req, timeout=30) as resp:
                    if resp.status == 200:
                        release = {"tag_name": version, "assets": []}
                        # Fetch latest.json for download URLs
                        latest_json = json.loads(resp.read())
                        release["_latest_json"] = latest_json
                        print(f"  Found release: {version}")
                        break
            except Exception:
                continue
        else:
            print("  ERROR: Could not find any release. Check your internet connection.")
            input("Press Enter to exit...")
            return 1

    tag = release.get("tag_name", "v0.5.0")
    version = tag.lstrip("v")
    print(f"  Latest release: {tag}")

    # Get latest.json for proper URLs + checksums
    latest_json_url = f"https://github.com/{REPO}/releases/download/{tag}/latest.json"
    try:
        req = urllib.request.Request(latest_json_url, headers={"User-Agent": "MT5TradingWorkstation-Updater"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            latest_json = json.loads(resp.read())
    except Exception:
        latest_json = release.get("_latest_json", {})

    installer_url = latest_json.get("installer_url", "")
    installer_sha = latest_json.get("installer_sha256", "")
    portable_url = latest_json.get("portable_zip_url", "")
    portable_sha = latest_json.get("portable_zip_sha256", "")

    if not installer_url or not portable_url:
        # Fallback: construct URLs from assets
        for asset in release.get("assets", []):
            name = asset.get("name", "")
            url = asset.get("browser_download_url", "")
            if "Setup" in name and name.endswith(".exe"):
                installer_url = url
            elif "portable" in name and name.endswith(".zip"):
                portable_url = url

    print(f"  Installer:   {installer_url}")
    print(f"  Portable:   {portable_url}")
    print()

    # Step 2: Ask user what they want
    print("[2/4] Choose download method:")
    print("  1. Installer (recommended) — downloads ~200 MB, installs to")
    print("     %LOCALAPPDATA%\\MT5TradingWorkstation\\")
    print("  2. Portable zip — downloads ~320 MB, extract anywhere")
    print("  3. Just download installer (don't run it)")
    print()
    choice = input("Enter choice (1/2/3) [default: 1]: ").strip() or "1"
    print()

    # Step 3: Download
    temp_dir = Path(tempfile.mkdtemp(prefix="mt5tw_update_"))

    if choice in ("1", "3"):
        print(f"[3/4] Downloading installer ({version})...")
        installer_path = temp_dir / f"MT5TradingWorkstation-Setup-{version}.exe"
        if not download_file(installer_url, installer_path, installer_sha):
            print("  Download failed!")
            input("Press Enter to exit...")
            return 1

        if choice == "1":
            print("[4/4] Running installer...")
            print(f"  Path: {installer_path}")
            print("  The installer will install MT5 Trading Workstation and launch it.")
            try:
                subprocess.Popen([str(installer_path)])
                print("  Installer launched. Follow the on-screen instructions.")
            except Exception as e:
                print(f"  Could not auto-launch: {e}")
                print(f"  Please run manually: {installer_path}")
        else:
            print(f"[4/4] Installer saved to: {installer_path}")
            print("  Run it manually when ready.")

    elif choice == "2":
        print(f"[3/4] Downloading portable zip ({version})...")
        zip_path = temp_dir / f"MT5TradingWorkstation-{version}-portable.zip"
        if not download_file(portable_url, zip_path, portable_sha):
            print("  Download failed!")
            input("Press Enter to exit...")
            return 1

        print("[4/4] Extracting...")
        extract_dir = Path.home() / "MT5TradingWorkstation"
        extract_dir.mkdir(parents=True, exist_ok=True)
        print(f"  Extracting to: {extract_dir}")
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)

        exe_path = extract_dir / "MT5TradingWorkstation.exe"
        print(f"  Done! Launch: {exe_path}")
        try:
            subprocess.Popen([str(exe_path)])
            print("  App launched!")
        except Exception as e:
            print(f"  Could not auto-launch: {e}")
            print(f"  Please run manually: {exe_path}")

    print()
    print("=" * 60)
    print("  Update complete!")
    print("=" * 60)
    input("Press Enter to exit...")
    return 0


if __name__ == "__main__":
    sys.exit(main())
