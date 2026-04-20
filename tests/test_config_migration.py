import os
import json
import pytest
from scripts.utils import load_config

@pytest.fixture
def mock_config_path(tmp_path, monkeypatch):
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    config_file = config_dir / "config.json"
    
    # Store original join to avoid recursion
    original_join = os.path.join
    
    import scripts.utils
    def mock_join(*args):
        if len(args) > 0 and "config.json" in args[-1]:
            return str(config_file)
        return original_join(*args)
        
    monkeypatch.setattr(scripts.utils.os.path, "join", mock_join)
    
    return config_file

def test_load_config_with_apec_email(mock_config_path):
    config_data = {
        "apec_email": "test@apec.com",
        "apec_password": "password123"
    }
    mock_config_path.write_text(json.dumps(config_data))
    
    config = load_config()
    assert config["apec_email"] == "test@apec.com"

def test_load_config_backward_compatibility(mock_config_path):
    config_data = {
        "email": "old@example.com",
        "apec_password": "password123",
        "jobteaser_password": "jobpassword"
    }
    mock_config_path.write_text(json.dumps(config_data))
    
    config = load_config()
    # We expect 'apec_email' and 'jobteaser_email' to be populated from 'email'
    assert config.get("apec_email") == "old@example.com"
    assert config.get("jobteaser_email") == "old@example.com"
