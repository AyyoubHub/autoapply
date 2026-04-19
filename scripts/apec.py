from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    InvalidSessionIdException,
    WebDriverException,
)
import time
import urllib.parse
import logging
import questionary

from utils import load_config, create_driver, ask_timeout


def run() -> None:
    # --- Configuration & user input ---
    config = load_config()
    EMAIL = config["email"]
    PASSWORD = config["apec_password"]

    KEYWORD = questionary.text("Enter the job keyword:").ask()
    encoded_keyword = urllib.parse.quote_plus(KEYWORD)

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

    TIME_OUT = ask_timeout()

    # --- URLs ---
    LOGIN_URL = "https://www.apec.fr/"
    BASE_SEARCH_URL = (
        "https://www.apec.fr/candidat/recherche-emploi.html/emploi?"
        "typesConvention=143684&typesConvention=143685"
        "&typesConvention=143686&typesConvention=143687"
        f"&motsCles={encoded_keyword}"
        f"&typesContrat={CONTRACT_TYPE}"
        f"&sortsType={SORT_BY}"
        "&page="
    )

    # --- Driver ---
    driver = create_driver()
    wait = WebDriverWait(driver, 10)

    applied_count = 0
    processed_count = 0
    start_time = time.time()

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

        # --- Job search loop ---
        # session_alive tracks whether the Chrome session is still usable.
        # InvalidSessionIdException / WebDriverException mean Chrome died
        # (e.g. anti-bot detection, tab close) and we must stop immediately.
        session_alive = True
        page = 0

        while session_alive:
            if time.time() - start_time > TIME_OUT:
                break

            try:
                driver.get(f"{BASE_SEARCH_URL}{page}")
                job_list = wait.until(
                    EC.presence_of_all_elements_located(
                        (By.XPATH, "//div[@class='container-result']/div")
                    )
                )
            except (InvalidSessionIdException, WebDriverException):
                logging.error("APEC: browser session lost during page navigation.")
                break
            except Exception:
                break  # No more pages or page failed to load

            if not job_list:
                break  # Empty page — end of results

            for i in range(len(job_list)):
                if time.time() - start_time > TIME_OUT or not session_alive:
                    break

                try:
                    # Re-fetch list to avoid stale element references
                    job_list = wait.until(
                        EC.presence_of_all_elements_located(
                            (By.XPATH, "//div[@class='container-result']/div")
                        )
                    )
                    job = job_list[i]
                    driver.execute_script("arguments[0].scrollIntoView();", job)

                    job_link = job.find_element(
                        By.XPATH, ".//a[contains(@href, '/detail-offre/')]"
                    )
                    href = job_link.get_attribute("href").split('?')[0]
                    driver.get(href)

                    time.sleep(1)
                    # Check if already applied
                    already_applied = driver.find_elements(
                        By.XPATH, 
                        "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'déjà postulé') or "
                        "contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'deja postule')]"
                    )
                    if any(el.is_displayed() for el in already_applied):
                        logging.info("APEC: Skipped job index %d - Already applied ('Vous avez déjà postulé').", i)
                        continue  # This safely triggers the finally block to navigate back

                    try:
                        apply_button = wait.until(
                            EC.element_to_be_clickable(
                                (By.XPATH, "//a[@class='btn btn-primary mr-12 mb-20']")
                            )
                        )
                    except TimeoutException:
                        logging.info(
                            "APEC: Skipped job index %d - No native apply button found (might be external or closed).", i
                        )
                        continue

                    if apply_button.text == "Postuler":
                        apply_button.click()
                        time.sleep(1)

                        apply_button2 = wait.until(
                            EC.element_to_be_clickable(
                                (By.XPATH, "//button[@title='Postuler']")
                            )
                        )
                        apply_button2.click()
                        time.sleep(1)

                        try:
                            apply_button3 = wait.until(
                                EC.element_to_be_clickable(
                                    (By.XPATH, "//button[@title='Envoyer ma candidature']")
                                )
                            )
                            apply_button3.click()
                            applied_count += 1
                        except TimeoutException:
                            logging.info(
                                "APEC: Skipped job index %d - Required extra steps (custom form/attachments).", i
                            )
                    else:
                        logging.info(
                            "APEC: Skipped job index %d - External application site (button text: '%s').", 
                            i, apply_button.text
                        )

                except (InvalidSessionIdException, WebDriverException):
                    # Chrome session died — cannot recover; exit the loop cleanly
                    logging.error(
                        "APEC: browser session died at job index %d, page %d. Stopping.", i, page
                    )
                    session_alive = False
                    break

                except Exception:
                    logging.exception(
                        "APEC: error on job index %d, page %d.", i, page
                    )

                finally:
                    if session_alive:
                        # Update counter and navigate back to the list
                        processed_count += 1
                        print(
                            f"\rJobs processed: {processed_count}, "
                            f"Jobs applied to: {applied_count}",
                            end="",
                            flush=True,
                        )
                        try:
                            driver.get(f"{BASE_SEARCH_URL}{page}")
                            time.sleep(1)
                        except (InvalidSessionIdException, WebDriverException):
                            logging.error(
                                "APEC: browser session died while navigating back to list."
                            )
                            session_alive = False

            page += 1
            time.sleep(3)

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
