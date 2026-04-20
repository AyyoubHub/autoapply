import os
import json
import pytest
from unittest.mock import MagicMock, patch
from scripts.utils import check_and_prompt_apec_config

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

def test_check_and_prompt_apec_config_no_prompt_if_valid(mock_config_path):
    config_data = {
        "apec_email": "real@example.com",
        "apec_password": "real_password"
    }
    mock_config_path.write_text(json.dumps(config_data))
    
    with patch("questionary.text") as mock_text:
        config = check_and_prompt_apec_config()
        assert not mock_text.called
        assert config["apec_email"] == "real@example.com"

def test_check_and_prompt_apec_config_prompts_if_placeholder(mock_config_path):
    config_data = {
        "apec_email": "your_apec_email@example.com",
        "apec_password": "your_apec_password"
    }
    mock_config_path.write_text(json.dumps(config_data))
    
    # Mock questionary.text().ask()
    mock_ask = MagicMock()
    mock_ask.ask.side_effect = ["new@example.com", "new_password"]
    
    with patch("questionary.text", return_value=mock_ask):
        config = check_and_prompt_apec_config()
        assert config["apec_email"] == "new@example.com"
        assert config["apec_password"] == "new_password"
        
        # Verify it was saved back
        saved_config = json.loads(mock_config_path.read_text())
        assert saved_config["apec_email"] == "new@example.com"
        assert saved_config["apec_password"] == "new_password"
