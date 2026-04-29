import sqlite3
import os

def migrate_unique_url(db_path="history.db"):
    """Migration to add UNIQUE constraint to url column in job_applications."""
    if not os.path.exists(db_path):
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 1. Create temporary table with UNIQUE constraint
        cursor.execute("""
            CREATE TABLE job_applications_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER,
                job_id TEXT,
                url TEXT UNIQUE,
                title TEXT,
                company TEXT,
                state TEXT DEFAULT 'Discovered / Pending',
                ai_reason TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (run_id) REFERENCES runs (id)
            )
        """)

        # 2. Copy data (using INSERT OR IGNORE just in case duplicates still exist)
        cursor.execute("""
            INSERT OR IGNORE INTO job_applications_new 
            (id, run_id, job_id, url, title, company, state, ai_reason, timestamp)
            SELECT id, run_id, job_id, url, title, company, state, ai_reason, timestamp 
            FROM job_applications
        """)

        # 3. Drop old table
        cursor.execute("DROP TABLE job_applications")

        # 4. Rename new table
        cursor.execute("ALTER TABLE job_applications_new RENAME TO job_applications")

        conn.commit()
        print("Migration complete: UNIQUE constraint added to url column.")
    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_unique_url()
