"""
main.py — AutoApply entry point.

First-run bootstrap (runs silently if everything is already set up):
  1. Install missing Python dependencies from requirements.txt
  2. Create configs/config.json from the example if it doesn't exist
     → prompts only for email + password (the only user-specific values)
  3. Auto-download Ungoogled Chromium into browser/chromium/ if
     browser_executable_path is missing or points to a non-existent file
     → saves the detected path back to config.json automatically

After bootstrap the platform menu is shown.
"""

import os
import sys
import json
import shutil
import subprocess
import importlib
import getpass

# Project root and scripts path — resolved before any third-party imports.
_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

# Placeholder values shipped in config.example.json that must be replaced.
_PLACEHOLDER_BROWSER_PATHS = {
    "",
    "/path/to/Chromium-or-Chrome",
    "/path/to/your/Chrome-or-Chromium",
}


# ---------------------------------------------------------------------------
# Step 1 — Python dependency check
# ---------------------------------------------------------------------------

def _ensure_dependencies() -> None:
    """Install requirements.txt packages if any are missing."""
    req_path = os.path.join(_ROOT, "requirements.txt")
    if not os.path.exists(req_path):
        return

    with open(req_path, encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]

    import re as _re
    import importlib.metadata as _metadata
    
    missing = []
    for line in lines:
        line = line.split("#")[0].strip()
        if not line:
            continue
        pkg_name = _re.split(r"[>=<!;\[]", line)[0].strip()
        try:
            _metadata.version(pkg_name)
        except _metadata.PackageNotFoundError:
            missing.append(pkg_name)

    if missing:
        print(f"\n[Setup] Installing missing packages: {', '.join(missing)} …")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-r", req_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )
        print("[Setup] ✓ Dependencies ready.\n")


# ---------------------------------------------------------------------------
# Step 2 — Config file
# ---------------------------------------------------------------------------

def _ensure_config() -> None:
    """Create configs/config.json from the example if it doesn't exist.

    Only asks for the two fields that are personal to the user:
    email and APEC password.  Everything else is either optional or
    filled in automatically (e.g. browser_executable_path in step 3).
    """
    config_path = os.path.join(_ROOT, "configs", "config.json")
    example_path = os.path.join(_ROOT, "configs", "config.example.json")

    if os.path.exists(config_path):
        return

    print("\n" + "─" * 52)
    print("  First-run setup — let's create your config.json")
    print("─" * 52)
    print("  Only your credentials are needed now.")
    print("  Everything else is configured automatically.\n")

    # Load the example and strip comment-only keys (_comment, _*_note)
    with open(example_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    config = {k: v for k, v in config.items() if not k.startswith("_")}

    # Prompt for the only user-specific values
    config["email"] = input("  APEC email    : ").strip()
    config["apec_password"] = getpass.getpass("  APEC password : ").strip()

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"\n[Setup] ✓ Config saved to configs/config.json\n")


# ---------------------------------------------------------------------------
# Step 3 — Browser auto-install
# ---------------------------------------------------------------------------

def _ensure_browser() -> None:
    """Auto-install Ungoogled Chromium and update config if not configured.

    Skips silently if browser_executable_path already points to an existing file.
    After a successful install the path is written back to config.json so no
    manual copy-paste is needed.
    """
    config_path = os.path.join(_ROOT, "configs", "config.json")

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    browser_path = config.get("browser_executable_path", "")

    # Already configured and binary exists — nothing to do
    if browser_path not in _PLACEHOLDER_BROWSER_PATHS and os.path.exists(browser_path):
        return

    if browser_path and browser_path not in _PLACEHOLDER_BROWSER_PATHS:
        print(f"\n[Setup] Browser not found at: {browser_path}")
    else:
        print("\n[Setup] No browser configured — running auto-install …")

    print("[Setup] Downloading Ungoogled Chromium for your platform …\n")

    from install_browser import install_and_get_path
    exe = install_and_get_path()

    if exe and os.path.exists(str(exe)):
        config["browser_executable_path"] = str(exe)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"\n[Setup] ✓ Browser path saved to config.json")
        print(f"  {exe}\n")
    else:
        print(
            "\n[Setup] ⚠ Could not auto-install browser.\n"
            "  Install Ungoogled Chromium manually, then set\n"
            '  "browser_executable_path" in configs/config.json.\n'
        )


# ---------------------------------------------------------------------------
# Bootstrap — runs silently on repeat invocations (everything already set up)
# ---------------------------------------------------------------------------

_ensure_dependencies()
_ensure_config()
_ensure_browser()

# ---------------------------------------------------------------------------
# Normal startup — only reached after bootstrap succeeds
# ---------------------------------------------------------------------------

import warnings
warnings.filterwarnings("ignore", message=".*urllib3 v2 only supports OpenSSL.*")
warnings.filterwarnings("ignore", message=".*You are using a Python version.*")

import questionary  # noqa: E402  (installed by _ensure_dependencies if needed)

from utils import setup_logging  # noqa: E402
setup_logging()

from apec import run as run_apec          # noqa: E402
from jobteaser import run as run_jobteaser  # noqa: E402

platforms = {
    "APEC": run_apec,
    "JobTeaser  ⚠  (experimental — not fully functional)": run_jobteaser,
}

selected_run = questionary.select(
    "Choose a job platform to launch:",
    choices=[
        questionary.Choice(title=name, value=fn)
        for name, fn in platforms.items()
    ],
).ask()

try:
    selected_run()
except KeyboardInterrupt:
    print("\n\nInterrupted by user. Exiting cleanly.")