import sqlite3
import os
import logging

def deduplicate(db_path="history.db"):
    """Remove duplicate job applications based on URL, keeping the first one."""
    if not os.path.exists(db_path):
        print(f"Database {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Find duplicates and keep the minimum ID
        cursor.execute("""
            DELETE FROM job_applications
            WHERE id NOT IN (
                SELECT MIN(id)
                FROM job_applications
                GROUP BY url
            )
        """)
        rows_deleted = conn.total_changes
        conn.commit()
        print(f"Deduplication complete. Removed {rows_deleted} duplicate entries.")
        logging.info("Deduplication complete. Removed %d duplicate entries.", rows_deleted)
    except Exception as e:
        print(f"Deduplication failed: {e}")
        logging.error("Deduplication failed: %s", e)
    finally:
        conn.close()

if __name__ == "__main__":
    deduplicate()
