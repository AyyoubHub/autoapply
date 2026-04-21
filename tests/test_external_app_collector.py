import os
import json
import pytest
from scripts.utils import init_external_apps_file

@pytest.fixture
def temp_external_apps_file(tmp_path):
    """Fixture to provide a temporary path for the external applications file."""
    f = tmp_path / "external_applications.json"
    return str(f)

def test_init_external_apps_file(temp_external_apps_file, monkeypatch):
    """Test that init_external_apps_file creates an empty dict if file doesn't exist."""
    
    # Mock the path in utils to use our temp file
    import scripts.utils
    monkeypatch.setattr(scripts.utils, "EXTERNAL_APPS_PATH", temp_external_apps_file)
    
    # Ensure file doesn't exist
    assert not os.path.exists(temp_external_apps_file)
    
    # Call init
    init_external_apps_file()
    
    # Check it exists and is {}
    assert os.path.exists(temp_external_apps_file)
    with open(temp_external_apps_file, "r") as f:
        data = json.load(f)
        assert data == {}

def test_init_external_apps_file_exists(temp_external_apps_file, monkeypatch):
    """Test that init_external_apps_file doesn't overwrite existing content."""
    
    import scripts.utils
    monkeypatch.setattr(scripts.utils, "EXTERNAL_APPS_PATH", temp_external_apps_file)
    
    # Create file with content
    existing_data = {"test": "data"}
    with open(temp_external_apps_file, "w") as f:
        json.dump(existing_data, f)
        
    # Call init
    init_external_apps_file()
    
    # Check it still has existing data
    with open(temp_external_apps_file, "r") as f:
        data = json.load(f)
        assert data == existing_data

def test_init_external_apps_file_corrupt(temp_external_apps_file, monkeypatch):
    """Test that init_external_apps_file resets file if it contains invalid JSON or not a dict."""
    
    import scripts.utils
    monkeypatch.setattr(scripts.utils, "EXTERNAL_APPS_PATH", temp_external_apps_file)
    
    # Create file with invalid JSON
    with open(temp_external_apps_file, "w") as f:
        f.write("not json")
        
    init_external_apps_file()
    with open(temp_external_apps_file, "r") as f:
        assert json.load(f) == {}
        
    # Create file with a list instead of a dict
    with open(temp_external_apps_file, "w") as f:
        json.dump([1, 2, 3], f)
        
    init_external_apps_file()
    with open(temp_external_apps_file, "r") as f:
        assert json.load(f) == {}

def test_load_external_apps(temp_external_apps_file, monkeypatch):
    """Test that load_external_apps correctly loads the JSON data."""
    from scripts.utils import load_external_apps
    
    import scripts.utils
    monkeypatch.setattr(scripts.utils, "EXTERNAL_APPS_PATH", temp_external_apps_file)
    
    # Existing data
    existing_data = {"id1": {"title": "Job 1"}}
    with open(temp_external_apps_file, "w") as f:
        json.dump(existing_data, f)
        
    data = load_external_apps()
    assert data == existing_data
