import time
import re
import urllib.parse
import questionary
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    InvalidSessionIdException,
    WebDriverException,
    ElementClickInterceptedException,
)

from base_portal import BaseJobPortal
from utils import check_and_prompt_apec_config, save_config

class APECPortal(BaseJobPortal):
    def __init__(self, config, contract_type, sort_by, date_filter_param, max_pages_per_kw, force_reprocess):
        super().__init__("APEC", force_reprocess)
        self.config = config
        self.contract_type = contract_type
        self.sort_by = sort_by
        self.date_filter_param = date_filter_param
        self.max_pages_per_kw = max_pages_per_kw

    def authenticate(self):
        email = self.config["apec_email"]
        password = self.config["apec_password"]
        login_url = "https://www.apec.fr/"

        logging.info("[APEC] Navigating to login page.")
        self.driver.get(login_url)

        try:
            cookies_button = self.wait_for_clickable((By.ID, "didomi-notice-agree-button"), timeout=3)
            cookies_button.click()
            logging.debug("[APEC] Cookie banner dismissed.")
        except TimeoutException:
            pass

        login_popup_button = self.wait_for_clickable((By.XPATH, "//a[@onclick='showloginPopin()']"))
        login_popup_button.click()

        email_input = self.wait_for_presence((By.NAME, "emailid"))
        email_input.clear()
        email_input.send_keys(email)

        password_input = self.wait_for_presence((By.NAME, "password"))
        password_input.clear()
        password_input.send_keys(password)

        login_button = self.wait_for_clickable((By.XPATH, "//button[contains(text(), 'Se connecter')]"))
        login_button.click()

        # Wait for either an error message or successful navigation away from the form
        time.sleep(2)
        error_els = self.driver.find_elements(
            By.XPATH,
            "//*[self::span or self::p or self::div or self::li]"
            "["
            "contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'incorrect') or "
            "contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'invalide') or "
            "contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'failed') or "
            "contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'erreur')"
            "]",
        )
        visible_errors = [el for el in error_els if el.is_displayed() and el.text.strip()]
        if visible_errors:
            error_text = visible_errors[0].text.strip()
            raise Exception(f"APEC login form error: '{error_text}'. Check credentials.")

        logging.info("[APEC] Navigating to personal space to confirm login.")
        self.driver.get("https://www.apec.fr/candidat/mon-espace.html")

        # Wait for the personal space to load (any heading element)
        try:
            self.wait_for_presence((By.TAG_NAME, "h1"), timeout=8)
        except TimeoutException:
            pass

        if "connexion" in self.driver.current_url.lower() or "login" in self.driver.current_url.lower():
            raise Exception("Login rejected by APEC (redirected to login page). Check credentials.")

        logging.info("[APEC] Session started — login verified.")
        print("APEC login successful.")

    def discover_jobs(self, keywords):
        href_scores = {}

        for kw_idx, kw in enumerate(keywords):
            if not self.ensure_session_alive():
                break

            encoded_kw = urllib.parse.quote_plus(kw)
            kw_search_url = (
                "https://www.apec.fr/candidat/recherche-emploi.html/emploi?"
                "typesConvention=143684&typesConvention=143685"
                "&typesConvention=143686&typesConvention=143687"
                f"&motsCles={encoded_kw}"
                f"&typesContrat={self.contract_type}"
                f"&sortsType={self.sort_by}"
                f"{self.date_filter_param}"
                "&page="
            )

            label = f"(up to {self.max_pages_per_kw} pages)" if self.max_pages_per_kw != float("inf") else "(all pages — date-filtered)"
            print(f"\n[{kw_idx + 1}/{len(keywords)}] Scanning APEC for '{kw}' {label}...", flush=True)

            page = 0
            while page < self.max_pages_per_kw:
                if not self.ensure_session_alive():
                    break

                try:
                    self.driver.get(f"{kw_search_url}{page}")
                    hrefs = self._collect_job_links()
                except (InvalidSessionIdException, WebDriverException):
                    logging.error("[APEC] Browser session lost during discovery for '%s'.", kw)
                    self.teardown_browser()
                    break
                except Exception as e:
                    logging.warning("[APEC] Unexpected error during discovery page %d for '%s': %s", page, kw, e)
                    break

                if not hrefs:
                    logging.info("[APEC] No jobs found on page %d for '%s' — stopping.", page, kw)
                    break

                new_count = sum(1 for h in hrefs if h not in href_scores)
                for href in hrefs:
                    href_scores[href] = href_scores.get(href, 0) + 1

                page_label = str(page + 1) if self.max_pages_per_kw == float("inf") else f"{page + 1}/{int(self.max_pages_per_kw)}"
                print(f"  Page {page_label}: {len(hrefs)} jobs ({new_count} new · {len(href_scores)} unique total)", flush=True)

                if new_count == 0:
                    logging.info("[APEC] Page %d yielded no new results for '%s' — stopping early.", page, kw)
                    break

                page += 1
                time.sleep(1)  # Rate-limit between pages

        sorted_hrefs = sorted(href_scores.keys(), key=lambda h: href_scores[h], reverse=True)
        jobs = [{"href": href, "score": href_scores[href]} for href in sorted_hrefs]

        if jobs:
            max_score = max(href_scores.values())
            print(f"Best match score: {max_score}/{len(keywords)} keywords\n")
        else:
            print("No jobs found for the given keywords and filters.\n")

        return jobs

    def _collect_job_links(self) -> list:
        try:
            job_elements = self.wait_for_all_presence((By.XPATH, "//div[@class='container-result']/div"), timeout=5)
        except TimeoutException:
            return []

        hrefs = []
        for job in job_elements:
            try:
                link = job.find_element(By.XPATH, ".//a[contains(@href, '/detail-offre/')]")
                href = link.get_attribute("href").split("?")[0]
                if href and href not in hrefs:
                    hrefs.append(href)
            except (NoSuchElementException, WebDriverException):
                continue
        return hrefs

    def apply_to_job(self, job, keywords):
        href = job['href']
        logging.info("[APEC] Processing job: %s", href)
        self.driver.get(href)

        job_title = "Unknown"
        job_company = "Unknown"
        job_id = href.split("/")[-1].split("?")[0]

        try:
            job_title = self.wait_for_presence((By.TAG_NAME, "h1"), timeout=5).text.strip()
        except TimeoutException:
            logging.warning("[APEC] Could not find job title (h1) for %s", href)

        try:
            job_company = self.driver.find_element(By.XPATH, "//div[contains(@class, 'company-name')]").text.strip()
        except NoSuchElementException:
            logging.debug("[APEC] Company name element not found for %s", href)

        app_id = self.db.add_job_application(self.run_id, job_id, href, job_title, job_company)
        print(f"\r{' '*80}\r[Job] {job_title} @ {job_company}")

        # Already Applied Native Check
        if self._is_already_applied():
            logging.info("[APEC] Skipped %s — already applied (detected on page).", href)
            print("  ↳ Skipped: Already applied on APEC")
            if app_id:
                self.db.update_job_state(app_id, "Already Applied")
            return "already_applied"

        # Keyword Match
        matched, matched_kw = self._matches_keywords(keywords)
        if not matched:
            msg = f"No keyword match (none of {keywords} found in job body)"
            logging.info("[APEC] Skipped %s — %s", href, msg)
            print(f"  ↳ Skipped: {msg}")
            if app_id:
                self.db.update_job_state(app_id, "Irrelevant", ai_reason=msg)
            return "irrelevant"

        logging.debug("[APEC] Keyword match on '%s' for %s", matched_kw, href)

        # AI Check
        try:
            job_desc = self.driver.find_element(By.TAG_NAME, "body").text.strip()
            is_match, reason = self.evaluate_ai_match(job_title, job_desc, keywords, app_id)
            if not is_match:
                logging.info("[APEC] AI rejected %s — %s", href, reason)
                return "ai_rejected"
        except Exception as e:
            logging.warning("[APEC] Failed to extract body text for AI check on %s: %s", href, e)

        # Find Native Apply Button
        _native_xpath = "//a[normalize-space(.) = 'Postuler' and contains(@class, 'btn') and contains(@href, '?to=int')]"
        _fallback_xpath = "//a[normalize-space(.) = 'Postuler' and contains(@class, 'btn')]"

        apply_button = None
        try:
            apply_button = self.wait_for_clickable((By.XPATH, _native_xpath), timeout=3)
            logging.debug("[APEC] Found native apply button for %s", href)
        except TimeoutException:
            try:
                apply_button = self.driver.find_element(By.XPATH, _fallback_xpath)
                logging.debug("[APEC] Using fallback apply button for %s", href)
            except NoSuchElementException:
                pass

        if apply_button is None:
            logging.info("[APEC] Skipped %s — no native apply button found (external offer).", href)
            print("  ↳ Skipped: No native apply button (external)")
            if app_id:
                self.db.update_job_state(app_id, "External")
            return "external"

        # Modal flow — Step 1: click apply
        try:
            apply_button.click()
        except ElementClickInterceptedException:
            self._dismiss_cookie_banner()
            apply_button.click()

        # Step 2: Modal 'Postuler'
        try:
            apply_button2 = self.wait_for_clickable(
                (By.XPATH, "//button[contains(normalize-space(.), 'Postuler')]"), timeout=8
            )
            apply_button2.click()
            logging.debug("[APEC] Clicked step-2 Postuler for %s", href)
        except TimeoutException:
            logging.debug("[APEC] Step-2 button not found for %s — may be a direct apply.", href)

        # Step 3: Final 'Envoyer ma candidature'
        try:
            apply_button3 = self.wait_for_clickable(
                (By.XPATH, "//button[contains(normalize-space(.), 'Envoyer ma candidature')]"), timeout=8
            )
            apply_button3.click()
            logging.debug("[APEC] Clicked 'Envoyer ma candidature' for %s", href)
        except TimeoutException:
            # Step 2 may have been the final step — check for confirmation already
            if not self._wait_for_application_confirmation(timeout=3):
                logging.warning("[APEC] 'Envoyer ma candidature' button not found and no confirmation for %s.", href)
                print("  ↳ Failed: Final submit button not found in modal")
                if app_id:
                    self.db.update_job_state(app_id, "Application Failed", ai_reason="Final 'Envoyer' button not found")
                return "failed"

        confirmed = self._wait_for_application_confirmation(timeout=8)
        if confirmed:
            logging.info("[APEC] Successfully applied to %s", href)
            print("  ↳ Applied Successfully!")
            if app_id:
                self.db.update_job_state(app_id, "Applied Successfully")
            return "applied"
        else:
            # We clicked submit and saw no error — optimistically mark as applied
            logging.warning(
                "[APEC] Applied to %s but no confirmation banner detected — marking as applied anyway.",
                href,
            )
            print("  ↳ Applied (confirmation banner not detected)")
            if app_id:
                self.db.update_job_state(app_id, "Applied Successfully", ai_reason="No confirmation banner detected")
            return "applied"

    def _is_already_applied(self) -> bool:
        _xpath = (
            "//*["
            "contains(translate(normalize-space(text()), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ\u00c0\u00c2\u00c9\u00c8\u00ca\u00cb\u00ce\u00cf\u00d4\u00d9\u00db\u00dc\u00c7', 'abcdefghijklmnopqrstuvwxyz\u00e0\u00e2\u00e9\u00e8\u00ea\u00eb\u00ee\u00ef\u00f4\u00f9\u00fb\u00fc\u00e7'), 'd\u00e9j\u00e0 postul') or "
            "contains(translate(normalize-space(text()), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ\u00c0\u00c2\u00c9\u00c8\u00ca\u00cb\u00ce\u00cf\u00d4\u00d9\u00db\u00dc\u00c7', 'abcdefghijklmnopqrstuvwxyz\u00e0\u00e2\u00e9\u00e8\u00ea\u00eb\u00ee\u00ef\u00f4\u00f9\u00fb\u00fc\u00e7'), 'candidature envoy\u00e9e')"
            "]"
        )
        els = self.driver.find_elements(By.XPATH, _xpath)
        return any(el.is_displayed() for el in els)

    def _matches_keywords(self, keywords: list) -> tuple:
        if not keywords:
            return True, "(no filter)"
        try:
            body_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
        except Exception as e:
            logging.warning("[APEC] Could not read page body for keyword check: %s", e)
            return True, "(page unreadable)"

        for kw in keywords:
            if kw in body_text:
                return True, kw
        return False, ""

    def _wait_for_application_confirmation(self, timeout: int = 8) -> bool:
        """Wait for a visible application confirmation element using WebDriverWait."""
        confirmation_xpath = (
            "//*["
            "contains(translate(normalize-space(text()), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ\u00c0\u00c2\u00c9\u00c8\u00ca\u00cb\u00ce\u00cf\u00d4\u00d9\u00db\u00dc\u00c7', 'abcdefghijklmnopqrstuvwxyz\u00e0\u00e2\u00e9\u00e8\u00ea\u00eb\u00ee\u00ef\u00f4\u00f9\u00fb\u00fc\u00e7'), 'candidature a bien') or "
            "contains(translate(normalize-space(text()), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ\u00c0\u00c2\u00c9\u00c8\u00ca\u00cb\u00ce\u00cf\u00d4\u00d9\u00db\u00dc\u00c7', 'abcdefghijklmnopqrstuvwxyz\u00e0\u00e2\u00e9\u00e8\u00ea\u00eb\u00ee\u00ef\u00f4\u00f9\u00fb\u00fc\u00e7'), 'd\u00e9j\u00e0 postul')"
            "]"
        )
        try:
            self.wait_for_visible((By.XPATH, confirmation_xpath), timeout=timeout)
            return True
        except TimeoutException:
            return False


def run() -> None:
    config = check_and_prompt_apec_config()

    KEYWORD_RAW = questionary.text("Enter job keywords (space or comma separated):").ask()
    if not KEYWORD_RAW or not KEYWORD_RAW.strip():
        print("No keywords entered. Exiting.")
        return

    keywords = list(dict.fromkeys(k.lower() for k in re.split(r"[,;\s]+", KEYWORD_RAW.strip()) if k.strip()))

    date_range_choices = [
        questionary.Choice(title="Last 24 hours (Dernières 24h)",   value="101850"),
        questionary.Choice(title="Last 7 days  (7 derniers jours)",  value="101851"),
        questionary.Choice(title="Last 30 days (30 derniers jours)", value="101852"),
        questionary.Choice(title="All time     (no date filter)",     value=None),
    ]
    DISCOVERY_FILTER = questionary.select("Discover jobs posted in:", choices=date_range_choices).ask()
    date_filter_param = f"&anciennetePublication={DISCOVERY_FILTER}" if DISCOVERY_FILTER else ""

    if DISCOVERY_FILTER:
        MAX_PAGES_PER_KW = float("inf")
    else:
        current_val = config.get("apec_max_pages_per_keyword")
        if current_val is None or str(current_val).strip() == "" or current_val == 0:
            raw = questionary.text("Enter max pages to crawl per keyword (All time mode):", default="3").ask()
            try:
                MAX_PAGES_PER_KW = int(raw)
            except (ValueError, TypeError):
                MAX_PAGES_PER_KW = 3
            config["apec_max_pages_per_keyword"] = MAX_PAGES_PER_KW
            save_config(config)
        else:
            MAX_PAGES_PER_KW = int(current_val)

    contract_choices = {
        "CDI": "101888",
        "CDD": "101889",
        "Alternance": "101891",
        "Intérim": "101890",
    }
    CONTRACT_TYPE = questionary.select(
        "Select contract type:",
        choices=[questionary.Choice(title=label, value=code) for label, code in contract_choices.items()],
    ).ask()

    sorting_choices = {"Date": "DATE", "Score": "SCORE"}
    SORT_BY = questionary.select(
        "Sort jobs by:",
        choices=[questionary.Choice(title=label, value=code) for label, code in sorting_choices.items()],
    ).ask()

    FORCE_REPROCESS = questionary.confirm("Force reprocess previously seen/rejected jobs?", default=False).ask()

    portal = APECPortal(config, CONTRACT_TYPE, SORT_BY, date_filter_param, MAX_PAGES_PER_KW, FORCE_REPROCESS)
    portal.run_portal(keywords)
