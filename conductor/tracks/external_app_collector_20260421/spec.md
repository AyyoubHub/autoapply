# Specification: External Application Link Collector

## Overview
AutoApply currently focuses on "Easy Apply" (APEC). This feature introduces a mechanism to collect job offers that require applying on the company's website ("postuler sur le site de l'entreprise"). These offers will be saved to a local JSON file to allow the user to follow up manually.

## Functional Requirements
1. **Detection:** Identify job offers on APEC that display the "postuler sur le site de l'entreprise" button or message.
2. **Extraction:** Extract the external application URL, Job Title, Company Name, and generate a Unique Key/ID for the offer.
3. **Storage:**
    - Save the data to `scratch/external_applications.json`.
    - Use a dictionary structure keyed by the Unique ID.
    - Fields per entry: `title`, `company`, `url`, `discovery_date`.
4. **Duplicate Prevention:** Before adding a new entry, check if the Unique ID already exists in `scratch/external_applications.json`. If it exists, do not add it again (Ignore Duplicates).
5. **Initialization:** Ensure `scratch/external_applications.json` is initialized as an empty dictionary `{}` if it doesn't exist.

## Non-Functional Requirements
- **Resilience:** The process of saving to JSON should be atomic or handle file locks to prevent corruption if the bot is interrupted.
- **Maintainability:** Use existing utility functions for JSON file operations if available.

## Acceptance Criteria
- [ ] A job offer with "postuler sur le site de l'entreprise" is detected.
- [ ] The external URL is successfully extracted.
- [ ] The offer information is saved in `scratch/external_applications.json` with the correct structure.
- [ ] Subsequent detections of the same offer do not create duplicate entries in the JSON file.
- [ ] The file `scratch/external_applications.json` is created if it doesn't exist.

## Out of Scope
- Automatic form filling on the company's external website.
- Tracking the status of manual applications within AutoApply.
