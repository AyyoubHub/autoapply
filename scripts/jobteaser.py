import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import InvalidSessionIdException, WebDriverException
import time
import urllib.parse
import logging
import questionary

from utils import load_config, create_driver, ask_timeout


def run() -> None:
    # --- Configuration & user input ---
    config = load_config()
    EMAIL = config["email"]
    PASSWORD = config["jobteaser_password"]

    KEYWORD = questionary.text("Enter the job keyword:").ask()
    encoded_keyword = urllib.parse.quote_plus(KEYWORD)

    TIME_OUT = ask_timeout()

    # --- URLs ---
    # Navigate to the main sign-in page and let the OAuth flow start naturally,
    # instead of hardcoding a URL with a stale nonce/state token.
    LOGIN_URL = "https://www.jobteaser.com/fr/sign-in"
    BASE_SEARCH_URL = (
        "https://www.jobteaser.com/fr/job-offers?"
        f"candidacy_type=INTERNAL&q={encoded_keyword}&sort=recency&page="
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
                EC.element_to_be_clickable((By.ID, "didomi-notice-agree-button"))
            )
            accept_button.click()

            email_input = wait.until(
                EC.presence_of_element_located((By.ID, "email"))
            )
            email_input.clear()
            email_input.send_keys(EMAIL)

            password_input = wait.until(
                EC.presence_of_element_located((By.ID, "passwordInput"))
            )
            password_input.clear()
            password_input.send_keys(PASSWORD)

            login_button = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(text(), 'Connexion')]")
                )
            )
            login_button.click()

            connect_button = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//a[contains(text(), 'JobTeaser Connect')]")
                )
            )
            connect_button.click()

            # --- Verify login was successful ---
            # JobTeaser redirects unauthenticated users back to sign-in.
            # Navigate to the protected dashboard and check the resulting URL.
            time.sleep(3)
            driver.get("https://www.jobteaser.com/fr/dashboard")
            time.sleep(2)

            if "sign-in" in driver.current_url.lower() or "login" in driver.current_url.lower():
                raise Exception(
                    f"Login rejected by JobTeaser (redirected to: {driver.current_url}). "
                    "Check email/password in configs/config.json."
                )

            logging.info("JobTeaser Session started — login verified.")
            print("JobTeaser login successful.")


        except Exception:
            logging.exception("JobTeaser login failed.")
            print("JobTeaser login failed.")
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
                        (By.XPATH, "//ul[@class='PageContent_results__zSSNO']/li")
                    )
                )
            except (InvalidSessionIdException, WebDriverException):
                logging.error("JobTeaser: browser session lost during page navigation.")
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
                            (By.XPATH, "//ul[@class='PageContent_results__zSSNO']/li")
                        )
                    )
                    job = job_list[i]
                    driver.execute_script("arguments[0].scrollIntoView();", job)

                    job_link = job.find_element(
                        By.XPATH, ".//a[@class='JobAdCard_link__n5lkb']"
                    )
                    href = job_link.get_attribute("href")
                    driver.get(href)
                    time.sleep(2)

                    try:
                        apply_button = wait.until(
                            EC.element_to_be_clickable(
                                (By.XPATH, "//button[@data-testid='jobad-DetailView__CandidateActions__Buttons_apply_internal_candidacy']")
                            )
                        )
                        apply_button.click()
                        time.sleep(1)

                        apply_button2 = wait.until(
                            EC.element_to_be_clickable(
                                (By.XPATH, "//button[@data-testid='jobad-DetailView__ApplicationFlow__Buttons__apply_button']")
                            )
                        )
                        apply_button2.click()
                        time.sleep(3)

                        # Check for a success confirmation before counting
                        try:
                            driver.find_element(
                                By.XPATH,
                                "//div[@data-testid='jobad-DetailView__ApplicationFlow__Success']",
                            )
                            applied_count += 1
                        except Exception:
                            logging.info(
                                "JobTeaser: Skipped job index %d - Application not confirmed (may require extra steps or failed).", i
                            )
                    except TimeoutException:
                        logging.info(
                            "JobTeaser: Skipped job index %d - No native apply button found (likely an external site).", i
                        )

                except (InvalidSessionIdException, WebDriverException):
                    logging.error(
                        "JobTeaser: browser session died at job index %d, page %d. Stopping.", i, page
                    )
                    session_alive = False
                    break

                except Exception:
                    logging.exception(
                        "JobTeaser: error on job index %d, page %d.", i, page
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
                                "JobTeaser: browser session died while navigating back to list."
                            )
                            session_alive = False

            page += 1
            time.sleep(3)

    except Exception:
        logging.exception("JobTeaser: unexpected error in main loop.")
        print("\nAn unexpected error occurred.")

    finally:
        logging.info(
            "JobTeaser Session ended. Total jobs applied to: %d", applied_count
        )
        print(f"\nJobTeaser Session ended. Total jobs applied to: {applied_count}")
        try:
            driver.quit()
        except Exception:
            pass