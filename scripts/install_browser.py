#!/usr/bin/env python3
"""
install_browser.py  —  Download an isolated Ungoogled Chromium build
into the project's browser/ directory.

Standalone usage (run once from the project root):
    python scripts/install_browser.py

Also importable — main.py calls install_and_get_path() directly so it
can auto-configure the browser path in configs/config.json on first run.

Supported platforms
-------------------
  macOS   — Apple Silicon (arm64) and Intel (x86_64)
  Windows — x64
  Linux   — auto-download not supported; install instructions printed.

Dependencies: Python 3.9+ stdlib only (no pip packages required).
"""

import os
import sys
import json
import platform
import re
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------

_SYSTEM = platform.system().lower()   # 'darwin' | 'windows' | 'linux'
_MACHINE = platform.machine().lower() # 'arm64' | 'amd64' | 'x86_64' | ...

if _MACHINE in ("amd64", "x86_64"):
    _ARCH = "x86_64"
elif _MACHINE in ("arm64", "aarch64"):
    _ARCH = "arm64"
else:
    _ARCH = _MACHINE

# ---------------------------------------------------------------------------
# Platform → GitHub release config
# ---------------------------------------------------------------------------

GITHUB_API = "https://api.github.com/repos/{repo}/releases/latest"

PLATFORM_CONFIG = {
    ("darwin", "arm64"): {
        "repo": "ungoogled-software/ungoogled-chromium-macos",
        "asset_patterns": [r"macos[-_]arm64.*\.dmg$", r"macos.*\.dmg$"],
        "archive_type": "dmg",
        "exe_relative": "Chromium.app/Contents/MacOS/Chromium",
    },
    ("darwin", "x86_64"): {
        "repo": "ungoogled-software/ungoogled-chromium-macos",
        "asset_patterns": [r"macos[-_]x86.64.*\.dmg$", r"macos.*\.dmg$"],
        "archive_type": "dmg",
        "exe_relative": "Chromium.app/Contents/MacOS/Chromium",
    },
    ("windows", "x86_64"): {
        "repo": "ungoogled-software/ungoogled-chromium-windows",
        "asset_patterns": [r"windows.*x64.*\.zip$", r"windows.*\.zip$"],
        "archive_type": "zip",
        "exe_relative": "chrome.exe",
    },
}

# ---------------------------------------------------------------------------
# Download / extraction helpers
# ---------------------------------------------------------------------------

def _fetch_json(url: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "autoapply-install-script/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode())


def _pick_asset(assets: list, patterns: list) -> Optional[dict]:
    """Return the first asset whose name matches any pattern (priority order)."""
    for pattern in patterns:
        for asset in assets:
            if re.search(pattern, asset["name"], re.IGNORECASE):
                return asset
    return None


def _download(url: str, dest: Path) -> None:
    def _progress(count, block_size, total_size):
        if total_size > 0:
            pct = min(count * block_size / total_size * 100, 100)
            print(f"\r  Downloading {dest.name} … {pct:.0f}%", end="", flush=True)

    urllib.request.urlretrieve(url, dest, reporthook=_progress)
    print()  # newline after progress bar


def _extract_dmg(dmg_path: Path, dest_dir: Path) -> None:
    """Mount DMG, copy Chromium.app to dest_dir, unmount."""
    mount_point = Path(tempfile.mkdtemp(prefix="chromium_mount_"))
    try:
        print("  Mounting DMG …")
        subprocess.run(
            ["hdiutil", "attach", str(dmg_path),
             "-mountpoint", str(mount_point),
             "-nobrowse", "-quiet"],
            check=True,
        )
        app_src = mount_point / "Chromium.app"
        if not app_src.exists():
            candidates = list(mount_point.glob("*.app"))
            if not candidates:
                raise FileNotFoundError("Could not find *.app inside the DMG.")
            app_src = candidates[0]

        app_dst = dest_dir / "Chromium.app"
        if app_dst.exists():
            shutil.rmtree(app_dst)
        print(f"  Copying {app_src.name} → {dest_dir} …")
        shutil.copytree(str(app_src), str(app_dst))
    finally:
        subprocess.run(
            ["hdiutil", "detach", str(mount_point), "-quiet"],
            check=False,
        )
        shutil.rmtree(mount_point, ignore_errors=True)


def _extract_zip(zip_path: Path, dest_dir: Path) -> None:
    import zipfile
    print(f"  Extracting {zip_path.name} …")
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(dest_dir)


def _linux_instructions() -> None:
    print("""
┌─────────────────────────────────────────────────────────────────┐
│  Linux — manual browser install required                        │
└─────────────────────────────────────────────────────────────────┘

Automated download is not supported on Linux due to distro fragmentation.
Choose the method that matches your system:

  Arch Linux (AUR):
    yay -S ungoogled-chromium

  Debian / Ubuntu:
    Follow https://github.com/ungoogled-software/ungoogled-chromium-debian

  Flatpak (distro-independent):
    flatpak install flathub com.github.Eloston.UngoogledChromium

  AppImage (portable — most distros):
    Download from:
    https://github.com/ungoogled-software/ungoogled-chromium-binaries/releases
    chmod +x ungoogled-chromium-*.AppImage

After installing, find the path with:
    which chromium  OR  which ungoogled-chromium

Then set "browser_executable_path" in configs/config.json to that path.
""")


# ---------------------------------------------------------------------------
# Core install logic (importable)
# ---------------------------------------------------------------------------

def install_and_get_path() -> Optional[Path]:
    """Download and install Ungoogled Chromium for the current platform.

    Returns the Path to the Chromium executable on success.
    Returns None on unsupported platform or failure.

    Safe to call multiple times — exits early if the binary is already
    present in browser/chromium/ so no re-download occurs.
    """
    project_root = Path(__file__).resolve().parent.parent
    browser_dir = project_root / "browser" / "chromium"

    key = (_SYSTEM, _ARCH)

    if _SYSTEM == "linux":
        _linux_instructions()
        return None

    if key not in PLATFORM_CONFIG:
        print(f"[Browser] Unsupported platform: {_SYSTEM}/{_ARCH}")
        print("  Supported: macOS arm64, macOS x86_64, Windows x64")
        return None

    cfg = PLATFORM_CONFIG[key]

    # --- Idempotency: return early if already installed ---
    exe = browser_dir / cfg["exe_relative"]
    if not exe.exists():
        candidates = list(browser_dir.rglob(Path(cfg["exe_relative"]).name))
        if candidates:
            exe = candidates[0]
    if exe.exists():
        print(f"[Browser] Already installed at:\n  {exe}")
        return exe

    # --- Fetch latest release metadata from GitHub ---
    api_url = GITHUB_API.format(repo=cfg["repo"])
    print(f"  Fetching latest release from github.com/{cfg['repo']} …")
    try:
        release = _fetch_json(api_url)
    except Exception as exc:
        print(f"[Browser] Could not reach GitHub API: {exc}")
        return None

    tag = release.get("tag_name", "unknown")
    assets = release.get("assets", [])
    print(f"  Latest  : {tag}  ({len(assets)} assets)")

    asset = _pick_asset(assets, cfg["asset_patterns"])
    if asset is None:
        print("[Browser] Could not match a download asset. Available:")
        for a in assets:
            print(f"    {a['name']}")
        return None

    print(f"  Asset   : {asset['name']} ({asset['size'] // 1_048_576} MB)")
    print()

    # --- Create destination directory ---
    browser_dir.mkdir(parents=True, exist_ok=True)

    # --- Download to a temp directory, then extract ---
    with tempfile.TemporaryDirectory(prefix="chromium_dl_") as tmp:
        archive_path = Path(tmp) / asset["name"]
        try:
            _download(asset["browser_download_url"], archive_path)
        except Exception as exc:
            print(f"[Browser] Download failed: {exc}")
            return None

        print()
        try:
            if cfg["archive_type"] == "dmg":
                _extract_dmg(archive_path, browser_dir)
            elif cfg["archive_type"] == "zip":
                _extract_zip(archive_path, browser_dir)
            else:
                print(f"[Browser] Unknown archive type: {cfg['archive_type']}")
                return None
        except Exception as exc:
            print(f"[Browser] Extraction failed: {exc}")
            return None

    # --- Resolve and fix executable permissions ---
    exe = browser_dir / cfg["exe_relative"]
    if not exe.exists():
        candidates = list(browser_dir.rglob(Path(cfg["exe_relative"]).name))
        if candidates:
            exe = candidates[0]

    if exe.exists() and _SYSTEM in ("darwin", "linux"):
        exe.chmod(exe.stat().st_mode | 0o111)

    return exe if exe.exists() else None


# ---------------------------------------------------------------------------
# Standalone CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    print()
    print("═" * 52)
    print("  AutoApply — Ungoogled Chromium Installer")
    print("═" * 52)
    print(f"  OS   : {platform.system()} {platform.release()} ({_SYSTEM})")
    print(f"  Arch : {_ARCH}")
    print()

    exe = install_and_get_path()

    if exe:
        print()
        print("┌─────────────────────────────────────────────┐")
        print("│  ✓  Install complete                        │")
        print("└─────────────────────────────────────────────┘")
        print(f"\n  Chromium is at:\n    {exe}\n")
        print("  Paste this into configs/config.json:")
        print(f'    "browser_executable_path": "{exe}"')
        print()
    elif _SYSTEM != "linux":
        print("\n[!] Install failed — see errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
