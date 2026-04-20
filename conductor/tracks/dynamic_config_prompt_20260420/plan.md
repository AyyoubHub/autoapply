# Implementation Plan: Dynamic Configuration Prompting (APEC)

## Phase 1: Refactoring Configuration and Settings
- [ ] Task: Update default configurations to separate APEC and JobTeaser credentials.
    - [ ] Update `configs/config.example.json` to replace `email` with `apec_email`.
    - [ ] Ensure backward compatibility or clear error messages for users with the old `email` key format.
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Refactoring Configuration and Settings' (Protocol in workflow.md)

## Phase 2: Dynamic Prompting Logic
- [ ] Task: Implement configuration checking utility.
    - [ ] Write tests for a new function `check_and_prompt_apec_config()` in `scripts/utils.py`.
    - [ ] Implement the function to check `apec_email` and `apec_password` against missing, empty, or placeholder values.
    - [ ] Add logic to prompt the user using `input` / `questionary` if values are missing.
    - [ ] Add logic to save updated values back to `configs/config.json`.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Dynamic Prompting Logic' (Protocol in workflow.md)

## Phase 3: Integration into APEC Module
- [ ] Task: Integrate dynamic prompting into the APEC execution flow.
    - [ ] Update `scripts/apec.py` to prompt for `apec_max_pages_per_keyword` specifically when the date filter is "All time".
    - [ ] Update `scripts/apec.py` to call `check_and_prompt_apec_config()` immediately before attempting to log in.
- [ ] Task: Implement login retry mechanism.
    - [ ] Update `_login` or the main run loop in `scripts/apec.py` to catch credential errors (like "incorrect password" on the site).
    - [ ] Prompt the user for new credentials upon failure, save them to config, and retry the login seamlessly.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Integration into APEC Module' (Protocol in workflow.md)