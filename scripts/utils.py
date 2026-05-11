import os
import json
import logging
import subprocess
import re
import questionary
import undetected_chromedriver as uc
from urllib.parse import quote_plus, urlencode


EXTERNAL_APPS_PATH = os.path.join(
    os.path.dirname(__file__), "../scratch/external_applications_applied.json"
)


def init_external_apps_file() -> None:
    """Initialize the external applications JSON file with an empty dict if it doesn't exist or is invalid."""
    if os.path.exists(EXTERNAL_APPS_PATH):
        try:
            with open(EXTERNAL_APPS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return  # Valid file exists
        except (json.JSONDecodeError, Exception):
            pass
            
    # If file doesn't exist or is invalid, create/reset it
    os.makedirs(os.path.dirname(EXTERNAL_APPS_PATH), exist_ok=True)
    with open(EXTERNAL_APPS_PATH, "w", encoding="utf-8") as f:
        json.dump({}, f, indent=2)


def load_external_apps() -> dict:
    """Load and return the external applications dictionary."""
    init_external_apps_file()
    try:
        with open(EXTERNAL_APPS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.error("Failed to load external apps: %s", e)
        return {}


def save_external_app(job_id: str, job_info: dict) -> None:
    """Save an external application entry to the JSON file if it doesn't exist."""
    apps = load_external_apps()
    if job_id not in apps:
        apps[job_id] = job_info
        try:
            with open(EXTERNAL_APPS_PATH, "w", encoding="utf-8") as f:
                json.dump(apps, f, indent=2, ensure_ascii=False)
            logging.info("Saved external application: %s", job_id)
        except Exception as e:
            logging.error("Failed to save external application %s: %s", job_id, e)


def setup_logging() -> None:
    """Configure the root logger to write to a timestamped file in logs/.

    Safe to call multiple times — handlers are only added once,
    which fixes the silent no-op behaviour of logging.basicConfig()
    when called more than once in the same process.
    """
    import datetime

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_path = os.path.join(
        os.path.dirname(__file__), f"../logs/run_{timestamp}.log"
    )
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    logger = logging.getLogger()
    if not logger.handlers:
        handler = logging.FileHandler(log_path, encoding="utf-8")
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)


def load_config() -> dict:
    """Load and return the contents of configs/config.json.
    
    Includes backward compatibility for the old 'email' key.
    """
    config_path = os.path.join(
        os.path.dirname(__file__), "../configs/config.json"
    )
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    # Backward compatibility: migrate 'email' to platform-specific keys if missing
    if "email" in config:
        if "apec_email" not in config:
            config["apec_email"] = config["email"]
        if "jobteaser_email" not in config:
            config["jobteaser_email"] = config["email"]
        
    return config


def save_config(config: dict) -> None:
    """Save the config dictionary back to configs/config.json."""
    config_path = os.path.join(
        os.path.dirname(__file__), "../configs/config.json"
    )
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def check_and_prompt_apec_config() -> dict:
    """Check if APEC credentials are valid (not missing/placeholder) and prompt if needed.
    
    Returns the updated config dictionary.
    """
    config = load_config()
    placeholders = {
        "your_apec_email@example.com",
        "your_apec_password",
        "your_email@example.com",  # old placeholder
    }
    
    changed = False
    
    # Check apec_email
    val = config.get("apec_email", "").strip()
    if not val or val in placeholders:
        print("\n[Config] Missing APEC email.")
        config["apec_email"] = questionary.text("Enter APEC email:").ask().strip()
        changed = True
        
    # Check apec_password
    val = config.get("apec_password", "").strip()
    if not val or val in placeholders:
        print("\n[Config] Missing APEC password.")
        # Note: User explicitly asked for password to be echoed locally
        config["apec_password"] = questionary.text("Enter APEC password:").ask().strip()
        changed = True
        
    if changed:
        save_config(config)
        print("[Config] ✓ Credentials saved to configs/config.json\n")
        
    return config




from typing import Optional

def _get_chrome_major_version() -> Optional[int]:
    """Read the installed Chrome major version.

    On Windows, checks the registry.
    On Linux/macOS (or if registry fails), tries to run the browser with --version
    if the path is known in config.json.
    """
    # 1. Try Windows registry
    try:
        import winreg
        registry_paths = [
            (winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Google\Chrome\BLBeacon"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Google\Chrome\BLBeacon"),
        ]
        for hive, path in registry_paths:
            try:
                with winreg.OpenKey(hive, path) as key:
                    version_str, _ = winreg.QueryValueEx(key, "version")
                    major = int(version_str.split(".")[0])
                    logging.info("Detected Chrome version from registry: %s", version_str)
                    return major
            except (FileNotFoundError, OSError, ValueError):
                continue
    except ImportError:
        pass

    # 2. Try running the executable with --version
    config = load_config()
    browser_path = config.get("browser_executable_path")
    if browser_path and os.path.exists(browser_path):
        try:
            output = subprocess.check_output([browser_path, "--version"], stderr=subprocess.STDOUT).decode()
            # Expecting something like "Chromium 123.0.6312.58" or "Google Chrome 123.0.6312.58"
            match = re.search(r"(\d+)\.\d+\.\d+", output)
            if match:
                major = int(match.group(1))
                logging.info("Detected browser version from executable: %d", major)
                return major
        except (subprocess.SubprocessError, OSError, ValueError) as e:
            logging.warning("Could not detect browser version from executable: %s", e)

    logging.warning("Could not detect Chrome version — letting uc auto-detect.")
    return None


def create_driver() -> uc.Chrome:
    """Create an undetected Chrome WebDriver.

    Reads the installed Chrome version from the Windows registry and
    passes it explicitly to avoid ChromeDriver/Chrome version mismatches.
    Browser console logging is enabled so scripts can collect SEVERE errors.
    """
    options = uc.ChromeOptions()
    # Enable browser-level log collection (used to surface console errors)
    options.set_capability("goog:loggingPrefs", {"browser": "ALL"})
    version = _get_chrome_major_version()

    config = load_config()
    browser_path = config.get("browser_executable_path")
    headless = config.get("headless", False)

    kwargs = {"version_main": version, "options": options, "headless": headless}
    if browser_path and os.path.exists(browser_path):
        kwargs["browser_executable_path"] = browser_path
        logging.info("Using custom browser executable: %s", browser_path)

    driver = uc.Chrome(**kwargs)
    if not headless:
        driver.maximize_window()
    return driver



def build_jobteaser_search_url_prefix(
    *,
    keyword: str,
    sort: str = "recency",
    contracts: list[str] = None,
    work_experience_codes: list[str] = None,
    languages: list[str] = None,
    study_levels: str = None,
    remote_types: str = None,
    job_category_ids: list[int] = None,
    job_function_ids: list[int] = None,
    domain_ids: list[int] = None,
    duration: str = None,
    company_business_type: str = None,
    start_date: str = None,
) -> str:
    """Build JobTeaser list URL through page= (1-based page appended by caller).

    Uses default location and category filters provided by user.
    """
    parts: list[tuple[str, str]] = [
        ("candidacy_type", "INTERNAL"),
        ("q", keyword),
        ("sort", sort),
    ]

    position_category_uuids = [
        "a33fd4ee-ec99-4251-be78-69f0a7401961",
        "88210e98-4cc1-42bf-b4cb-bd39599abab5",
        "ddc0460c-ce0b-4d98-bc5d-d8829ff9cf11",
        "f3f9d2a0-1b7b-4cca-89b7-5b68af828c40",
        "141a2494-80c5-4bae-8865-1ee0f702f441",
        "fbab2736-0eea-4d61-899c-161eea6a2b45"
    ]
    for puuid in position_category_uuids:
        parts.append(("position_category_uuid", puuid))

    parts.append(("abroad_only", "false"))
    parts.append(("lat", "46.711046"))
    parts.append(("lng", "2.181179"))
    parts.append(("localized_location", "France"))
    parts.append(("location", "France::_Y291bnRyeTo6OnVGaW9mQWV3VEVWbzlSc056bVZmZU5jOEFyTT0="))

    for c in contracts or []:
        parts.append(("contract", c))
    for wec in work_experience_codes or []:
        parts.append(("work_experience_code", wec))
    for lang in languages or []:
        parts.append(("locale", lang))
    if study_levels:
        parts.append(("study_levels", study_levels))
    if remote_types:
        parts.append(("remote_types", remote_types))
    for cid in job_category_ids or []:
        parts.append(("job_category_ids[]", str(cid)))
    for jid in job_function_ids or []:
        parts.append(("job_function_ids[]", str(jid)))
    for did in domain_ids or []:
        parts.append(("domain_ids[]", str(did)))
    if duration:
        parts.append(("duration", duration))
    if company_business_type:
        parts.append(("company_business_type", company_business_type))
    if start_date:
        parts.append(("start_date", start_date))
    return (
        "https://www.jobteaser.com/fr/job-offers?"
        + urlencode(parts, quote_via=quote_plus)
        + "&page="
    )




def ask_timeout(default_minutes: float = None) -> int:
    """Prompt for max runtime; return seconds. Optional default from config."""
    prompt = "Enter max runtime in minutes:"
    if default_minutes is not None:
        def_str = (
            str(int(default_minutes))
            if default_minutes == int(default_minutes)
            else str(default_minutes)
        )
        raw = questionary.text(prompt, default=def_str).ask()
    else:
        raw = questionary.text(prompt).ask()
    try:
        return int(float(raw) * 60)
    except (ValueError, TypeError):
        print("Invalid input. Defaulting to 5 hours.")
        return 5 * 60 * 60




def check_and_prompt_jobteaser_config() -> dict:
    """Check if JobTeaser credentials are valid (not missing/placeholder) and prompt if needed.

    Returns the updated config dictionary.
    """
    config = load_config()
    placeholders = {
        "your_jobteaser_email@example.com",
        "your_jobteaser_password",
        "your_email@example.com",
    }

    changed = False

    # Check jobteaser_email
    val = config.get("jobteaser_email", "").strip()
    if not val or val in placeholders:
        print("\n[Config] Missing JobTeaser email.")
        config["jobteaser_email"] = questionary.text("Enter JobTeaser email:").ask().strip()
        changed = True

    # Check jobteaser_password
    val = config.get("jobteaser_password", "").strip()
    if not val or val in placeholders:
        import getpass
        print("\n[Config] Missing JobTeaser password.")
        config["jobteaser_password"] = getpass.getpass("  JobTeaser password: ").strip()
        changed = True

    if changed:
        save_config(config)
        print("[Config] ✓ Credentials saved to configs/config.json\n")

    return config
