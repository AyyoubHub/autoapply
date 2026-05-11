"""
test_core_integration.py

Integration tests that verify the full DB state lifecycle without a browser.
Portal-level tests (which require undetected-chromedriver) live in
test_portal_flow.py and only run inside the project virtualenv.
"""

import unittest
import os
import sys
import gc

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_SCRIPTS = os.path.join(_ROOT, "scripts")
for _p in (_ROOT, _SCRIPTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from scripts.db_manager import DBManager


def _make_db(name="test_integration.db"):
    path = os.path.join(os.path.dirname(__file__), name)
    if os.path.exists(path):
        os.remove(path)
    return DBManager(path), path


class TestRunLifecycle(unittest.TestCase):
    def setUp(self):
        self.db, self.db_path = _make_db()

    def tearDown(self):
        self.db = None
        gc.collect()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_full_run_flow(self):
        """Start run → add job → update state → finish run → verify all."""
        run_id = self.db.start_run(platform="APEC", keywords="Python")
        self.assertIsNotNone(run_id)

        run = self.db.get_run(run_id)
        self.assertEqual(run["platform"], "APEC")
        self.assertEqual(run["status"], "in_progress")

        app_id = self.db.add_job_application(
            run_id, "job_abc", "https://apec.fr/job/abc", "Dev Python", "TechCorp"
        )
        self.assertIsNotNone(app_id)

        job = self.db.get_job_application(app_id)
        self.assertEqual(job["state"], "Discovered / Pending")

        self.db.update_job_state(app_id, "Applied Successfully")
        job = self.db.get_job_application(app_id)
        self.assertEqual(job["state"], "Applied Successfully")

        self.db.finish_run(run_id, total_found=1, total_applied=1)
        run = self.db.get_run(run_id)
        self.assertEqual(run["status"], "completed")
        self.assertEqual(run["total_applied"], 1)

    def test_ai_rejected_skipped_on_next_run(self):
        """AI-rejected jobs must be skipped (should_skip returns True)."""
        run_id = self.db.start_run(platform="APEC", keywords="Python")
        app_id = self.db.add_job_application(
            run_id, "job_x", "https://apec.fr/job/x", "Irrelevant", "Co"
        )
        self.db.update_job_state(app_id, "AI Filtered / Rejected", ai_reason="Off-topic")
        self.assertTrue(self.db.should_skip("https://apec.fr/job/x"))

    def test_failed_job_not_skipped(self):
        """Failed jobs must NOT be skipped — they should be retried."""
        run_id = self.db.start_run(platform="APEC", keywords="Python")
        app_id = self.db.add_job_application(
            run_id, "job_y", "https://apec.fr/job/y", "DevOps", "Corp"
        )
        self.db.update_job_state(app_id, "Application Failed")
        self.assertFalse(self.db.should_skip("https://apec.fr/job/y"))

    def test_duplicate_url_returns_same_id(self):
        """INSERT OR IGNORE: duplicate URLs silently return the first row's ID."""
        run_id = self.db.start_run(platform="JobTeaser", keywords="DevOps")
        id1 = self.db.add_job_application(
            run_id, "jt_1", "https://jt.com/offer/1", "SRE", "Acme"
        )
        id2 = self.db.add_job_application(
            run_id, "jt_2", "https://jt.com/offer/1", "Other", "OtherCo"
        )
        self.assertEqual(id1, id2)
        job = self.db.get_job_application(id1)
        self.assertEqual(job["title"], "SRE")  # Original title preserved

    def test_external_job_not_in_skip_set(self):
        """External jobs should be retried on subsequent runs."""
        run_id = self.db.start_run(platform="APEC", keywords="Python")
        app_id = self.db.add_job_application(
            run_id, "ext_1", "https://apec.fr/job/ext", "Ext Dev", "ExtCo"
        )
        self.db.update_job_state(app_id, "External")
        self.assertFalse(self.db.should_skip("https://apec.fr/job/ext"))

    def test_already_applied_in_skip_set(self):
        """'Already Applied' state must also be skipped."""
        run_id = self.db.start_run(platform="JobTeaser", keywords="DevOps")
        app_id = self.db.add_job_application(
            run_id, "jt_aa", "https://jt.com/offer/aa", "SRE", "Acme"
        )
        self.db.update_job_state(app_id, "Already Applied")
        self.assertTrue(self.db.should_skip("https://jt.com/offer/aa"))


if __name__ == "__main__":
    unittest.main()
