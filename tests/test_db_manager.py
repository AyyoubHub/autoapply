import unittest
import sqlite3
import os
import sys
from datetime import datetime

# Add scripts directory to path
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _ROOT not in sys.path:
    sys.path.append(_ROOT)
_SCRIPTS = os.path.join(_ROOT, 'scripts')
if _SCRIPTS not in sys.path:
    sys.path.append(_SCRIPTS)

try:
    from scripts.db_manager import DBManager
except ImportError:
    # This is expected to fail in the Red phase
    DBManager = None

class TestDBManager(unittest.TestCase):
    def setUp(self):
        self.db_path = "test_history.db"
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        
        if DBManager is None:
            self.skipTest("DBManager not implemented yet")
            
        self.manager = DBManager(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_initialization(self):
        """Test tables are created."""
        self.assertTrue(os.path.exists(self.db_path))
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check Runs table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='runs'")
        self.assertIsNotNone(cursor.fetchone())
        
        # Check JobApplications table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='job_applications'")
        self.assertIsNotNone(cursor.fetchone())
        conn.close()

    def test_run_crud(self):
        """Test creating and finishing runs."""
        run_id = self.manager.start_run(platform="APEC", keywords="Python, AI")
        self.assertIsInstance(run_id, int)
        
        run = self.manager.get_run(run_id)
        self.assertEqual(run['platform'], "APEC")
        self.assertEqual(run['keywords'], "Python, AI")
        self.assertEqual(run['status'], "in_progress")
        
        self.manager.finish_run(run_id, total_found=10, total_applied=5)
        run = self.manager.get_run(run_id)
        self.assertEqual(run['status'], "completed")
        self.assertEqual(run['total_found'], 10)
        self.assertEqual(run['total_applied'], 5)
        self.assertIsNotNone(run['end_time'])

    def test_job_application_crud(self):
        """Test adding and updating job states."""
        run_id = self.manager.start_run(platform="APEC", keywords="Python")
        
        job_data = {
            "job_id": "apec_123",
            "url": "https://example.com/job",
            "title": "Software Engineer",
            "company": "Tech Corp"
        }
        
        app_id = self.manager.add_job_application(run_id, **job_data)
        self.assertIsInstance(app_id, int)
        
        # Check state update
        self.manager.update_job_state(app_id, "Applied Successfully")
        job = self.manager.get_job_application(app_id)
        self.assertEqual(job['state'], "Applied Successfully")
        
        # Check AI reason update
        self.manager.update_job_state(app_id, "AI Filtered / Rejected", ai_reason="Low relevance score")
        job = self.manager.get_job_application(app_id)
        self.assertEqual(job['state'], "AI Filtered / Rejected")
        self.assertEqual(job['ai_reason'], "Low relevance score")

    def test_should_skip(self):
        """Test the should_skip logic."""
        run_id = self.manager.start_run(platform="APEC", keywords="Python")
        
        # 1. Successful job -> should skip
        app_id = self.manager.add_job_application(run_id, "job1", "url1", "Title", "Co")
        self.manager.update_job_state(app_id, "Applied Successfully")
        self.assertTrue(self.manager.should_skip("url1"))
        
        # 2. AI Rejected job -> should skip
        app_id2 = self.manager.add_job_application(run_id, "job2", "url2", "Title", "Co")
        self.manager.update_job_state(app_id2, "AI Filtered / Rejected")
        self.assertTrue(self.manager.should_skip("url2"))
        
        # 3. Failed job -> should NOT skip
        app_id3 = self.manager.add_job_application(run_id, "job3", "url3", "Title", "Co")
        self.manager.update_job_state(app_id3, "Application Failed")
        self.assertFalse(self.manager.should_skip("url3"))

    def test_unique_url(self):
        """Test that duplicate URLs are handled gracefully."""
        run_id = self.manager.start_run(platform="APEC", keywords="Python")
        
        id1 = self.manager.add_job_application(run_id, "job1", "url_unique", "Title", "Co")
        id2 = self.manager.add_job_application(run_id, "job2", "url_unique", "Other", "OtherCo")
        
        self.assertEqual(id1, id2)
        job = self.manager.get_job_application(id1)
        self.assertEqual(job['title'], "Title") # Original preserved

if __name__ == '__main__':
    unittest.main()
