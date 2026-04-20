# Specification: Dynamic Configuration Prompting (APEC)

## Overview
This feature enhances the onboarding and execution experience for the APEC module by dynamically prompting the user for missing, placeholder, or invalid configuration values at runtime, rather than solely during the initial bootstrap phase.

## Functional Requirements
- **Post-Selection Prompting:** The application will prompt the user for necessary APEC credentials (`apec_email`, `apec_password`) *after* they select the APEC platform from the main menu.
- **Config Separation:** The configuration will be updated to explicitly use `apec_email` instead of a generic `email` field to clearly separate APEC credentials from other platforms like JobTeaser.
- **Placeholder & Missing Detection:** The system will identify "missing info" by checking if keys are entirely missing from `configs/config.json`, if their values are empty strings, or if they match known default placeholders.
- **Persistent Storage:** New information provided by the user during these prompts will be automatically saved back to `configs/config.json` for future runs.
- **Dynamic Configuration (APEC Pages):** The configuration for `apec_max_pages_per_keyword` will be dynamically prompted during the APEC launch process *only* if the user selects the "All time" date filter and the value is missing, empty, or a placeholder.
- **Login Retry Prompting:** If the APEC login attempt fails (e.g., due to invalid credentials), the application will inform the user, prompt them to re-enter their `apec_email` and `apec_password` (which can be echoed as standard text input since this runs locally), and retry the login, saving the new successful credentials to the config.

## Non-Functional Requirements
- **UX:** Prompts should be clear, utilizing the existing terminal interface tools.

## Out of Scope
- Any modifications to the JobTeaser module or its configuration flow.

## Acceptance Criteria
1. Given a `configs/config.json` file missing an `apec_email` or `apec_password`, when the user selects APEC, they are prompted for the missing values, and they are saved to the file.
2. If all APEC credentials are present and valid, the application proceeds without prompting.
3. If the APEC login fails with the saved credentials, the user is immediately prompted to enter new credentials, which are used to retry and then saved if successful.
4. When the user selects "All time" for the date filter, if `apec_max_pages_per_keyword` is missing/empty, they are prompted to provide a value. If another date filter is selected, no prompt for this value occurs.