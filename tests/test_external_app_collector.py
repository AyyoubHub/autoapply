import os
import json
import pytest
from selenium.webdriver.common.by import By
from scripts.utils import init_external_apps_file, load_external_apps

@pytest.fixture
def temp_external_apps_file(tmp_path):
    """Fixture to provide a temporary path for the external applications file."""
    f = tmp_path / "external_applications.json"
    return str(f)

@pytest.fixture
def mock_external_apps_path(monkeypatch, temp_external_apps_file):
    import scripts.utils
    monkeypatch.setattr(scripts.utils, "EXTERNAL_APPS_PATH", temp_external_apps_file)
    return temp_external_apps_file

def test_init_external_apps_file(mock_external_apps_path):
    """Test that init_external_apps_file creates an empty dict if file doesn't exist."""
    assert not os.path.exists(mock_external_apps_path)
    init_external_apps_file()
    assert os.path.exists(mock_external_apps_path)
    with open(mock_external_apps_path, "r") as f:
        assert json.load(f) == {}

def test_load_external_apps(mock_external_apps_path):
    """Test that load_external_apps correctly loads the JSON data."""
    existing_data = {"id1": {"title": "Job 1"}}
    with open(mock_external_apps_path, "w") as f:
        json.dump(existing_data, f)
    data = load_external_apps()
    assert data == existing_data

from scripts.apec import _extract_external_link_info
from unittest.mock import MagicMock

def test_extract_external_link_info():
    """Test extracting info from a mock driver."""
    driver = MagicMock()
    
    def side_effect(by, value):
        mock = MagicMock()
        # By.TAG_NAME is 'tag name', By.XPATH is 'xpath'
        if value == "h1":
            mock.text = "Senior Python Developer"
        elif "card-offer-summary" in value:
            mock.text = "Tech Corp"
        elif "Postuler sur le site" in value:
            mock.get_attribute.return_value = "https://external.com/apply"
        else:
            mock.text = "Unknown"
            mock.get_attribute.return_value = None
        
        # If mock.text is a string, we need to mock it if we want .strip() to be a mock, 
        # but easier is just to let it be a string if we use it directly.
        # However _extract_external_link_info calls .text.strip()
        
        real_text = mock.text
        mock.text = MagicMock(spec=str)
        mock.text.__str__.return_value = real_text
        mock.text.strip.return_value = real_text
        
        return mock
        
    driver.find_element.side_effect = side_effect
    
    info = _extract_external_link_info(driver, "https://apec.fr/detail/123")
    assert info["title"] == "Senior Python Developer"
    assert info["company"] == "Tech Corp"
    assert info["url"] == "https://external.com/apply"
    assert "discovery_date" in info

def test_save_external_app(mock_external_apps_path):
    """Test that save_external_app saves new entries and ignores duplicates."""
    from scripts.utils import save_external_app, load_external_apps
    
    init_external_apps_file()
    
    job_id = "12345"
    job_info = {"title": "Test Job", "company": "Test Co", "url": "http://test.com"}
    
    # Save new
    save_external_app(job_id, job_info)
    data = load_external_apps()
    assert job_id in data
    assert data[job_id]["title"] == "Test Job"
    
    # Save duplicate (should be ignored)
    duplicate_info = {"title": "Changed Title"}
    save_external_app(job_id, duplicate_info)
    data = load_external_apps()
    assert data[job_id]["title"] == "Test Job"  # Still old title
    
    # Save another new one
    job_id_2 = "67890"
    save_external_app(job_id_2, {"title": "Job 2"})
    data = load_external_apps()
    assert len(data) == 2
    assert job_id_2 in data
