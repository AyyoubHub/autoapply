import pytest
from unittest.mock import MagicMock, patch
from scripts.ai_agent import is_high_quality_match

@patch("scripts.ai_agent.get_gemini_client")
def test_is_high_quality_match_positive(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    
    # Mock successful relevant response
    mock_response = MagicMock()
    mock_response.text = '{"relevant": true, "reason": "Matches seniority and keywords"}'
    mock_client.models.generate_content.return_value = mock_response
    
    keywords = ["Python", "Developer"]
    job_title = "Senior Python Developer"
    job_desc = "We are looking for a Senior Python Developer with 5 years of experience."
    
    result = is_high_quality_match(job_title, job_desc, keywords)
    assert result is True

@patch("scripts.ai_agent.get_gemini_client")
def test_is_high_quality_match_negative(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    
    # Mock irrelevant response
    mock_response = MagicMock()
    mock_response.text = '{"relevant": false, "reason": "This is an internship, not a developer role"}'
    mock_client.models.generate_content.return_value = mock_response
    
    keywords = ["Python", "Developer"]
    job_title = "Python Intern"
    job_desc = "We are looking for a student for a Python internship."
    
    result = is_high_quality_match(job_title, job_desc, keywords)
    assert result is False

@patch("scripts.ai_agent.get_gemini_client")
def test_is_high_quality_match_fallback_on_error(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    
    # Mock error during API call
    mock_client.models.generate_content.side_effect = Exception("API error")
    
    keywords = ["Python", "Developer"]
    job_title = "Python Developer"
    job_desc = "Any description"
    
    # Should fail open (True)
    result = is_high_quality_match(job_title, job_desc, keywords)
    assert result is True
