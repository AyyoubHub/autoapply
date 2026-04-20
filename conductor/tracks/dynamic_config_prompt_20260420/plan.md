# Implementation Plan: Dynamic Configuration Prompting (APEC)

## Phase 1: Refactoring Configuration and Settings [checkpoint: fb4e1a9]
- [x] Task: Update default configurations to separate APEC and JobTeaser credentials. e9d4e13
    - [x] Update `configs/config.example.json` to replace `email` with `apec_email`.
    - [x] Ensure backward compatibility or clear error messages for users with the old `email` key format.
- [x] Task: Conductor - User Manual Verification 'Phase 1: Refactoring Configuration and Settings' (Protocol in workflow.md)

## Phase 2: Dynamic Prompting Logic [checkpoint: a0e4399]
- [x] Task: Implement configuration checking utility. a46a5fe
    - [x] Write tests for a new function `check_and_prompt_apec_config()` in `scripts/utils.py`.
    - [x] Implement the function to check `apec_email` and `apec_password` against missing, empty, or placeholder values.
    - [x] Add logic to prompt the user using `input` / `questionary` if values are missing.
    - [x] Add logic to save updated values back to `configs/config.json`.
- [x] Task: Conductor - User Manual Verification 'Phase 2: Dynamic Prompting Logic' (Protocol in workflow.md)

## Phase 3: Integration into APEC Module [checkpoint: d7c78e1]
- [x] Task: Integrate dynamic prompting into the APEC execution flow. 2079ae5
    - [x] Update `scripts/apec.py` to prompt for `apec_max_pages_per_keyword` specifically when the date filter is "All time".
    - [x] Update `scripts/apec.py` to call `check_and_prompt_apec_config()` immediately before attempting to log in.
- [x] Task: Implement login retry mechanism. 2079ae5
    - [x] Update `_login` or the main run loop in `scripts/apec.py` to catch credential errors (like "incorrect password" on the site).
    - [x] Prompt the user for new credentials upon failure, save them to config, and retry the login seamlessly.
- [x] Task: Conductor - User Manual Verification 'Phase 3: Integration into APEC Module' (Protocol in workflow.md)