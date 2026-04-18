import os
import json
import logging
import questionary
import undetected_chromedriver as uc


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
    """Load and return the contents of configs/config.json."""
    config_path = os.path.join(
        os.path.dirname(__file__), "../configs/config.json"
    )
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _get_chrome_major_version() -> int | None:
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
    driver = uc.Chrome(version_main=version, options=options)
    driver.maximize_window()
    return driver



def ask_timeout() -> int:
    """Prompt the user for a max runtime and return the value in seconds."""
    raw = questionary.text("Enter max runtime in minutes:").ask()
    try:
        return int(float(raw) * 60)
    except (ValueError, TypeError):
        print("Invalid input. Defaulting to 5 hours.")
        return 5 * 60 * 60
