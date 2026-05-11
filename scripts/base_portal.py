import logging
import time
from abc import ABC, abstractmethod
from typing import Optional, Tuple, List, Dict, Any

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    InvalidSessionIdException,
    WebDriverException,
    NoSuchElementException,
    ElementClickInterceptedException,
)

from db_manager import DBManager
from utils import create_driver
from ai_agent import is_high_quality_match


class BaseJobPortal(ABC):
    """
    Base class for automated job portals.
    Encapsulates standard execution loops, error handling,
    database integration, and wait strategies.
    """

    def __init__(self, platform_name: str, force_reprocess: bool = False):
        self.platform_name = platform_name
        self.force_reprocess = force_reprocess
        
        self.db = DBManager()
        self.run_id = None
        self.driver = None
        self.wait = None
        
        # Stats tracking
        self.total_unique = 0
        self.processed_count = 0
        self.applied_count = 0
        self.ai_rejected_count = 0
        self.already_applied_count = 0
        self.external_count = 0
        self.irrelevant_count = 0
        self.failed_count = 0

    # --- Standard Execution Flow ---
    
    def run_portal(self, keywords: List[str]):
        """Main execution loop for a portal."""
        keyword_str = ", ".join(keywords) if isinstance(keywords, list) else keywords
        self.run_id = self.db.start_run(platform=self.platform_name, keywords=keyword_str)
        
        try:
            self.setup_browser()
            
            # Subclass implementation
            self.authenticate()
            
            jobs = self.discover_jobs(keywords)
            self.total_unique = len(jobs)
            
            if self.total_unique > 0:
                print(f"\n{'─' * 50}\nStarting applications (total jobs: {self.total_unique})...\n{'─' * 50}", flush=True)
                self.process_jobs(jobs, keywords)
                
        except Exception as e:
            logging.exception(f"[{self.platform_name}] Unexpected fatal error.")
            print(f"\nAn unexpected fatal error occurred: {e}")
        finally:
            self.print_summary()
            if self.run_id:
                self.db.finish_run(self.run_id, total_found=self.total_unique, total_applied=self.applied_count)
            self.teardown_browser()

    def process_jobs(self, jobs: List[Dict[str, Any]], keywords: List[str]):
        """Iterate over job dicts. Each must at least have 'href'."""
        for job in jobs:
            href = job.get('href')
            if not href:
                continue
                
            self.processed_count += 1
            
            # Skip check
            if not self.force_reprocess and self.db.should_skip(href):
                logging.info(f"[{self.platform_name}] Skipped job {self.processed_count} - Already processed (in DB).")
                print(f"\r{' '*80}\r[Skipped] Already processed (in DB): {href.split('/')[-1]}")
                self.already_applied_count += 1
                continue
                
            status = self.process_single_job_with_retries(job, keywords)
            
            if status == "applied":
                self.applied_count += 1
            elif status == "ai_rejected":
                self.ai_rejected_count += 1
            elif status == "already_applied":
                self.already_applied_count += 1
            elif status == "external":
                self.external_count += 1
            elif status == "irrelevant":
                self.irrelevant_count += 1
            elif status == "failed":
                self.failed_count += 1

            print(
                f"\rJobs: {self.processed_count}/{self.total_unique} | "
                f"Applied: {self.applied_count} | "
                f"External: {self.external_count} | "
                f"AI Rej: {self.ai_rejected_count} | "
                f"Already: {self.already_applied_count} | "
                f"Irrev: {self.irrelevant_count} | "
                f"Fail: {self.failed_count}   ",
                end="",
                flush=True,
            )

    def process_single_job_with_retries(self, job: Dict[str, Any], keywords: List[str], max_retries: int = 1) -> str:
        """Process a single job, with a retry loop for transient browser crashes."""
        status = "failed"
        
        for attempt in range(max_retries + 1):
            if not self.ensure_session_alive():
                return "failed"
                
            try:
                status = self.apply_to_job(job, keywords)
                break
            except (InvalidSessionIdException, WebDriverException) as e:
                logging.error(f"[{self.platform_name}] Browser session died on job {self.processed_count} (attempt {attempt + 1}).")
                self.teardown_browser() # Will force recreation in next loop
                if attempt == max_retries:
                    status = "failed"
            except Exception as e:
                logging.warning(f"[{self.platform_name}] Job {self.processed_count} failed (attempt {attempt + 1}): {e}")
                status = "failed"
                break
                
        return status

    # --- Abstract Methods (Subclasses must implement) ---

    @abstractmethod
    def authenticate(self):
        """Perform platform login."""
        pass
        
    @abstractmethod
    def discover_jobs(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """Return a list of dictionaries, each containing at least 'href'."""
        pass
        
    @abstractmethod
    def apply_to_job(self, job: Dict[str, Any], keywords: List[str]) -> str:
        """
        Process the job. Return one of:
        'applied', 'already_applied', 'irrelevant', 'external', 'ai_rejected', 'failed'
        """
        pass

    # --- Shared Utilities ---
    
    def setup_browser(self):
        self.driver = create_driver()
        self.wait = WebDriverWait(self.driver, 10)
        
    def teardown_browser(self):
        try:
            if self.driver:
                self.driver.quit()
        except Exception:
            pass
        finally:
            self.driver = None
            self.wait = None
            
    def ensure_session_alive(self) -> bool:
        """Checks if the browser is responsive. If not, attempts a full recovery."""
        needs_recovery = False

        if not self.driver or not self.wait:
            needs_recovery = True
        else:
            try:
                _ = self.driver.current_url
            except Exception:
                needs_recovery = True

        if needs_recovery:
            logging.warning(
                "[%s] Browser session unresponsive or dead. Attempting recovery...",
                self.platform_name,
            )
            self.teardown_browser()
            try:
                self.setup_browser()
                self.authenticate()
                logging.info("[%s] Browser session recovered successfully.", self.platform_name)
                return True
            except Exception as e:
                logging.error(
                    "[%s] Failed to recover browser session: %s",
                    self.platform_name, e,
                )
                return False
        return True

    def evaluate_ai_match(self, job_title: str, job_desc: str, keywords: List[str], app_id: int = None) -> Tuple[bool, str]:
        """Wrapper for AI evaluation that handles state tracking."""
        try:
            is_match, reason = is_high_quality_match(job_title, job_desc, keywords)
            if not is_match:
                logging.info(f"[{self.platform_name}] AI rejected relevance (Title: '{job_title}'). Reason: {reason}")
                print(f"\n  [AI Skip] {reason}")
                if app_id:
                    self.db.update_job_state(app_id, "AI Filtered / Rejected", ai_reason=reason)
            return is_match, reason
        except Exception as e:
            logging.warning(f"AI check failed, proceeding with basic keyword match: {e}")
            return True, str(e)
            
    def print_summary(self):
        print(
            f"\n\n{'─' * 50}\n"
            f"{self.platform_name.upper()} RUN COMPLETE\n"
            f"{'─' * 50}\n"
            f"Total Unique Jobs    : {self.total_unique}\n"
            f"Successfully Applied : {self.applied_count}\n"
            f"External (skipped)   : {self.external_count}\n"
            f"AI Relevance Reject  : {self.ai_rejected_count}\n"
            f"Already Applied      : {self.already_applied_count}\n"
            f"Irrelevant (skipped) : {self.irrelevant_count}\n"
            f"Failed / System Skip : {self.failed_count}\n"
            f"{'─' * 50}\n"
        )
        
    # --- Selenium Wait Wrappers ---
    
    def wait_for_clickable(self, locator: tuple, timeout: int = 10):
        wait = WebDriverWait(self.driver, timeout)
        return wait.until(EC.element_to_be_clickable(locator))

    def wait_for_presence(self, locator: tuple, timeout: int = 10):
        wait = WebDriverWait(self.driver, timeout)
        return wait.until(EC.presence_of_element_located(locator))

    def wait_for_all_presence(self, locator: tuple, timeout: int = 10):
        wait = WebDriverWait(self.driver, timeout)
        return wait.until(EC.presence_of_all_elements_located(locator))

    def wait_for_visible(self, locator: tuple, timeout: int = 10):
        """Wait until the element is visible (in DOM *and* displayed)."""
        wait = WebDriverWait(self.driver, timeout)
        return wait.until(EC.visibility_of_element_located(locator))

    def _dismiss_cookie_banner(self) -> None:
        """Dismiss the Didomi cookie consent banner if it is present.

        Safe to call unconditionally — silently no-ops when the banner
        has already been dismissed or is not present on the page.
        """
        try:
            btn = self.driver.find_element(By.ID, "didomi-notice-agree-button")
            btn.click()
            logging.debug("[%s] Cookie banner dismissed.", self.platform_name)
        except Exception:
            pass  # Banner not present — perfectly normal

