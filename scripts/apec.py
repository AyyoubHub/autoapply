from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    InvalidSessionIdException,
    WebDriverException,
)
import time
import re
import urllib.parse
import logging
import questionary

from utils import load_config, create_driver


def run() -> None:
    # --- Configuration & user input ---
    config = load_config()
    EMAIL = config["email"]
    PASSWORD = config["apec_password"]

    KEYWORD_RAW = questionary.text(
        "Enter job keywords (space or comma separated, at least one must appear in each job):"
    ).ask()
    if not KEYWORD_RAW or not KEYWORD_RAW.strip():
        print("No keywords entered. Exiting.")
        return
    # Split on commas, spaces, or semicolons — deduplicate, preserve order
    keywords = list(
        dict.fromkeys(
            k.lower()
            for k in re.split(r"[,;\s]+", KEYWORD_RAW.strip())
            if k.strip()
        )
    )
    print(
        f"  → Keywords ({len(keywords)}) : {', '.join(keywords)}\n"
        f"  → Each keyword searched separately; jobs ranked by overlap count."
    )

    # --- Discovery time-range filter ---
    # These are APEC's internal codes verified from the live search UI.
    date_range_choices = [
        questionary.Choice(title="Last 24 hours (Dernières 24h)",   value="101850"),
        questionary.Choice(title="Last 7 days  (7 derniers jours)",  value="101851"),
        questionary.Choice(title="Last 30 days (30 derniers jours)", value="101852"),
        questionary.Choice(title="All time     (no date filter)",     value=None),
    ]
    DISCOVERY_FILTER = questionary.select(
        "Discover jobs posted in:",
        choices=date_range_choices,
    ).ask()
    # APEC URL parameter — omit entirely for 'All time' so the server applies no filter
    date_filter_param = f"&anciennetePublication={DISCOVERY_FILTER}" if DISCOVERY_FILTER else ""

    # Page cap strategy:
    # - Time-bounded modes (24h / 7d / 30d): scan ALL pages to exhaustion — the
    #   server-side filter guarantees freshness so every result is relevant.
    # - All time: use a configurable hard cap (default 3) to avoid crawling thousands
    #   of pages for broad keywords like 'devops'.
    MAX_PAGES_PER_KW: int = (
        float("inf") if DISCOVERY_FILTER
        else config.get("apec_max_pages_per_keyword", 3)
    )

    contract_choices = {
        "CDI": "101888",
        "CDD": "101889",
        "Alternance": "101891",
        "Intérim": "101890",
    }
    CONTRACT_TYPE = questionary.select(
        "Select contract type:",
        choices=[
            questionary.Choice(title=label, value=code)
            for label, code in contract_choices.items()
        ],
    ).ask()

    sorting_choices = {"Date": "DATE", "Score": "SCORE"}
    SORT_BY = questionary.select(
        "Sort jobs by:",
        choices=[
            questionary.Choice(title=label, value=code)
            for label, code in sorting_choices.items()
        ],
    ).ask()


    # --- URLs ---
    LOGIN_URL = "https://www.apec.fr/"

    # --- Driver ---
    driver = create_driver()
    wait = WebDriverWait(driver, 10)

    applied_count = 0
    processed_count = 0
    processed_count = 0
    try:
        # --- Login ---
        try:
            driver.get(LOGIN_URL)

            # APEC uses the Didomi consent management platform.
            # The accept button has a stable ID: "didomi-notice-agree-button".
            cookies_button = wait.until(
                EC.element_to_be_clickable((By.ID, "didomi-notice-agree-button"))
            )
            cookies_button.click()
            time.sleep(1)  # Let the dialog close before interacting with the page

            # Open the login popup
            login_popup_button = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//a[@onclick='showloginPopin()']")
                )
            )
            login_popup_button.click()

            email_input = wait.until(EC.presence_of_element_located((By.NAME, "emailid")))
            email_input.clear()
            email_input.send_keys(EMAIL)

            password_input = wait.until(EC.presence_of_element_located((By.NAME, "password")))
            password_input.clear()
            password_input.send_keys(PASSWORD)

            login_button = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(text(), 'Se connecter')]")
                )
            )
            login_button.click()

            # --- 1. Check for inline credential error messages ---
            # Wait briefly for the form to validate and show any error text.
            time.sleep(2)
            error_els = driver.find_elements(
                By.XPATH,
                "//*[self::span or self::p or self::div or self::li]"
                "["
                "contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'incorrect') or "
                "contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'invalide') or "
                "contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'failed') or "
                "contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'erreur')"
                "]",
            )
            visible_errors = [
                el for el in error_els if el.is_displayed() and el.text.strip()
            ]
            if visible_errors:
                error_text = visible_errors[0].text.strip()
                raise Exception(
                    f"APEC login form error: '{error_text}'. "
                    "Check email/password in configs/config.json."
                )

            # --- 2. Log browser console errors ---
            try:
                for entry in driver.get_log("browser"):
                    level = entry.get("level", "")
                    msg = entry.get("message", "")
                    if level == "SEVERE":
                        logging.error("Browser console SEVERE: %s", msg)
                    elif level == "WARNING":
                        logging.warning("Browser console WARNING: %s", msg)
            except Exception:
                pass  # Console log collection unavailable in this driver setup

            # --- 3. Verify login via protected-page redirect ---
            # Navigate to a protected user page. APEC redirects unauthenticated
            # users back to a URL containing "connexion". If we land on mon-espace,
            # the login was accepted; if we're redirected, credentials were rejected.
            time.sleep(1)
            driver.get("https://www.apec.fr/candidat/mon-espace.html")
            time.sleep(2)

            if "connexion" in driver.current_url.lower() or "login" in driver.current_url.lower():
                raise Exception(
                    f"Login rejected by APEC (redirected to: {driver.current_url}). "
                    "Check email/password in configs/config.json."
                )

            logging.info("APEC Session started — login verified.")
            print("APEC login successful.")

        except Exception:
            logging.exception("APEC login failed.")
            print("APEC login failed.")
            return  # Stop here — do not proceed with a dead browser session

        # ================================================================
        # Phase 1 — Discovery: search APEC once per keyword, score by hits
        # ================================================================
        # A job URL that appears in multiple keyword searches is more relevant.
        # We score each href by the count of keywords that returned it, then
        # apply jobs in descending score order (best matches first).

        session_alive = True
        href_scores: dict = {}  # href -> number of keyword searches that returned it

        for kw_idx, kw in enumerate(keywords):
            if not session_alive:
                break

            encoded_kw = urllib.parse.quote_plus(kw)
            kw_search_url = (
                "https://www.apec.fr/candidat/recherche-emploi.html/emploi?"
                "typesConvention=143684&typesConvention=143685"
                "&typesConvention=143686&typesConvention=143687"
                f"&motsCles={encoded_kw}"
                f"&typesContrat={CONTRACT_TYPE}"
                f"&sortsType={SORT_BY}"
                f"{date_filter_param}"
                "&page="
            )

            label = f"(up to {MAX_PAGES_PER_KW} pages)" if MAX_PAGES_PER_KW != float("inf") else "(all pages — date-filtered)"
            print(
                f"\n[{kw_idx + 1}/{len(keywords)}] Scanning APEC for '{kw}' {label}...",
                flush=True,
            )
            logging.info("APEC: Discovery — keyword '%s' (%d/%d).", kw, kw_idx + 1, len(keywords))

            page = 0
            while page < MAX_PAGES_PER_KW:  # float('inf') = no cap for date-filtered modes
                if not session_alive:
                    break
                try:
                    driver.get(f"{kw_search_url}{page}")
                    hrefs = _collect_job_links(driver, wait)
                except (InvalidSessionIdException, WebDriverException):
                    logging.error("APEC: browser session lost during discovery for '%s'.", kw)
                    session_alive = False
                    break
                except Exception:
                    break  # No more pages for this keyword

                if not hrefs:
                    break  # Natural end of results

                new_count = sum(1 for h in hrefs if h not in href_scores)
                for href in hrefs:
                    href_scores[href] = href_scores.get(href, 0) + 1

                page_label = str(page + 1) if MAX_PAGES_PER_KW == float("inf") else f"{page + 1}/{int(MAX_PAGES_PER_KW)}"
                print(
                    f"  Page {page_label}: {len(hrefs)} jobs "
                    f"({new_count} new · {len(href_scores)} unique total)",
                    flush=True,
                )

                # Early-stop: if an entire page yields 0 new unique jobs,
                # subsequent pages will be even more redundant — stop now.
                if new_count == 0:
                    logging.info(
                        "APEC: Early stop for '%s' on page %d — 0 new jobs.", kw, page + 1
                    )
                    break

                page += 1
                time.sleep(1)

        if not href_scores:
            print("\nNo jobs found for any keyword. Exiting.")
            logging.info("APEC: No jobs collected during discovery phase.")
        else:
            # Sort hrefs: highest score first (most keyword overlaps = best match)
            sorted_hrefs = sorted(
                href_scores.keys(), key=lambda h: href_scores[h], reverse=True
            )
            total_unique = len(sorted_hrefs)
            max_score = max(href_scores.values())
            print(
                f"\n{'─' * 50}\n"
                f"Unique jobs collected : {total_unique}\n"
                f"Best match score      : {max_score}/{len(keywords)} keywords\n"
                f"Starting applications (best matches first)...\n"
                f"{'─' * 50}",
                flush=True,
            )
            logging.info(
                "APEC: Discovery complete. %d unique jobs, max score %d/%d.",
                total_unique, max_score, len(keywords),
            )

            # ================================================================
            # Phase 2 — Application: apply to jobs in best-match order
            for href in sorted_hrefs:
                if not session_alive:
                    break

                score = href_scores[href]
                try:
                    applied = _process_job(driver, wait, href, processed_count, score, keywords)
                except (InvalidSessionIdException, WebDriverException):
                    logging.error("APEC: browser session died during application phase.")
                    session_alive = False
                    break

                processed_count += 1
                if applied:
                    applied_count += 1

                print(
                    f"\rJobs processed: {processed_count}/{total_unique}  "
                    f"Applied: {applied_count}  "
                    f"[match {score}/{len(keywords)}]   ",
                    end="",
                    flush=True,
                )
                time.sleep(0.5)



    except Exception:
        logging.exception("APEC: unexpected error in main loop.")
        print("\nAn unexpected error occurred.")

    finally:
        logging.info("APEC Session ended. Total jobs applied to: %d", applied_count)
        print(f"\nAPEC Session ended. Total jobs applied to: {applied_count}")
        try:
            driver.quit()
        except Exception:
            pass


def _collect_job_links(driver, wait) -> list:
    """Load current results page and collect all job detail hrefs.

    Collects hrefs up-front so we never hold stale Selenium element
    references across page navigations.  Returns [] if no jobs found.
    """
    try:
        job_elements = wait.until(
            EC.presence_of_all_elements_located(
                (By.XPATH, "//div[@class='container-result']/div")
            )
        )
    except TimeoutException:
        return []

    hrefs = []
    for job in job_elements:
        try:
            link = job.find_element(
                By.XPATH, ".//a[contains(@href, '/detail-offre/')]"
            )
            href = link.get_attribute("href").split("?")[0]
            if href and href not in hrefs:  # deduplicate sponsored duplicates
                hrefs.append(href)
        except (NoSuchElementException, WebDriverException):
            continue  # Malformed card — skip

    return hrefs


def _is_already_applied(driver) -> bool:
    """Return True if APEC shows a 'Vous avez déjà postulé' banner."""
    # Strategy 1: look for a button/badge labelled "Déjà postulé"
    already_applied_els = driver.find_elements(
        By.XPATH,
        "//*["
        "contains(translate(normalize-space(text()), "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ\u00c0\u00c2\u00c9\u00c8\u00ca\u00cb\u00ce\u00cf\u00d4\u00d9\u00db\u00dc\u00c7', "
        "'abcdefghijklmnopqrstuvwxyz\u00e0\u00e2\u00e9\u00e8\u00ea\u00eb\u00ee\u00ef\u00f4\u00f9\u00fb\u00fc\u00e7'), "
        "'d\u00e9j\u00e0 postul') or "
        "contains(translate(normalize-space(text()), "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', "
        "'abcdefghijklmnopqrstuvwxyz'), "
        "'deja postule')"
        "]",
    )
    if any(el.is_displayed() for el in already_applied_els):
        return True

    # Strategy 2: check for the green confirmation icon / "candidature envoyée" text
    sent_els = driver.find_elements(
        By.XPATH,
        "//*[contains(translate(normalize-space(text()), "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ\u00c0\u00c2\u00c9\u00c8\u00ca\u00cb\u00ce\u00cf\u00d4\u00d9\u00db\u00dc\u00c7', "
        "'abcdefghijklmnopqrstuvwxyz\u00e0\u00e2\u00e9\u00e8\u00ea\u00eb\u00ee\u00ef\u00f4\u00f9\u00fb\u00fc\u00e7'), "
        "'candidature envoy\u00e9e')]",
    )
    return any(el.is_displayed() for el in sent_els)


def _matches_keywords(driver, keywords: list) -> tuple:
    """Return (matched: bool, matched_keyword: str) based on visible page text.

    Searches the full body text (job title + description) for any of the
    supplied keywords (case-insensitive, accent-insensitive via lower()).
    Returns (True, keyword) on first match, (False, '') if none match.
    """
    if not keywords:
        return True, "(no filter)"
    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
    except Exception:
        # If we can't read the page, let it through to avoid false-negatives
        return True, "(page unreadable)"
    for kw in keywords:
        if kw in body_text:
            return True, kw
    return False, ""


def _process_job(driver, wait, href: str, job_idx: int, page: int, keywords: list = None) -> bool:
    """Navigate to a job page and attempt to apply.

    Returns True if the application was submitted successfully, False otherwise.
    All exceptions are caught and logged so the caller loop always continues.
    """
    try:
        driver.get(href)
        time.sleep(1)

        # --- Already applied? ---
        if _is_already_applied(driver):
            logging.info(
                "APEC: Skipped job index %d (page %d) - Already applied ('Vous avez déjà postulé').",
                job_idx, page,
            )
            return False

        # --- Keyword filter: at least one keyword must appear in job text ---
        matched, matched_kw = _matches_keywords(driver, keywords or [])
        if not matched:
            logging.info(
                "APEC: Skipped job index %d (page %d) - No keyword match (keywords: %s).",
                job_idx, page, keywords,
            )
            return False
        logging.info(
            "APEC: Job index %d (page %d) matched keyword '%s'.",
            job_idx, page, matched_kw,
        )

        # --- Find the first-level "Postuler" anchor ---
        try:
            apply_button = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//a[@class='btn btn-primary mr-12 mb-20']")
                )
            )
        except TimeoutException:
            logging.info(
                "APEC: Skipped job index %d (page %d) - No native apply button found (might be external or closed).",
                job_idx, page,
            )
            return False

        btn_text = apply_button.text.strip()
        if btn_text != "Postuler":
            logging.info(
                "APEC: Skipped job index %d (page %d) - External application site (button text: '%s').",
                job_idx, page, btn_text,
            )
            return False

        # --- Step 1: click "Postuler" to open the modal ---
        apply_button.click()
        time.sleep(1)

        # --- Step 2: click "Postuler" inside the modal (confirm intent) ---
        try:
            apply_button2 = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[@title='Postuler']")
                )
            )
        except TimeoutException:
            logging.info(
                "APEC: Skipped job index %d (page %d) - Modal 'Postuler' button not found.",
                job_idx, page,
            )
            return False

        apply_button2.click()
        time.sleep(1)

        # --- Step 3: click "Envoyer ma candidature" (final confirm) ---
        try:
            apply_button3 = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[@title='Envoyer ma candidature']")
                )
            )
        except TimeoutException:
            logging.info(
                "APEC: Skipped job index %d (page %d) - Required extra steps (custom form/attachments).",
                job_idx, page,
            )
            return False

        apply_button3.click()

        # --- Wait for the confirmation banner to appear ---
        # APEC shows either "Votre candidature a bien été envoyée" or the
        # "Vous avez déjà postulé" banner after a successful submit.
        time.sleep(2)
        confirmed = _wait_for_application_confirmation(driver, timeout=8)
        if confirmed:
            logging.info(
                "APEC: Applied to job index %d (page %d) — confirmation received.",
                job_idx, page,
            )
            return True
        else:
            # The click went through but no confirmation banner appeared.
            # Count it anyway to avoid under-counting if APEC was just slow.
            logging.warning(
                "APEC: Applied to job index %d (page %d) — no confirmation banner detected (may still have worked).",
                job_idx, page,
            )
            return True

    except (InvalidSessionIdException, WebDriverException):
        # Re-raise session-fatal exceptions so the caller can stop the loop.
        raise

    except Exception:
        logging.exception(
            "APEC: unexpected error processing job index %d (page %d).", job_idx, page
        )
        return False


def _wait_for_application_confirmation(driver, timeout: int = 8) -> bool:
    """Poll for a post-apply confirmation element on the current page.

    Returns True as soon as any confirmation indicator is visible.
    Returns False if nothing appears within *timeout* seconds.
    """
    confirmation_xpath = (
        "//*["
        "contains(translate(normalize-space(text()), "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ\u00c0\u00c2\u00c9\u00c8\u00ca\u00cb\u00ce\u00cf\u00d4\u00d9\u00db\u00dc\u00c7', "
        "'abcdefghijklmnopqrstuvwxyz\u00e0\u00e2\u00e9\u00e8\u00ea\u00eb\u00ee\u00ef\u00f4\u00f9\u00fb\u00fc\u00e7'), "
        "'candidature a bien') or "
        "contains(translate(normalize-space(text()), "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ\u00c0\u00c2\u00c9\u00c8\u00ca\u00cb\u00ce\u00cf\u00d4\u00d9\u00db\u00dc\u00c7', "
        "'abcdefghijklmnopqrstuvwxyz\u00e0\u00e2\u00e9\u00e8\u00ea\u00eb\u00ee\u00ef\u00f4\u00f9\u00fb\u00fc\u00e7'), "
        "'d\u00e9j\u00e0 postul')"
        "]"
    )
    deadline = time.time() + timeout
    while time.time() < deadline:
        els = driver.find_elements(By.XPATH, confirmation_xpath)
        if any(el.is_displayed() for el in els):
            return True
        time.sleep(0.5)
    return False
