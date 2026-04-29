import sqlite3
from datetime import datetime
import os
try:
    from zoneinfo import ZoneInfo
except ImportError:
    # Fallback for very old python, but user has 3.11
    # On Windows, you might need 'pip install tzdata'
    from backports.zoneinfo import ZoneInfo

class DBManager:
    def __init__(self, db_path=None):
        self.tz = ZoneInfo("Europe/Paris")
        if db_path is None:
            # Place history.db in the project root relative to this script
            db_path = os.path.join(os.path.dirname(__file__), "..", "history.db")
        self.db_path = os.path.abspath(db_path)
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initialize database tables."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Create Runs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    keywords TEXT,
                    platform TEXT,
                    status TEXT DEFAULT 'in_progress',
                    total_found INTEGER DEFAULT 0,
                    total_applied INTEGER DEFAULT 0
                )
            """)
            
            # Create JobApplications table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS job_applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER,
                    job_id TEXT,
                    url TEXT UNIQUE,
                    title TEXT,
                    company TEXT,
                    state TEXT DEFAULT 'Discovered / Pending',
                    ai_reason TEXT,
                    timestamp TIMESTAMP,
                    FOREIGN KEY (run_id) REFERENCES runs (id)
                )
            """)
            conn.commit()

    def _get_now(self):
        """Get current time in Paris timezone."""
        return datetime.now(self.tz).isoformat()

    def start_run(self, platform, keywords):
        """Start a new script run."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO runs (platform, keywords, start_time) VALUES (?, ?, ?)",
                (platform, keywords, self._get_now())
            )
            return cursor.lastrowid

    def finish_run(self, run_id, total_found=0, total_applied=0):
        """Finalize a run with stats."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE runs SET end_time = ?, status = 'completed', total_found = ?, total_applied = ? WHERE id = ?",
                (self._get_now(), total_found, total_applied, run_id)
            )

    def get_run(self, run_id):
        """Retrieve run details."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def add_job_application(self, run_id, job_id, url, title, company):
        """Add a new job application record. Returns row ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO job_applications (run_id, job_id, url, title, company, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                (run_id, job_id, url, title, company, self._get_now())
            )
            if cursor.lastrowid:
                return cursor.lastrowid
            
            # If not inserted, fetch existing ID
            cursor.execute("SELECT id FROM job_applications WHERE url = ?", (url,))
            row = cursor.fetchone()
            return row[0] if row else None

    def update_job_state(self, app_id, state, ai_reason=None):
        """Update the state and optionally the AI reason of a job application."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if ai_reason:
                cursor.execute(
                    "UPDATE job_applications SET state = ?, ai_reason = ? WHERE id = ?",
                    (state, ai_reason, app_id)
                )
            else:
                cursor.execute(
                    "UPDATE job_applications SET state = ? WHERE id = ?",
                    (state, app_id)
                )

    def get_job_application(self, app_id):
        """Retrieve job application details."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM job_applications WHERE id = ?", (app_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def is_applied(self, url):
        """Check if a URL has already been successfully applied to (any platform)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # We consider a job applied if it's in state 'Applied Successfully' or 'Already Applied'
            cursor.execute(
                "SELECT 1 FROM job_applications WHERE url = ? AND state IN ('Applied Successfully', 'Already Applied')",
                (url,)
            )
            return cursor.fetchone() is not None

    def should_skip(self, url):
        """Check if a URL should be skipped based on terminal states."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Skip if successfully applied OR AI rejected (terminal states)
            cursor.execute(
                "SELECT 1 FROM job_applications WHERE url = ? AND state IN ('Applied Successfully', 'Already Applied', 'AI Filtered / Rejected')",
                (url,)
            )
            return cursor.fetchone() is not None

if __name__ == "__main__":
    # Simple manual verification
    db = DBManager("manual_test.db")
    run_id = db.start_run("TEST", "manual, test")
    print(f"Started run: {run_id}")
    app_id = db.add_job_application(run_id, "test_1", "http://test.com", "Tester", "Test Co")
    print(f"Added job: {app_id}")
    db.update_job_state(app_id, "Applied Successfully")
    db.finish_run(run_id, 1, 1)
    print("Manual test complete. Check manual_test.db")
