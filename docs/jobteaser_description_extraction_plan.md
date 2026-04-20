# Implementation Plan - JobTeaser Description Extraction

This plan outlines the changes required to extract and store job descriptions and company information from JobTeaser offer pages during the automated application process.

## Proposed Changes

### [Component Name] Scripts & Data Storage

#### [MODIFY] `scripts/jobteaser.py`
- **Add Extraction Logic**: Before clicking the "Apply" button, execute a JavaScript snippet to capture:
    - Main job description content and structure.
    - "About the Company" section (if available).
- **Structure Capture**: Categorize content into headers, paragraphs, and lists to satisfy the "structure" requirement.
- **Data Persistence**: Save the extracted data to `scratch/job_descriptions.json`. 
    - Format: JSON (preferred for parsing).
    - Key: Job URL (unique identifier).
    - Content: `title`, `company`, `description_structure`, `about_company_structure`.

## Verification Plan

### Manual Verification
- Run the script on a few job offers.
- Verify that `scratch/job_descriptions.json` is created/updated.
- Ensure "About the Company" is correctly captured if present.
