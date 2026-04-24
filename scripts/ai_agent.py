import os
import json
import logging
import subprocess
from google import genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def is_high_quality_match(job_title: str, job_description: str, keywords: list) -> tuple[bool, str]:
    """
    Uses Gemini to determine if a job is a high-quality match based on keywords.
    Provides a semantic layer over simple keyword matching.
    Returns (is_relevant, reason).
    """
    client = get_gemini_client()
    if not client:
        return True, "AI service unavailable"  # Fail open

    model_id = "gemini-3.1-flash-lite"
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
            config={'response_mime_type': 'application/json'}
        )
        data = json.loads(response.text.strip())
        is_relevant = data.get("relevant", True)
        reason = data.get("reason", "No reason provided")
        
        if not is_relevant:
            logging.info("AI rejected job: %s. Reason: %s", job_title, reason)
        return is_relevant, reason
    except Exception as e:
        logging.error("AI relevance check failed: %s", e)
        return True, f"Error: {str(e)}"

def compile_tex_to_pdf(tex_path: str):
    """
    Compiles a .tex file to .pdf using the bundled Tectonic binary.
    """
    tectonic_path = os.path.join(os.path.dirname(__file__), "tectonic")
    if not os.path.exists(tectonic_path):
        logging.error("Tectonic binary not found at %s", tectonic_path)
        return None
    
    out_dir = os.path.dirname(tex_path)
    try:
        logging.info("Compiling %s with Tectonic...", os.path.basename(tex_path))
        result = subprocess.run(
            [tectonic_path, tex_path, "--outdir", out_dir],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            pdf_path = tex_path.replace(".tex", ".pdf")
            if os.path.exists(pdf_path):
                logging.info("Successfully compiled PDF: %s", pdf_path)
                return pdf_path
        else:
            logging.error("Tectonic compilation failed: %s", result.stderr)
    except Exception as e:
        logging.error("Failed to run Tectonic: %s", e)
    return None

def get_gemini_client():
    api_key = os.getenv("GEMINI_API")
    if not api_key:
        logging.error("GEMINI_API not found in environment. Please check your .env file.")
        return None
    return genai.Client(api_key=api_key)

def adapt_cv_and_generate_message(cv_content: str, job_dossier: dict):
    """
    Uses Gemini to adapt the LaTeX CV and generate a motivation message using the new GenAI SDK.
    Returns a tuple (adapted_cv_tex, motivation_message).
    """
    client = get_gemini_client()
    if not client:
        return None, None

    # Using the suggested model from the Gemini 3.1 series
    # Using 'gemini-3.1-flash-lite' as a reliable stable fallback
    model_id = "gemini-3.1-flash"

    
    prompt = f"""
    You are an expert career coach and LaTeX developer. 
    Your task is to take a base LaTeX CV and adapt it for a specific job offer.

    JOB DETAILS:
    Title: {job_dossier.get('title')}
    Company: {job_dossier.get('company')}
    Description: {json.dumps(job_dossier.get('description_structure'), indent=2)}

    BASE CV (LaTeX):
    {cv_content}

    TASKS:
    1. Adapt the CV to highlight skills and experiences most relevant to the job. 
       - Keep the overall LaTeX structure and personal info intact.
       - Focus on the "Expertise Technique", "Compétences Principales", and "Expériences Professionnelles" sections.
       - Ensure the LaTeX is valid and compiles.
    2. Generate a short, professional motivation message (approx 100-150 words) that can be used in the 'Message' field of the application.

    RESPONSE FORMAT:
    Please provide your response in JSON format with two keys:
    - "adapted_cv": "the full LaTeX code of the adapted CV"
    - "message": "the motivation message"

    Only return the JSON object, nothing else.
    """

    try:
        # The new SDK uses contents=...
        response = client.models.generate_content(
            model=model_id,
            contents=prompt
        )
        text = response.text.strip()
        
        # Clean up Markdown code blocks if present
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        
        data = json.loads(text.strip())
        return data.get("adapted_cv"), data.get("message")
    except Exception as e:
        logging.error("AI Agent failed with model %s: %s", model_id, e)
        # Attempt fallback to 3.1-flash-lite
        if model_id != "gemini-3.1-flash-lite":
            logging.info("Attempting fallback to gemini-3.1-flash-lite...")
            try:
                response = client.models.generate_content(model="gemini-3.1-flash-lite", contents=prompt)
                data = json.loads(response.text.strip().replace("```json", "").replace("```", "").strip())
                return data.get("adapted_cv"), data.get("message")
            except Exception as e2:
                logging.error("Fallback AI Agent failed: %s", e2)
        return None, None

def process_job_for_apply(job_url: str):
    """
    High-level flow for preparing an application.
    """
    from job_dossier_manager import get_dossier_by_url
    from utils import load_config
    
    config = load_config()
    cv_path = os.path.join(os.path.dirname(__file__), "..", config.get("cv_path", "tex/default.tex"))
    
    if not os.path.exists(cv_path):
        logging.error("Base CV not found at %s", cv_path)
        return None

    dossier = get_dossier_by_url(job_url)
    if not dossier:
        logging.error("Dossier not found for URL: %s", job_url)
        return None

    with open(cv_path, "r", encoding="utf-8") as f:
        cv_content = f.read()

    logging.info("Calling Gemini to adapt CV for %s...", dossier.get("title"))
    adapted_cv, message = adapt_cv_and_generate_message(cv_content, dossier)
    
    if adapted_cv and message:
        # Save adapted CV
        safe_title = "".join(x for x in dossier.get("title") if x.isalnum() or x in " -_").strip()
        safe_company = "".join(x for x in dossier.get("company") if x.isalnum() or x in " -_").strip()
        filename = f"{safe_title}_{safe_company}.tex"
        out_folder = os.path.join(os.path.dirname(__file__), "../tex")
        os.makedirs(out_folder, exist_ok=True)
        
        out_path = os.path.join(out_folder, filename)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(adapted_cv)
        
        logging.info("Adapted CV saved to %s", out_path)
        
        # Compile to PDF
        pdf_path = compile_tex_to_pdf(out_path)
        
        return {
            "cv_path": out_path,
            "pdf_path": pdf_path,
            "message": message
        }
    return None
