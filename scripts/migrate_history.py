import json
import os
import logging
from db_manager import DBManager

def migrate(db, apec_path, ext_path):
    """Migrate legacy JSON history to SQLite."""
    run_id = db.start_run(platform="Legacy Migration", keywords="N/A")
    total_found = 0
    total_applied = 0

    # 1. APEC JSON (List of URLs)
    if os.path.exists(apec_path):
        try:
            with open(apec_path, "r", encoding="utf-8") as f:
                urls = json.load(f)
                if isinstance(urls, list):
                    for url in urls:
                        job_id = url.split("/")[-1].split("?")[0]
                        app_id = db.add_job_application(
                            run_id, job_id, url, "Legacy (Migrated)", "Unknown"
                        )
                        db.update_job_state(app_id, "Applied Successfully")
                        total_applied += 1
                        total_found += 1
        except Exception as e:
            logging.error("Failed to migrate APEC JSON: %s", e)

    # 2. External Apps JSON (Dict of job_id -> info)
    if os.path.exists(ext_path):
        try:
            with open(ext_path, "r", encoding="utf-8") as f:
                apps = json.load(f)
                if isinstance(apps, dict):
                    for job_id, info in apps.items():
                        app_id = db.add_job_application(
                            run_id, 
                            job_id, 
                            info.get("url", "N/A"), 
                            info.get("title", "Legacy (Migrated)"), 
                            info.get("company", "Unknown")
                        )
                        db.update_job_state(app_id, "External")
                        total_found += 1
        except Exception as e:
            logging.error("Failed to migrate External JSON: %s", e)

    db.finish_run(run_id, total_found=total_found, total_applied=total_applied)
    logging.info("Migration complete: %d jobs migrated.", total_found)

if __name__ == "__main__":
    import sys
    # Add project root to path for local execution
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    
    SCRATCH_DIR = os.path.join(os.path.dirname(__file__), "../scratch")
    APEC_PATH = os.path.join(SCRATCH_DIR, "apec_applied.json")
    EXT_PATH = os.path.join(SCRATCH_DIR, "external_applications_applied.json")
    
    db = DBManager()
    migrate(db, APEC_PATH, EXT_PATH)
    print("Migration finished. Check history.db")
