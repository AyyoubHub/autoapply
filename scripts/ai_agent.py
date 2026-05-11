import os
import json
import logging
from google import genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ---------------------------------------------------------------------------
# Gemini client
# ---------------------------------------------------------------------------

def get_gemini_client():
    """Return a configured Gemini client, or None if the API key is absent."""
    api_key = os.getenv("GEMINI_API")
    if not api_key:
        logging.warning(
            "GEMINI_API not set in environment — AI filtering disabled. "
            "Add GEMINI_API=<your_key> to .env to enable it."
        )
        return None
    return genai.Client(api_key=api_key)


# ---------------------------------------------------------------------------
# Job relevance check
# ---------------------------------------------------------------------------

def is_high_quality_match(job_title: str, job_description: str, keywords: list) -> tuple[bool, str]:
    """
    Uses Gemini to determine if a job is a high-quality match based on keywords.
    Provides a semantic layer over simple keyword matching.
    Returns (is_relevant, reason).

    If the Gemini API key is not configured, fails open (returns True) so
    the pipeline continues without AI filtering.
    """
    client = get_gemini_client()
    if not client:
        return True, "AI service unavailable — API key not configured"

    # gemini-2.0-flash-lite is the lightweight fast model (as of 2025-Q1)
    model_id = "gemini-2.0-flash-lite"
    prompt = f"""
    Analyze if this job is a high-quality match for a candidate searching with these keywords.

    Target Keywords: {", ".join(keywords)}
    Job Title: {job_title}
    Job Description:
    {job_description[:3000]}

    Task: Determine if the job is truly relevant to the candidate's field and seniority level.
    - If the keywords are "Python, Developer" and the job is a "Python Internship", it might be a mismatch depending on the spirit of the search.
    - Exclude "Freelance" or "Portage" if the description seems purely focused on B2B while the candidate is likely seeking a contract.

    Return ONLY a JSON object: {{"relevant": true/false, "reason": "short explanation"}}
    """

    try:
        response = client.models.generate_content(
            model=model_id,
            contents=prompt,
            config={"response_mime_type": "application/json"},
        )
        data = json.loads(response.text.strip())
        is_relevant = data.get("relevant", True)
        reason = data.get("reason", "No reason provided")

        if not is_relevant:
            logging.info("AI rejected job: %s. Reason: %s", job_title, reason)
        return is_relevant, reason
    except Exception as e:
        logging.error("AI relevance check failed for '%s': %s", job_title, e)
        return True, f"AI check error: {e}"
