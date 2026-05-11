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

def _prompt_form_data() -> dict:
    """Interactively collect all fields needed to pre-fill JobTeaser application modals."""
    import questionary
    print("\n  ── Application form details (pre-fill JobTeaser modals) ──")
    print("  These values are injected into each application form automatically.\n")

    fullname = input("  Full name            : ").strip()
    phone    = input("  Phone (+33XXXXXXXXX) : ").strip()

    gender = questionary.select(
        "  Gender:",
        choices=[
            questionary.Choice("Homme (Man)",           "Homme"),
            questionary.Choice("Femme (Woman)",         "Femme"),
            questionary.Choice("Autre / Prefer not to say", "Autre"),
        ],
    ).ask()

    linkedin = input("  LinkedIn URL (Enter to skip): ").strip()
    github   = input("  GitHub URL   (Enter to skip): ").strip()

    print("\n  ── Default cover letter ──")
    print("  This message is used when JobTeaser marks the cover letter as required.")
    print("  Keep it concise (~100 words). Press Enter to finish.")
    cover_letter = input("  > ").strip()

    data: dict = {
        "fullname":           fullname,
        "phoneNumber":        phone,          # matches the hidden form field name
        "gender":             gender,
        "coverLetterContent": cover_letter,   # matches the required textarea name
    }
    # Location (currentLocation) is extracted at runtime from each job offer page.
    if linkedin:
        data["linkedin"] = linkedin
    if github:
        data["github"] = github
    return data


def _ensure_config() -> None:
    """Create configs/config.json from the example if it doesn't exist.

    Prompts for all personal credentials (APEC + JobTeaser) and basic
    form-fill details.  Everything else is filled in automatically
    (e.g. browser_executable_path in step 3).
    """
    config_path = os.path.join(_ROOT, "configs", "config.json")
    example_path = os.path.join(_ROOT, "configs", "config.example.json")

    if os.path.exists(config_path):
        return

    print("\n" + "─" * 56)
    print("  First-run setup — let's create your config.json")
    print("─" * 56)
    print("  Fill in your credentials below.")
    print("  Everything else is configured automatically.\n")

    # Load the example and strip comment-only keys (_comment, _*_note)
    with open(example_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    config = {k: v for k, v in config.items() if not k.startswith("_")}

    # ── APEC credentials ──────────────────────────────────────────
    print("  ── APEC credentials ──")
    config["apec_email"]    = input("  APEC email    : ").strip()
    config["apec_password"] = getpass.getpass("  APEC password : ").strip()

    # ── JobTeaser credentials ─────────────────────────────────────
    print("\n  ── JobTeaser credentials ──")
    config["jobteaser_email"]    = input("  JobTeaser email    : ").strip()
    config["jobteaser_password"] = getpass.getpass("  JobTeaser password : ").strip()

    # ── All form-fill details ─────────────────────────────────────
    config["form_data"] = _prompt_form_data()

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"\n[Setup] ✓ Config saved to configs/config.json\n")


def _ensure_form_data_config() -> None:
    """If form_data is absent or missing required keys in config.json, prompt only
    for the specific missing fields and merge them in — never overwrites existing values.
    """
    config_path = os.path.join(_ROOT, "configs", "config.json")
    if not os.path.exists(config_path):
        return

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    fd = config.setdefault("form_data", {})
    required_keys = {"phoneNumber", "coverLetterContent"}
    missing = required_keys - set(fd.keys())

    if not missing:
        return

    print("\n[Setup] Some application form fields are missing from your config.")

    if "phoneNumber" in missing:
        fd["phoneNumber"] = input("  Phone (+33XXXXXXXXX): ").strip()

    if "coverLetterContent" in missing:
        print("  Default cover letter (used when JobTeaser marks it required).")
        print("  Press Enter to leave blank.")
        fd["coverLetterContent"] = input("  > ").strip()

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    print("[Setup] ✓ form_data saved.\n")


# ---------------------------------------------------------------------------
# Step 3 — Browser auto-install
# ---------------------------------------------------------------------------

def _ensure_browser() -> None:
    """Auto-install/update Ungoogled Chromium and update config.

    Always checks for the latest version from GitHub. After a successful 
    install or update, the path is written back to config.json.
    """
    config_path = os.path.join(_ROOT, "configs", "config.json")

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    print("\n[Setup] Checking for browser updates …")

    from install_browser import install_and_get_path
    exe = install_and_get_path()

    if exe and os.path.exists(str(exe)):
        config["browser_executable_path"] = str(exe)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"[Setup] ✓ Browser ready: {exe}\n")
    else:
        # Fallback to whatever was there if install failed
        current = config.get("browser_executable_path")
        if current and os.path.exists(current):
            print(f"[Setup] ⚠ Auto-install failed; using existing: {current}\n")
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

import questionary  # noqa: E402
import sys          # noqa: E402

# Patch questionary so Ctrl+C (which returns None) immediately exits the script cleanly
# instead of returning None and causing type/logic errors downstream.
_original_ask = questionary.Question.ask

def _patched_ask(self, *args, **kwargs):
    res = _original_ask(self, *args, **kwargs)
    if res is None:
        print("\n\nInterrupted by user. Exiting cleanly.")
        sys.exit(1)
    return res

questionary.Question.ask = _patched_ask

try:
    _ensure_config()
    _ensure_form_data_config()
    _ensure_browser()

    from utils import init_external_apps_file
    init_external_apps_file()

    # ---------------------------------------------------------------------------
    # Normal startup — only reached after bootstrap succeeds
    # ---------------------------------------------------------------------------

    import warnings
    warnings.filterwarnings("ignore", message=".*urllib3 v2 only supports OpenSSL.*")
    warnings.filterwarnings("ignore", message=".*You are using a Python version.*")

    from utils import setup_logging  # noqa: E402
    setup_logging()

    from apec import run as run_apec          # noqa: E402
    from jobteaser import run as run_jobteaser  # noqa: E402

    platforms = {
        "APEC": run_apec,
        "JobTeaser": run_jobteaser,
    }

    selected_run = questionary.select(
        "Choose a job platform to launch:",
        choices=[
            questionary.Choice(title=name, value=fn)
            for name, fn in platforms.items()
        ],
    ).ask()

    if selected_run is None:
        print("\nNo platform selected. Exiting.")
    else:
        selected_run()

except KeyboardInterrupt:
    print("\n\nInterrupted by user. Exiting cleanly.")