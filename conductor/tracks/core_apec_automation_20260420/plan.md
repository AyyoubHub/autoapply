# Implementation Plan: Core APEC Automation Enhancements & Stabilization

## Phase 1: Research and Design
- [x] Task: Research APEC's current application modal and button DOM structure for resilience. 2ac93f0
    - [x] Identify all potential button text variants (e.g., "Postuler", "Envoyer ma candidature").
    - [x] Verify the Didomi consent button's ID stability.
- [x] Task: Design the Gemini semantic filtering prompt for APEC. e2c9648
    - [x] Test various prompt versions with representative APEC job descriptions.
    - [x] Ensure the prompt correctly identifies seniority and contract type mismatches.
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Research and Design' (Protocol in workflow.md)

## Phase 2: Core Semantic Filtering Implementation
- [ ] Task: Integrate Gemini-2.0-flash into the APEC discovery/application flow.
    - [ ] Implement the `is_high_quality_match` function in `scripts/ai_agent.py`.
    - [ ] Call the AI check in `scripts/apec.py` after the initial keyword match.
    - [ ] Implement a fallback mechanism for when Gemini is unavailable.
- [ ] Task: Implement robust text-based button matching for APEC.
    - [ ] Update XPaths for "Postuler" and "Envoyer ma candidature" to use text normalization.
    - [ ] Enhance `_wait_for_application_confirmation` to handle varying confirmation banners.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Core Semantic Filtering Implementation' (Protocol in workflow.md)

## Phase 3: Local History and Persistence
- [ ] Task: Implement local persistence for applied job URLs.
    - [ ] Add `load_applied_jobs` and `save_applied_job` functions to `scripts/utils.py`.
    - [ ] Store applied job URLs in `scratch/apec_applied.json`.
    - [ ] Implement a pre-navigation check in `_process_job` using the local history.
- [ ] Task: Implement on-page to local history synchronization.
    - [ ] Update `_is_already_applied` to automatically save detected "Applied" statuses back to `apec_applied.json`.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Local History and Persistence' (Protocol in workflow.md)

## Phase 4: Reliability and Error Recovery
- [ ] Task: Enhance session crash recovery in APEC's main loop.
    - [ ] Improve handling of `InvalidSessionIdException` to ensure the driver is restarted if needed.
    - [ ] Implement a retry mechanism for failed individual job applications.
- [ ] Task: Refine logging and reporting.
    - [ ] Add clear summary reports at the end of each APEC run (e.g., "Jobs Applied: X, AI Rejected: Y, Already Applied: Z").
    - [ ] Improve timestamped logs with more diagnostic information for application failures.
- [ ] Task: Conductor - User Manual Verification 'Phase 4: Reliability and Error Recovery' (Protocol in workflow.md)
