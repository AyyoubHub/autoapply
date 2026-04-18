import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import InvalidSessionIdException, WebDriverException
import time
import urllib.parse
import logging
import questionary
from questionary import Choice

from utils import load_config, create_driver, ask_timeout


def run() -> None:
    # --- Configuration & user input ---
    config = load_config()
    EMAIL = config["email"]
    PASSWORD = config["hellowork_password"]

    KEYWORD = questionary.text("Enter the job keyword:").ask()
    encoded_keyword = urllib.parse.quote_plus(KEYWORD)

    contract_choices = {
        "CDI": "CDI",
        "CDD": "CDD",
        "Alternance": "Alternance",
        "Stage": "Stage",
        "Freelance": "Freelance",
        "Intérim": "Travail_temp",
    }
    selected_contracts = questionary.checkbox(
        "Select contract types:",
        choices=list(contract_choices.keys()),
    ).ask()
    CONTRACT_TYPE_PARAMS = (
        "&" + "&".join(f"c={contract_choices[c]}" for c in selected_contracts)
        if selected_contracts
        else ""
    )

    sorting_choices = {"Date": "date", "Score": "relevance"}
    SORT_BY = questionary.select(
        "Sort jobs by:",
        choices=[
            Choice(title=label, value=code)
            for label, code in sorting_choices.items()
        ],
    ).ask()

    TIME_OUT = ask_timeout()

    # --- URLs ---
    LOGIN_URL = "https://www.hellowork.com/fr-fr/candidat/connexion-inscription.html#connexion"
    BASE_SEARCH_URL = (
        "https://www.hellowork.com/fr-fr/emploi/recherche.html?"
        f"k={encoded_keyword}"
        "&k_autocomplete=&l=France"
        "&l_autocomplete=http%3A%2F%2Fwww.rj.com%2Fcommun%2Flocalite%2Fpays%2FFR"
        f"&st={SORT_BY}"
        f"{CONTRACT_TYPE_PARAMS}"
        "&ray=all&d=all&p="
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

            accept_button = wait.until(
                EC.element_to_be_clickable((By.ID, "hw-cc-notice-accept-btn"))
            )
            accept_button.click()

            email_input = wait.until(
                EC.presence_of_element_located((By.NAME, "email2"))
            )
            email_input.clear()
            email_input.send_keys(EMAIL)

            password_input = wait.until(
                EC.presence_of_element_located((By.NAME, "password2"))
            )
            password_input.clear()
            password_input.send_keys(PASSWORD)

            login_button = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(text(), 'Je me connecte')]")
                )
            )
            login_button.click()

            # --- Verify login was successful ---
            # HelloWork redirects unauthenticated users back to connexion-inscription.
            # Navigate to the protected profile page and check the resulting URL.
            time.sleep(5)
            driver.get("https://www.hellowork.com/fr-fr/candidat/mon-profil.html")
            time.sleep(2)

            if "connexion" in driver.current_url.lower() or "login" in driver.current_url.lower():
                raise Exception(
                    f"Login rejected by HelloWork (redirected to: {driver.current_url}). "
                    "Check email/password in configs/config.json."
                )

            logging.info("HelloWork Session started — login verified.")
            print("HelloWork login successful.")


        except Exception:
            logging.exception("HelloWork login failed.")
            print("HelloWork login failed.")
            return  # Stop here — do not proceed with a dead browser session

        # --- Job search loop ---
        session_alive = True
        page = 1

        while session_alive:
            if time.time() - start_time > TIME_OUT:
                break

            try:
                driver.get(f"{BASE_SEARCH_URL}{page}")
                job_list = wait.until(
                    EC.presence_of_all_elements_located(
                        (By.XPATH, "//ul[@aria-label='liste des offres']/li")
                    )
                )
            except (InvalidSessionIdException, WebDriverException):
                logging.error("HelloWork: browser session lost during page navigation.")
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
                            (By.XPATH, "//ul[@aria-label='liste des offres']/li")
                        )
                    )
                    job = job_list[i]
                    driver.execute_script("arguments[0].scrollIntoView();", job)

                    job_link = job.find_element(
                        By.XPATH, ".//a[@data-cy='offerTitle']"
                    )
                    href = job_link.get_attribute("href")
                    driver.get(href)

                    # Navigate directly to the application section
                    current_url = driver.current_url
                    driver.get(current_url + "#postuler")
                    time.sleep(3)

                    try:
                        apply_button = wait.until(
                            EC.element_to_be_clickable(
                                (By.XPATH, "//button[@data-cy='submitButton']")
                            )
                        )
                        apply_button.click()
                        time.sleep(3)

                        # Check for a success confirmation before counting
                        try:
                            driver.find_element(
                                By.XPATH,
                                "//p[contains(text(), 'Félicitations ! Votre candidature')]",
                            )
                            applied_count += 1
                        except Exception:
                            logging.info(
                                "HelloWork: Skipped job index %d - Application not confirmed (may require extra steps or failed).", i
                            )
                    except TimeoutException:
                        logging.info(
                            "HelloWork: Skipped job index %d - No native apply button found (likely an external site).", i
                        )

                except (InvalidSessionIdException, WebDriverException):
                    logging.error(
                        "HelloWork: browser session died at job index %d, page %d. Stopping.", i, page
                    )
                    session_alive = False
                    break

                except Exception:
                    logging.exception(
                        "HelloWork: error on job index %d, page %d.", i, page
                    )

                finally:
                    if session_alive:
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
                                "HelloWork: browser session died while navigating back to list."
                            )
                            session_alive = False

            page += 1
            time.sleep(3)

    except Exception:
        logging.exception("HelloWork: unexpected error in main loop.")
        print("\nAn unexpected error occurred.")

    finally:
        logging.info(
            "HelloWork Session ended. Total jobs applied to: %d", applied_count
        )
        try:
            driver.quit()
        except Exception:
            pass
