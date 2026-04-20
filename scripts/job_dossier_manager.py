import json
import os
import time
import logging

DOSSIER_PATH = os.path.join(os.path.dirname(__file__), "../scratch/job_dossiers.json")

def save_job_dossier(job_data: dict):
    """
    Saves or updates a job dossier in a single JSON file.
    The file contains a list of job dossier objects.
    """
    try:
        os.makedirs(os.path.dirname(DOSSIER_PATH), exist_ok=True)
        
        all_dossiers = []
        if os.path.exists(DOSSIER_PATH):
            try:
                with open(DOSSIER_PATH, "r", encoding="utf-8") as f:
                    all_dossiers = json.load(f)
                    if not isinstance(all_dossiers, list):
                        all_dossiers = []
            except Exception:
                all_dossiers = []

        # Use URL as unique identifier
        href = job_data.get("url")
        existing_index = -1
        for idx, dossier in enumerate(all_dossiers):
            if dossier.get("url") == href:
                existing_index = idx
                break

        job_data["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        
        if existing_index >= 0:
            all_dossiers[existing_index].update(job_data)
        else:
            all_dossiers.append(job_data)

        with open(DOSSIER_PATH, "w", encoding="utf-8") as f:
            json.dump(all_dossiers, f, indent=2, ensure_ascii=False)
            
        logging.info("Job dossier saved for: %s", job_data.get("title"))
        return True
    except Exception as e:
        logging.error("Failed to save job dossier: %s", e)
        return False

def get_dossier_by_url(url: str):
    """Retrieve a specific dossier from the storage."""
    if not os.path.exists(DOSSIER_PATH):
        return None
    try:
        with open(DOSSIER_PATH, "r", encoding="utf-8") as f:
            all_dossiers = json.load(f)
            for dossier in all_dossiers:
                if dossier.get("url") == url:
                    return dossier
    except Exception:
        pass
    return None
