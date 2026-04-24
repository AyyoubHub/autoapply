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
    ("linux", "x86_64"): {
        "repo": "ungoogled-software/ungoogled-chromium-portablelinux",
        "asset_patterns": [r"linux.*x86_64.*\.tar\.xz$", r"x86_64.*linux.*\.tar\.xz$"],
        "archive_type": "tar.xz",
        "exe_relative": "chrome",
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


def _extract_tar_xz(tar_path: Path, dest_dir: Path) -> None:
    import tarfile
    print(f"  Extracting {tar_path.name} …")
    with tarfile.open(tar_path, "r:xz") as tf:
        tf.extractall(dest_dir)


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

    Always checks GitHub for the latest release. If the local version
    is missing or outdated, it downloads and replaces it.
    """
    project_root = Path(__file__).resolve().parent.parent
    browser_dir = project_root / "browser" / "chromium"
    version_file = browser_dir / "version.tag"

    key = (_SYSTEM, _ARCH)

    if key not in PLATFORM_CONFIG:
        if _SYSTEM == "linux":
            _linux_instructions()
        else:
            print(f"[Browser] Unsupported platform: {_SYSTEM}/{_ARCH}")
        return None

    cfg = PLATFORM_CONFIG[key]

    # --- Fetch latest release metadata from GitHub ---
    api_url = GITHUB_API.format(repo=cfg["repo"])
    print(f"  Fetching latest release info from github.com/{cfg['repo']} …")
    try:
        release = _fetch_json(api_url)
    except Exception as exc:
        print(f"[Browser] Could not reach GitHub API: {exc}")
        # If offline, try to fallback to existing installation
        exe = browser_dir / cfg["exe_relative"]
        if not exe.exists():
            candidates = list(browser_dir.rglob(Path(cfg["exe_relative"]).name))
            if candidates: exe = candidates[0]
        return exe if exe and exe.exists() else None

    latest_tag = release.get("tag_name", "unknown")
    
    # --- Check if update is needed ---
    current_tag = ""
    if version_file.exists():
        current_tag = version_file.read_text().strip()

    exe = browser_dir / cfg["exe_relative"]
    if not exe.exists():
        candidates = list(browser_dir.rglob(Path(cfg["exe_relative"]).name))
        if candidates: exe = candidates[0]

    if exe.exists() and current_tag == latest_tag:
        print(f"[Browser] Latest version already installed ({latest_tag}).")
        return exe

    if exe.exists():
        print(f"[Browser] Update available: {current_tag} -> {latest_tag}")
    else:
        print(f"[Browser] Installing version: {latest_tag}")

    assets = release.get("assets", [])
    asset = _pick_asset(assets, cfg["asset_patterns"])
    if asset is None:
        print("[Browser] Could not match a download asset.")
        return None

    print(f"  Asset   : {asset['name']} ({asset['size'] // 1_048_576} MB)")

    # --- Fresh install: clean up old files ---
    if browser_dir.exists():
        # Keep the directory but clear contents to avoid "busy" errors if we're inside it
        for item in browser_dir.iterdir():
            if item.is_dir(): shutil.rmtree(item)
            else: item.unlink()
    
    browser_dir.mkdir(parents=True, exist_ok=True)

    # --- Download and extract ---
    with tempfile.TemporaryDirectory(prefix="chromium_dl_") as tmp:
        archive_path = Path(tmp) / asset["name"]
        try:
            _download(asset["browser_download_url"], archive_path)
            if cfg["archive_type"] == "dmg": _extract_dmg(archive_path, browser_dir)
            elif cfg["archive_type"] == "zip": _extract_zip(archive_path, browser_dir)
            elif cfg["archive_type"] == "tar.xz": _extract_tar_xz(archive_path, browser_dir)
        except Exception as exc:
            print(f"[Browser] Install failed: {exc}")
            return None

    # --- Save version tag ---
    version_file.write_text(latest_tag)

    # --- Resolve executable ---
    exe = browser_dir / cfg["exe_relative"]
    if not exe.exists():
        candidates = list(browser_dir.rglob(Path(cfg["exe_relative"]).name))
        if candidates: exe = candidates[0]

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
