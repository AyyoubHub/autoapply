from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    InvalidSessionIdException,
    WebDriverException,
    TimeoutException,
)
import time
import logging
import questionary

from utils import (
    load_config,
    create_driver,
    ask_timeout,
    load_jobteaser_search_config,
    build_jobteaser_search_url_from_profile,
)


def run() -> None:
    config = load_config()
    EMAIL = config["email"]
    PASSWORD = config["jobteaser_password"]

    profile = load_jobteaser_search_config()
    kw_default = (profile.get("keyword") or "").strip()
    keyword = (
        questionary.text("Enter the job keyword:", default=kw_default).ask() or ""
    ).strip()
    if not keyword:
        keyword = (questionary.text("Enter the job keyword (required):").ask() or "").strip()
    if not keyword:
        print("No keyword — exiting.")
        return

    BASE_SEARCH_URL = build_jobteaser_search_url_from_profile(profile, keyword)

    logging.info(
        "JobTeaser: candidature simplifiée only (candidacy_type=INTERNAL). URL prefix: %s",
        BASE_SEARCH_URL,
    )
    print("Search: candidature simplifiée / easy apply only (INTERNAL).")

    td = profile.get("timeout_minutes")
    timeout_default = float(td) if td is not None else None
    TIME_OUT = ask_timeout(timeout_default)

    LOGIN_URL = "https://www.jobteaser.com/fr/users/sign_in"
    CONNECT_URL = "https://www.jobteaser.com/users/auth/connect"

    driver = create_driver()
    wait = WebDriverWait(driver, 10)

    applied_count = 0
    processed_count = 0
    start_time = time.time()

    try:
        try:
            driver.get(LOGIN_URL)

            try:
                accept_button = wait.until(
                    EC.element_to_be_clickable((By.ID, "didomi-notice-agree-button"))
                )
                accept_button.click()
            except TimeoutException:
                pass

            driver.get(CONNECT_URL)

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
            return

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
                break

            if not job_list:
                break

            for i in range(len(job_list)):
                if time.time() - start_time > TIME_OUT or not session_alive:
                    break

                try:
                    job_list = wait.until(
                        EC.presence_of_all_elements_located(
                            (By.XPATH, "//ul[@class='PageContent_results__zSSNO']/li")
                        )
                    )
                    job = job_list[i]
                    driver.execute_script("arguments[0].scrollIntoView();", job)

                    job_link = job.find_element(
                        By.XPATH, ".//a[contains(@href, '/job-offers/')]"
                    )
                    href = job_link.get_attribute("href").split("?")[0]
                    driver.get(href)
                    time.sleep(2)

                    time.sleep(1)
                    already_applied = driver.find_elements(
                        By.XPATH,
                        "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'candidature envoyée') or "
                        "contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'candidature envoyee')]",
                    )
                    if any(el.is_displayed() for el in already_applied):
                        logging.info(
                            "JobTeaser: Skipped job index %d - Already applied ('Candidature envoyée').",
                            i,
                        )
                        continue

                    try:
                        apply_button = wait.until(
                            EC.element_to_be_clickable(
                                (
                                    By.XPATH,
                                    "//button[@data-testid='jobad-DetailView__CandidateActions__Buttons_apply_internal_candidacy']",
                                )
                            )
                        )
                        apply_button.click()
                        time.sleep(1)

                        apply_button2 = wait.until(
                            EC.element_to_be_clickable(
                                (
                                    By.XPATH,
                                    "//button[@data-testid='jobad-DetailView__ApplicationFlow__Buttons__apply_button']",
                                )
                            )
                        )
                        apply_button2.click()
                        time.sleep(3)

                        try:
                            driver.find_element(
                                By.XPATH,
                                "//div[@data-testid='jobad-DetailView__ApplicationFlow__Success']",
                            )
                            applied_count += 1
                        except Exception:
                            logging.info(
                                "JobTeaser: Skipped job index %d - Application not confirmed (may require extra steps or failed).",
                                i,
                            )
                    except TimeoutException:
                        logging.info(
                            "JobTeaser: Skipped job index %d - No native apply button found (likely an external site).",
                            i,
                        )

                except (InvalidSessionIdException, WebDriverException):
                    logging.error(
                        "JobTeaser: browser session died at job index %d, page %d. Stopping.",
                        i,
                        page,
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
