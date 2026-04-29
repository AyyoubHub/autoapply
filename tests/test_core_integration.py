import unittest
from unittest.mock import MagicMock, patch
import os
import sys
import sqlite3

# Add project root and scripts to path
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _ROOT not in sys.path:
    sys.path.append(_ROOT)
_SCRIPTS = os.path.join(_ROOT, 'scripts')
if _SCRIPTS not in sys.path:
    sys.path.append(_SCRIPTS)

from scripts.db_manager import DBManager

class TestCoreIntegration(unittest.TestCase):
    def setUp(self):
        self.db_path = "test_integration.db"
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        self.db = DBManager(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    @patch('apec.check_and_prompt_apec_config')
    @patch('apec.create_driver')
    @patch('apec.WebDriverWait')
    @patch('apec.is_high_quality_match')
    @patch('questionary.text')
    def test_simulated_run_lifecycle(self, mock_text, mock_ai, mock_wait, mock_driver, mock_config):
        """Simulate an APEC run and verify DB tracking."""
        import apec
        # Setup mocks
        mock_config.return_value = {"apec_email": "test@test.com", "apec_password": "pass"}
        mock_text.return_value.ask.return_value = "Python"
        mock_ai.return_value = (True, "Good match")
        
        # We need to mock the run() in apec.py or similar
        # For this test, we'll verify that DBManager methods are called as expected
        # if they were integrated into the workflow.
        
        # 1. Start Run
        run_id = self.db.start_run(platform="APEC", keywords="Python")
        self.assertIsNotNone(run_id)
        
        # 2. Discover Job
        app_id = self.db.add_job_application(
            run_id, 
            job_id="apec_123", 
            url="http://apec.fr/job1", 
            title="Dev", 
            company="DevCo"
        )
        job = self.db.get_job_application(app_id)
        self.assertEqual(job['state'], "Discovered / Pending")
        
        # 3. AI Filter (Simulated)
        relevant, reason = mock_ai("Dev", "Desc", ["Python"])
        if relevant:
            self.db.update_job_state(app_id, "Applied Successfully")
        else:
            self.db.update_job_state(app_id, "AI Filtered / Rejected", ai_reason=reason)
            
        job = self.db.get_job_application(app_id)
        self.assertEqual(job['state'], "Applied Successfully")
        
        # 4. Finish Run
        self.db.finish_run(run_id, total_found=1, total_applied=1)
        run = self.db.get_run(run_id)
        self.assertEqual(run['status'], "completed")
        self.assertEqual(run['total_applied'], 1)

if __name__ == '__main__':
    unittest.main()
