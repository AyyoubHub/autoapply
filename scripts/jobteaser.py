import time
import logging
import questionary
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    ElementClickInterceptedException,
    InvalidSessionIdException,
    WebDriverException,
)

from base_portal import BaseJobPortal
from utils import (
    check_and_prompt_jobteaser_config,
    build_jobteaser_search_url_prefix,
    ask_timeout,
)


class JobTeaserPortal(BaseJobPortal):
    def __init__(self, config, search_url, timeout_secs, force_reprocess):
        super().__init__("JobTeaser", force_reprocess)
        self.config = config
        self.search_url = search_url
        self.timeout_secs = timeout_secs
        self.start_time = time.time()

    def authenticate(self):
        email = self.config["jobteaser_email"]
        password = self.config["jobteaser_password"]

        login_url = "https://www.jobteaser.com/fr/users/sign_in"
        connect_url = "https://www.jobteaser.com/users/auth/connect"

        logging.info("[JobTeaser] Navigating to login page.")
        self.driver.get(login_url)

        try:
            accept_button = self.wait_for_clickable((By.ID, "didomi-notice-agree-button"), timeout=3)
            accept_button.click()
            logging.debug("[JobTeaser] Cookie banner dismissed.")
        except TimeoutException:
            pass

        self.driver.get(connect_url)

        email_input = self.wait_for_presence((By.ID, "email"))
        email_input.clear()
        email_input.send_keys(email)

        password_input = self.wait_for_presence((By.ID, "passwordInput"))
        password_input.clear()
        password_input.send_keys(password)

        password_input.submit()

        # Wait for redirect away from the connect/sign-in page
        try:
            from selenium.webdriver.support.ui import WebDriverWait
            WebDriverWait(self.driver, 10).until(
                lambda d: "connect" not in d.current_url and "sign_in" not in d.current_url
            )
        except TimeoutException:
            pass  # Check will catch the login failure below

        self.driver.get("https://www.jobteaser.com/fr/dashboard")

        # Wait for the dashboard to confirm we're logged in
        try:
            self.wait_for_presence((By.TAG_NAME, "main"), timeout=8)
        except TimeoutException:
            pass

        if "sign-in" in self.driver.current_url.lower() or "login" in self.driver.current_url.lower():
            raise Exception("Login rejected by JobTeaser. Check credentials.")

        logging.info("[JobTeaser] Login verified.")
        print("JobTeaser login successful.")

    def discover_jobs(self, keywords):
        print("Scanning JobTeaser for jobs...", flush=True)
        all_jobs = []
        page = 1

        while time.time() - self.start_time < self.timeout_secs:
            try:
                self.driver.get(f"{self.search_url}{page}")
                job_elements = self.wait_for_all_presence(
                    (By.XPATH, "//ul[@class='PageContent_results__zSSNO']/li"), timeout=5
                )
            except TimeoutException:
                logging.info("[JobTeaser] No more jobs on page %d — stopping discovery.", page)
                break
            except (InvalidSessionIdException, WebDriverException) as e:
                logging.error("[JobTeaser] Browser session lost during discovery: %s", e)
                break

            if not job_elements:
                break

            new_count = 0
            for job in job_elements:
                try:
                    job_link = job.find_element(By.XPATH, ".//a[contains(@href, '/job-offers/')]")
                    href = job_link.get_attribute("href").split("?")[0]
                    if not any(j['href'] == href for j in all_jobs):
                        all_jobs.append({"href": href})
                        new_count += 1
                except Exception as e:
                    logging.debug("[JobTeaser] Failed to extract href from job card: %s", e)

            print(f"  Page {page}: {len(job_elements)} jobs ({new_count} new · {len(all_jobs)} unique total)", flush=True)

            if new_count == 0:
                logging.info("[JobTeaser] Page %d yielded no new results — stopping early.", page)
                break

            page += 1

        return all_jobs

    def apply_to_job(self, job, keywords):
        href = job['href']
        logging.info("[JobTeaser] Processing job: %s", href)
        self.driver.get(href)

        # 1. Extract Metadata
        job_title = "Unknown"
        company_name = "Unknown"
        try:
            job_title = self.wait_for_presence(
                (By.CSS_SELECTOR, "[data-testid='jobad-DetailView__Heading__title']"), timeout=5
            ).text
            company_name = self.driver.find_element(
                By.CSS_SELECTOR, "[data-testid='jobad-DetailView__Heading__company_name']"
            ).text
        except TimeoutException:
            logging.warning("[JobTeaser] Primary metadata selectors timed out for %s — trying fallback.", href)
            try:
                job_title = self.driver.find_element(By.TAG_NAME, "h1").text
                company_name = self.driver.find_element(
                    By.XPATH, "//div[contains(@class, 'CompanyProfile_name')]"
                ).text
            except Exception as e:
                logging.debug("[JobTeaser] Fallback metadata extraction also failed for %s: %s", href, e)

        job_id = href.split("/")[-1].split("-")[0]
        app_id = self.db.add_job_application(self.run_id, job_id, href, job_title, company_name)

        print(f"\r{' '*80}\r[Job] {job_title} @ {company_name}")

        # 2. Check if already applied natively (wait for React to render)
        try:
            self.wait_for_presence((By.TAG_NAME, "main"), timeout=5)
        except TimeoutException:
            pass

        already_applied = self.driver.find_elements(
            By.XPATH,
            "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'candidature envoyée') or "
            "contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'candidature envoyee') or "
            "contains(normalize-space(.), 'Vous avez postulé à cette offre !')]"
        )
        if any(el.is_displayed() for el in already_applied):
            logging.info("[JobTeaser] Skipped %s — already applied natively.", href)
            print("  ↳ Skipped: Already applied natively on JobTeaser")
            if app_id:
                self.db.update_job_state(app_id, "Already Applied")
            return "already_applied"

        # 3. Open Application Modal
        _apply_internal_xpath = (
            "//button[@data-testid='jobad-DetailView__CandidateActions__Buttons_apply_internal_candidacy']"
            " | //button[contains(normalize-space(.), 'Candidature simplifiée')]"
            " | //button[contains(normalize-space(.), 'Postuler') and not(contains(@href, 'http'))]"
        )
        try:
            apply_button = self.wait_for_clickable((By.XPATH, _apply_internal_xpath), timeout=8)
            try:
                apply_button.click()
            except ElementClickInterceptedException:
                self._dismiss_cookie_banner()
                apply_button.click()
        except TimeoutException:
            logging.info("[JobTeaser] Skipped %s — no internal apply button found (external offer).", href)
            print("  ↳ Skipped: Internal apply button not found (might be external)")
            if app_id:
                self.db.update_job_state(app_id, "External")
            return "external"

        # Wait for the modal form to become interactive before filling
        _modal_indicator_xpath = (
            "//input[@required] | //textarea[@required] | "
            "//button[@data-testid='jobad-DetailView__ApplicationFlow__Buttons__apply_button'] | "
            "//button[contains(normalize-space(.), 'Postuler maintenant')]"
        )
        try:
            self.wait_for_presence((By.XPATH, _modal_indicator_xpath), timeout=8)
            logging.debug("[JobTeaser] Modal loaded for %s", href)
        except TimeoutException:
            logging.warning("[JobTeaser] Modal did not load within timeout for %s — proceeding anyway.", href)

        # 4. Fill Form
        try:
            self._fill_application_form(href)
        except ValueError as e:
            msg = str(e)
            logging.warning("[JobTeaser] Aborted %s — %s", href, msg)
            print(f"  ↳ Failed: {msg}")
            if app_id:
                self.db.update_job_state(app_id, "Application Failed", ai_reason=msg)
            return "failed"

        # 5. Submit Application (Multi-step support)
        _submit_xpath = (
            "//button[@data-testid='jobad-DetailView__ApplicationFlow__Buttons__apply_button']"
            " | //button[contains(normalize-space(.), 'Postuler maintenant')]"
            " | //button[contains(normalize-space(.), 'Continuer')]"
            " | //button[contains(normalize-space(.), 'Suivant')]"
            " | //button[contains(normalize-space(.), 'Valider')]"
            " | //button[contains(normalize-space(.), 'Envoyer ma candidature')]"
        )

        for step in range(3):
            try:
                submit_button = self.wait_for_clickable((By.XPATH, _submit_xpath), timeout=10)
                btn_text = submit_button.text.lower()
                logging.debug("[JobTeaser] Step %d: clicking '%s' for %s", step + 1, btn_text, href)

                try:
                    submit_button.click()
                except ElementClickInterceptedException:
                    self._dismiss_cookie_banner()
                    submit_button.click()

                if any(x in btn_text for x in ["postuler", "envoyer", "valider"]):
                    break

                # Wait for the next step to load
                try:
                    self.wait_for_visible((By.XPATH, _submit_xpath), timeout=8)
                except TimeoutException:
                    logging.debug("[JobTeaser] Next step button not visible after step %d — assuming done.", step + 1)
                    break

            except TimeoutException:
                if step == 0:
                    logging.warning("[JobTeaser] Submit/next button not found in modal for %s.", href)
                    print("  ↳ Failed: Submit button not found in modal")
                    if app_id:
                        self.db.update_job_state(app_id, "Application Failed", ai_reason="Submit button not found")
                    return "failed"
                logging.debug("[JobTeaser] No more steps found after step %d for %s.", step, href)
                break

        # 6. Wait for Success Confirmation
        _success_xpath = (
            "//*[@data-testid='jobad-DetailView__ApplicationFlow__Success']"
            " | //*[contains(normalize-space(.), 'Candidature envoyée')]"
            " | //*[contains(normalize-space(.), 'candidature a été bien envoyée')]"
            " | //*[contains(normalize-space(.), 'candidature a bien été envoyée')]"
            " | //*[contains(normalize-space(.), 'déjà postulé')]"
            " | //*[contains(normalize-space(.), 'Vous avez postulé à cette offre !')]"
            " | //*[contains(normalize-space(.), 'Application successful')]"
        )
        try:
            self.wait_for_visible((By.XPATH, _success_xpath), timeout=10)
            logging.info("[JobTeaser] Successfully applied to %s", href)
            print("  ↳ Applied Successfully!")
            if app_id:
                self.db.update_job_state(app_id, "Applied Successfully")
            return "applied"
        except TimeoutException:
            # Clicked submit with no error detected — optimistically mark as applied
            logging.warning(
                "[JobTeaser] Applied to %s but confirmation banner not detected — marking as applied anyway.", href
            )
            print("  ↳ Applied (confirmation banner not detected)")
            if app_id:
                self.db.update_job_state(app_id, "Applied Successfully", ai_reason="Confirmation banner not detected")
            return "applied"

    def _fill_application_form(self, href: str = ""):
        """
        Fills the application form.
        Raises ValueError if a required field has no corresponding value in config.
        """
        form_data = self.config.get("form_data", {})
        missing_required = []

        # 1. Gender dropdown
        gender_val = form_data.get("gender", "").strip()
        if gender_val:
            try:
                combobox = self.driver.find_elements(By.CSS_SELECTOR, "[role='combobox'][id='gender']")
                if combobox and combobox[0].get_attribute("aria-expanded") == "false":
                    combobox[0].click()
                    time.sleep(0.5)
                    options = self.driver.find_elements(By.CSS_SELECTOR, "[id='gender-dropdown'] [role='option']")
                    matched = False
                    for opt in options:
                        if gender_val.lower() in opt.text.lower():
                            opt.click()
                            matched = True
                            logging.debug("[JobTeaser] Gender set to '%s' for %s", gender_val, href)
                            break
                    if not matched:
                        logging.warning("[JobTeaser] Could not find gender option '%s' for %s", gender_val, href)
            except Exception as e:
                logging.warning("[JobTeaser] Error filling gender field for %s: %s", href, e)

        # 2. Cover letter textarea
        cover_text = form_data.get("coverLetterContent", "").strip()
        if cover_text:
            try:
                cl_els = self.driver.find_elements(By.NAME, "coverLetterContent")
                filled = 0
                for cl in cl_els:
                    if not cl.get_attribute("value"):
                        self.driver.execute_script(
                            "arguments[0].value = arguments[1]; "
                            "arguments[0].dispatchEvent(new Event('input', { bubbles: true }));",
                            cl, cover_text,
                        )
                        filled += 1
                if filled:
                    logging.debug("[JobTeaser] Filled %d cover letter field(s) for %s", filled, href)
            except Exception as e:
                logging.warning("[JobTeaser] Error filling cover letter for %s: %s", href, e)

        # 3. Strict fill for required inputs / textareas
        try:
            required_inputs = self.driver.find_elements(
                By.XPATH, "//input[@required] | //textarea[@required]"
            )
            for inp in required_inputs:
                if inp.get_attribute("value"):
                    continue  # Already has a value

                tag_name = inp.tag_name.lower()
                name_attr = (inp.get_attribute("name") or "").lower()
                label_text = self._get_label_for_element(inp)

                val = None
                if tag_name == "textarea" or "motivation" in name_attr or "cover" in name_attr:
                    val = form_data.get("coverLetterContent", "").strip()
                elif "phone" in name_attr:
                    val = form_data.get("phoneNumber", "").strip()
                elif "email" in name_attr:
                    val = form_data.get("email", self.config.get("jobteaser_email", "")).strip()
                elif "name" in name_attr or "identity" in name_attr:
                    val = form_data.get("fullname", "").strip()

                if val:
                    self.driver.execute_script("arguments[0].value = arguments[1];", inp, val)
                    inp.send_keys(" ")   # Trigger React validation
                    inp.send_keys("\b")
                    logging.debug(
                        "[JobTeaser] Filled required field '%s' (name='%s') for %s",
                        label_text, name_attr, href,
                    )
                else:
                    logging.warning(
                        "[JobTeaser] Required field '%s' (name='%s') has no value in config for %s",
                        label_text, name_attr, href,
                    )
                    missing_required.append(label_text)

        except Exception as e:
            logging.warning("[JobTeaser] Error during required-field scan for %s: %s", href, e)

        if missing_required:
            fields = list(dict.fromkeys(missing_required))
            raise ValueError(f"Missing required config fields: {', '.join(fields)}")

        # 4. Auto-click mandatory checkboxes (GDPR consent, etc.)
        try:
            checkboxes = self.driver.find_elements(
                By.XPATH, "//input[@type='checkbox' and @required]"
            )
            for cb in checkboxes:
                if not cb.is_selected():
                    try:
                        self.driver.execute_script("arguments[0].click();", cb)
                        logging.debug("[JobTeaser] Checked mandatory checkbox for %s", href)
                    except Exception as e:
                        logging.warning("[JobTeaser] Could not check mandatory checkbox for %s: %s", href, e)
        except Exception as e:
            logging.warning("[JobTeaser] Error during checkbox scan for %s: %s", href, e)

        # 5. Save profile section (if present — some forms have it)
        try:
            save_btn = self.driver.find_elements(
                By.XPATH, "//button[contains(text(), 'Sauvegarder') or contains(text(), 'Enregistrer')]"
            )
            if save_btn:
                save_btn[0].click()
                logging.debug("[JobTeaser] Clicked save profile button for %s", href)
                time.sleep(1)
        except Exception as e:
            logging.debug("[JobTeaser] No save button or error clicking it for %s: %s", href, e)

    def _get_label_for_element(self, element) -> str:
        """Attempts to find a text label for a given input element."""
        try:
            eid = element.get_attribute("id")
            if eid:
                labels = self.driver.find_elements(By.XPATH, f"//label[@for='{eid}']")
                if labels:
                    return labels[0].text.strip()

            al = element.get_attribute("aria-label")
            if al:
                return al.strip()

            ph = element.get_attribute("placeholder")
            if ph:
                return ph.strip()

            parent = element.find_element(By.XPATH, "./..")
            if parent:
                text = parent.text.split('\n')[0].strip()
                if text:
                    return text
        except Exception:
            pass
        return element.get_attribute("name") or "Unknown Field"


def run() -> None:
    config = check_and_prompt_jobteaser_config()

    keyword = (questionary.text("Enter job keywords:").ask() or "").strip()
    if not keyword:
        keyword = (questionary.text("Keywords (required):").ask() or "").strip()
    if not keyword:
        print("No keyword — exiting.")
        return

    # Contracts
    while True:
        contracts = questionary.checkbox(
            "Contract type(s) — space to select, Enter to confirm (select at least one):",
            choices=[
                questionary.Choice("CDI", "cdi", checked=True),
                questionary.Choice("CDD", "cdd"),
                questionary.Choice("Stage (Internship)", "internship"),
                questionary.Choice("Alternance", "alternating"),
                questionary.Choice("Graduate Program", "graduate_program"),
                questionary.Choice("VIE / VIA", "vie_via"),
                questionary.Choice("Freelance", "freelance"),
                questionary.Choice("No filter (all types)", None),
            ],
        ).ask() or []
        if contracts:
            break
        print("  ⚠ Please select at least one contract type (or choose 'No filter').")

    # Experience
    while True:
        work_experience_codes = questionary.checkbox(
            "Experience level(s) — space to select, Enter to confirm:",
            choices=[
                questionary.Choice("Étudiant / jeune diplomé", "young_graduate", checked=True),
                questionary.Choice("3 à 5 ans", "three_to_five_years", checked=True),
                questionary.Choice("6 à 10 ans", "six_to_ten_years"),
                questionary.Choice("Plus de 10 ans", "more_than_ten_years"),
                questionary.Choice("All levels (no filter)", None),
            ],
        ).ask() or []
        if work_experience_codes:
            break
        print("  ⚠ Please select at least one experience level (or choose 'All levels').")

    remote_map = {
        "Télétravail complet (Full remote)": "remote_full",
        "Télétravail partiel (Partial)":    "remote_partial",
        "Sur site uniquement (On-site)":     "no_remote",
        "Pas de filtre":                     None,
    }
    chosen_remote = questionary.select(
        "Remote preference:",
        choices=list(remote_map.keys()),
    ).ask()
    remote_types = remote_map.get(chosen_remote)

    # Language
    while True:
        languages = questionary.checkbox(
            "Job language(s) — space to select, Enter to confirm (select at least one):",
            choices=[
                questionary.Choice("Français", "fr", checked=True),
                questionary.Choice("English", "en", checked=True),
                questionary.Choice("No filter (all languages)", None),
            ],
        ).ask() or []
        if languages:
            break
        print("  ⚠ Please select at least one language (or choose 'No filter').")

    contracts = [c for c in contracts if c]
    work_experience_codes = [wec for wec in work_experience_codes if wec]
    languages = [l for l in languages if l]

    sort = questionary.select(
        "Sort results by:",
        choices=[
            questionary.Choice("Date (most recent first)", "recency"),
            questionary.Choice("Relevance",                "relevance"),
        ],
    ).ask()

    timeout_secs = ask_timeout()

    force_reprocess = questionary.confirm(
        "Force reprocess previously seen / rejected jobs?", default=False
    ).ask()

    search_url = build_jobteaser_search_url_prefix(
        keyword=keyword,
        sort=sort,
        contracts=contracts or None,
        work_experience_codes=work_experience_codes or None,
        remote_types=remote_types,
        languages=languages or None,
    )

    logging.info("[JobTeaser] Search URL prefix: %s", search_url)
    print("Search: internal applications (candidature simplifiée / Postuler) only.\n")

    portal = JobTeaserPortal(config, search_url, timeout_secs, force_reprocess)
    portal.run_portal([keyword])
