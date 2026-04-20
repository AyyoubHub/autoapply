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
import json
import os

from utils import (
    load_config,
    create_driver,
    ask_timeout,
    load_jobteaser_search_config,
    build_jobteaser_search_url_from_profile,
)
from job_dossier_manager import save_job_dossier
from ai_agent import process_job_for_apply


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

            # Submit the form directly instead of finding the button
            password_input.submit()
            time.sleep(2)

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
                    
                    # Capture job metadata
                    job_title = "Unknown"
                    company_name = "Unknown"
                    try:
                        job_title = driver.find_element(By.CSS_SELECTOR, "[data-testid='jobad-DetailView__Heading__title']").text
                        company_name = driver.find_element(By.CSS_SELECTOR, "[data-testid='jobad-DetailView__Heading__company_name']").text
                    except Exception:
                        try:
                            # Fallback if data-testid is missing
                            job_title = driver.find_element(By.TAG_NAME, "h1").text
                            company_name = driver.find_element(By.XPATH, "//div[contains(@class, 'CompanyProfile_name')]").text
                        except Exception:
                            try:
                                company_name = driver.find_element(By.XPATH, "//a[contains(@href, '/companies/')]").text
                            except Exception:
                                pass

                    # Extract Job Description and About Company
                    try:
                        extraction_js = """
                        function parseStructure(container) {
                            if (!container) return null;
                            let structure = [];
                            // If it's a 'Read More' wrapper, use the content child
                            let target = container.querySelector('.Description_content__Ais4T') || container;
                            target.childNodes.forEach(node => {
                                if (node.nodeType === Node.ELEMENT_NODE) {
                                    let tag = node.tagName.toLowerCase();
                                    if (['h1', 'h2', 'h3', 'h4'].includes(tag)) {
                                        structure.push({ type: 'header', level: tag, text: node.innerText.trim() });
                                    } else if (tag === 'p' || tag === 'div' || tag === 'strong') {
                                        let text = node.innerText.trim();
                                        if (text) structure.push({ type: 'paragraph', text: text });
                                    } else if (tag === 'ul' || tag === 'ol') {
                                        let items = Array.from(node.querySelectorAll('li')).map(li => li.innerText.trim());
                                        if (items.length) structure.push({ type: 'list', tag: tag, items: items });
                                    } else {
                                        let text = node.innerText.trim();
                                        if (text) structure.push({ type: 'other', tag: tag, text: text });
                                    }
                                }
                            });
                            return structure;
                        }

                        // Try to click 'Voir plus' if present to expand description
                        let readMoreBtn = document.querySelector('[data-testid="jobad-DetailView__Description"] button');
                        if (readMoreBtn && readMoreBtn.innerText.toLowerCase().includes('voir')) {
                            readMoreBtn.click();
                        }

                        let descContainer = document.querySelector('[data-testid="jobad-DetailView__Description"]') || 
                                           document.querySelector('.job-description') || 
                                           document.querySelector('[data-testid="job-description-content"]');
                        let aboutContainer = document.querySelector('[data-testid="jobad-DetailView-CompanySection"]') || 
                                            document.querySelector('[data-testid="company-description"]') || 
                                            document.querySelector('.CompanyDescription_content') ||
                                            document.querySelector('.CompanyProfile_description');

                        return {
                            description: parseStructure(descContainer),
                            about_company: parseStructure(aboutContainer)
                        };
                        """
                        job_data = driver.execute_script(extraction_js)
                        
                        desc_storage_path = os.path.join(os.path.dirname(__file__), "../scratch/job_descriptions.json")
                        all_descriptions = {}
                        if os.path.exists(desc_storage_path):
                            try:
                                with open(desc_storage_path, "r", encoding="utf-8") as f:
                                    all_descriptions = json.load(f)
                            except Exception:
                                pass
                        
                        all_descriptions[href] = {
                            "title": job_title,
                            "company": company_name,
                            "url": href,
                            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                            "description_structure": job_data.get("description"),
                            "about_company_structure": job_data.get("about_company")
                        }
                        
                        with open(desc_storage_path, "w", encoding="utf-8") as f:
                            json.dump(all_descriptions, f, indent=2, ensure_ascii=False)
                        
                        logging.info("Extracted description and company info for: %s", job_title)
                        
                        # Save Job Dossier for AI/Automation
                        dossier_data = {
                            "url": href,
                            "title": job_title,
                            "company": company_name,
                            "description_structure": job_data.get("description"),
                            "about_company_structure": job_data.get("about_company")
                        }
                        save_job_dossier(dossier_data)
                        
                    except Exception as e:
                        logging.error("Failed to extract job description: %s", e)

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
                        time.sleep(2)  # Wait for modal to render
                        
                        # AUTOMATION: Call AI to prepare tailored CV and Message
                        ai_results = process_job_for_apply(href)
                        form_data = config.get("form_data", {})
                        
                        try:
                            # 1. Fill Textarea (Message/Cover Letter)
                            if ai_results and ai_results.get("message"):
                                try:
                                    message_area = wait.until(EC.presence_of_element_located((By.NAME, "coverLetterContent")))
                                    message_area.clear()
                                    message_area.send_keys(ai_results["message"])
                                    logging.info("AI-generated message injected.")
                                except Exception:
                                    logging.warning("Could not find coverLetterContent textarea.")

                            # 2. Fill Other Form Fields (Gender, Phone, etc.)
                            for field_name, value in form_data.items():
                                try:
                                    # Try by name first
                                    inputs = driver.find_elements(By.NAME, field_name)
                                    for inp in inputs:
                                        if inp.get_attribute("type") in ["text", "tel", "email"] and not inp.get_attribute("value"):
                                            inp.clear()
                                            inp.send_keys(value)
                                        elif inp.get_attribute("type") == "hidden" and not inp.get_attribute("value"):
                                            driver.execute_script("arguments[0].value = arguments[1]", inp, value)
                                except Exception:
                                    pass

                            # 3. Handle File Upload (Adapted CV)
                            if ai_results:
                                try:
                                    # Prioritize PDF if compilation was successful, otherwise fallback to .tex
                                    file_to_upload = ai_results.get("pdf_path") or ai_results.get("cv_path")
                                    if file_to_upload and os.path.exists(file_to_upload):
                                        file_input = driver.find_element(By.NAME, "resume")
                                        # Force it to be visible if it is hidden
                                        driver.execute_script("arguments[0].style.display = 'block'; arguments[0].style.visibility = 'visible';", file_input)
                                        file_input.send_keys(os.path.abspath(file_to_upload))
                                        logging.info("Tailored resume uploaded: %s", os.path.basename(file_to_upload))
                                    else:
                                        logging.warning("No resume file found for upload.")
                                except Exception as e:
                                    logging.warning("Resume upload failed: %s", e)

                        except Exception as e:
                            logging.error("Error during automated form filling: %s", e)
                        

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
