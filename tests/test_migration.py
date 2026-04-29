import unittest
import json
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

class TestMigration(unittest.TestCase):
    def setUp(self):
        self.db_path = "test_migration.db"
        self.apec_json = "test_apec_applied.json"
        self.ext_json = "test_external_applied.json"
        
        if os.path.exists(self.db_path): os.remove(self.db_path)
        if os.path.exists(self.apec_json): os.remove(self.apec_json)
        if os.path.exists(self.ext_json): os.remove(self.ext_json)
        
        self.db = DBManager(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path): os.remove(self.db_path)
        if os.path.exists(self.apec_json): os.remove(self.apec_json)
        if os.path.exists(self.ext_json): os.remove(self.ext_json)

    def test_migration_logic(self):
        # 1. Create mock JSON data
        apec_data = ["https://apec.fr/job1", "https://apec.fr/job2"]
        ext_data = {
            "ext_1": {"url": "https://comp.com/1", "title": "Dev", "company": "Co1"},
            "ext_2": {"url": "https://comp.com/2", "title": "Sec", "company": "Co2"}
        }
        
        with open(self.apec_json, "w") as f: json.dump(apec_data, f)
        with open(self.ext_json, "w") as f: json.dump(ext_data, f)
        
        # 2. Run migration (imported locally to avoid early failure)
        try:
            from scripts.migrate_history import migrate
            migrate(self.db, self.apec_json, self.ext_json)
        except ImportError:
            self.skipTest("migrate_history.py not implemented yet")

        # 3. Verify DB
        run = self.db.get_run(1)
        self.assertEqual(run['platform'], "Legacy Migration")
        
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT count(*) FROM job_applications WHERE state='Applied Successfully'")
            self.assertEqual(cursor.fetchone()[0], 2) # APEC jobs
            
            cursor.execute("SELECT count(*) FROM job_applications WHERE state='External'")
            self.assertEqual(cursor.fetchone()[0], 2) # External jobs

if __name__ == '__main__':
    unittest.main()
