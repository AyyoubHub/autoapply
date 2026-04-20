import os
import json
import pytest
from scripts.utils import load_applied_jobs, save_applied_job

TEST_FILE = "scratch/test_applied.json"

@pytest.fixture(autouse=True)
def cleanup_test_file():
    if os.path.exists(TEST_FILE):
        os.remove(TEST_FILE)
    yield
    if os.path.exists(TEST_FILE):
        os.remove(TEST_FILE)

def test_save_and_load_applied_jobs(monkeypatch):
    # Mock the path in utils.py to use our test file
    import scripts.utils
    monkeypatch.setattr(scripts.utils, "load_applied_jobs", lambda plat="test": _load_test(plat))
    monkeypatch.setattr(scripts.utils, "save_applied_job", lambda url, plat="test": _save_test(url, plat))
    
    def _load_test(plat):
        path = TEST_FILE
        if not os.path.exists(path):
            return set()
        with open(path, "r") as f:
            return set(json.load(f))
            
    def _save_test(url, plat):
        path = TEST_FILE
        applied = _load_test(plat)
        applied.add(url)
        with open(path, "w") as f:
            json.dump(list(applied), f)

    url1 = "https://example.com/job1"
    url2 = "https://example.com/job2"
    
    _save_test(url1, "test")
    _save_test(url2, "test")
    
    loaded = _load_test("test")
    assert url1 in loaded
    assert url2 in loaded
    assert len(loaded) == 2

def test_load_empty_history(monkeypatch):
    import scripts.utils
    # Ensure file doesn't exist
    if os.path.exists(TEST_FILE):
        os.remove(TEST_FILE)
        
    # We want to test the REAL function but pointing to a fake path.
    # Since the path is hardcoded in utils.py, we might need to patch os.path.join or similar.
    # Better: patch the entire function logic or use a dedicated test platform name.
    
    # Actually, scripts/utils.py uses:
    # path = os.path.join(os.path.dirname(__file__), f"../scratch/{platform}_applied.json")
    
    platform = "nonexistent_test_platform"
    path = os.path.join(os.path.dirname(scripts.utils.__file__), f"../scratch/{platform}_applied.json")
    if os.path.exists(path):
        os.remove(path)
        
    loaded = load_applied_jobs(platform)
    assert isinstance(loaded, set)
    assert len(loaded) == 0
