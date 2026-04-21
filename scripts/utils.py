import os
import json
import logging
import questionary
import undetected_chromedriver as uc
from urllib.parse import quote_plus, urlencode


EXTERNAL_APPS_PATH = os.path.join(
    os.path.dirname(__file__), "../scratch/external_applications.json"
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


def load_jobteaser_search_config() -> dict:
    """Load JobTeaser search profile from configs/jobteaser.search.json.

    Copy jobteaser.search.example.json to jobteaser.search.json and edit.
    See docs/jobteaser_search_config.md.
    """
    path = os.path.join(
        os.path.dirname(__file__), "../configs/jobteaser.search.json"
    )
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"Missing {path}. Copy configs/jobteaser.search.example.json "
            "to configs/jobteaser.search.json and adjust filters."
        )
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


from typing import Optional

def _get_chrome_major_version() -> Optional[int]:
    """Read the installed Chrome major version from the Windows registry.

    Checks both HKEY_CURRENT_USER and HKEY_LOCAL_MACHINE so it works
    regardless of whether Chrome was installed per-user or system-wide.
    Returns None on non-Windows platforms or if the key is not found.
    """
    try:
        import winreg  # Windows-only stdlib module
    except ImportError:
        return None  # Non-Windows platform — let uc auto-detect

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
                logging.info("Detected Chrome version: %s (major: %d)", version_str, major)
                return major
        except (FileNotFoundError, OSError, ValueError):
            continue

    logging.warning("Could not detect Chrome version from registry — letting uc auto-detect.")
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
    
    kwargs = {"version_main": version, "options": options}
    if browser_path and os.path.exists(browser_path):
        kwargs["browser_executable_path"] = browser_path
        logging.info("Using custom browser executable: %s", browser_path)
        
    driver = uc.Chrome(**kwargs)
    driver.maximize_window()
    return driver



def build_jobteaser_search_url_prefix(
    *,
    keyword: str,
    sort: str = "recency",
    contracts: list[str] = None,
    work_experience_code: str = None,
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

    Always includes candidacy_type=INTERNAL (easy apply only). See docs/jobteaser_url_analysis.md.
    """
    parts: list[tuple[str, str]] = [
        ("candidacy_type", "INTERNAL"),
        ("q", keyword),
        ("sort", sort),
    ]
    for c in contracts or []:
        parts.append(("contract", c))
    if work_experience_code:
        parts.append(("work_experience_code", work_experience_code))
    for lang in languages or []:
        parts.append(("languages[]", lang))
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


def build_jobteaser_search_url_from_profile(profile: dict, keyword: str) -> str:
    """Apply a loaded jobteaser.search.json object plus keyword to the URL builder."""

    def _str_or_none(key: str) -> str:
        v = profile.get(key)
        if v is None or v == "":
            return None
        return str(v)

    def _int_list(key: str) -> list[int]:
        raw = profile.get(key)
        if not raw:
            return None
        if isinstance(raw, list):
            return [int(x) for x in raw]
        return None

    wc = _str_or_none("work_experience_code")
    sl = _str_or_none("study_levels")
    rt = _str_or_none("remote_types")
    sd = _str_or_none("start_date")
    dur = _str_or_none("duration")
    cbt = _str_or_none("company_business_type")

    contracts = profile.get("contracts")
    if isinstance(contracts, list):
        clist = [str(c) for c in contracts]
    else:
        clist = []

    langs = profile.get("languages")
    if isinstance(langs, list):
        lang_list = [str(x) for x in langs]
    else:
        lang_list = []

    sort = str(profile.get("sort") or "recency")
    if sort not in ("recency", "relevance"):
        sort = "recency"

    return build_jobteaser_search_url_prefix(
        keyword=keyword,
        sort=sort,
        contracts=clist or None,
        work_experience_code=wc,
        languages=lang_list or None,
        study_levels=sl,
        remote_types=rt,
        job_category_ids=_int_list("job_category_ids"),
        job_function_ids=_int_list("job_function_ids"),
        domain_ids=_int_list("domain_ids"),
        duration=dur,
        company_business_type=cbt,
        start_date=sd,
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


def load_applied_jobs(platform: str = "apec") -> set:
    """Load the set of URLs we have already successfully applied to."""
    path = os.path.join(os.path.dirname(__file__), f"../scratch/{platform}_applied.json")
    if not os.path.exists(path):
        return set()
    try:
        with open(path, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()


def save_applied_job(url: str, platform: str = "apec") -> None:
    """Add a URL to the local applied history file."""
    path = os.path.join(os.path.dirname(__file__), f"../scratch/{platform}_applied.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    applied = load_applied_jobs(platform)
    applied.add(url)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(list(applied), f, indent=2)
    except Exception as e:
        logging.error("Failed to save applied job to history: %s", e)
