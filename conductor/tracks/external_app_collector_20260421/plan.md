# Implementation Plan: External Application Link Collector

## Phase 1: Infrastructure & Data Models [checkpoint: fc52d59]
- [x] Task: Define the data model for external applications and initialize the storage file. e6d32da
    - [x] Create a new module or update `scripts/utils.py` to handle `scratch/external_applications.json`.
    - [x] Implement a function to initialize the JSON file if it doesn't exist.
    - [x] Write unit tests for file initialization and data validation.
    - [x] Integrate initialization into `main.py` bootstrap.
- [x] Task: Conductor - User Manual Verification 'Phase 1: Infrastructure & Data Models' (Protocol in workflow.md)

## Phase 2: Detection and Extraction Logic [checkpoint: 9e23b06]
- [x] Task: Implement detection of "postuler sur le site de l'entreprise". d9e3674
    - [x] Update `scripts/apec.py` to identify the external application button/link.
    - [x] Extract the target URL and offer metadata (Title, Company).
    - [x] Write unit tests for the detection logic using HTML mocks.
- [x] Task: Implement storage logic with duplicate prevention. d9e3674
    - [x] Implement a function to add a new offer to `scratch/external_applications.json`.
    - [x] Ensure it checks for existing IDs before saving.
    - [x] Write unit tests for saving logic and duplicate handling.
- [x] Task: Conductor - User Manual Verification 'Phase 2: Detection and Extraction Logic' (Protocol in workflow.md)

## Phase 3: Integration and End-to-End Verification
- [x] Task: Integrate the collection logic into the main APEC loop. e19a3a4
    - [x] Update the APEC application flow to call the collection function when an external link is found.
    - [x] Verify that the flow continues to the next job after collecting the link.
- [x] Task: Manual end-to-end verification. e19a3a4
    - [x] Run the bot on a keyword known to have external application links.
    - [x] Verify `scratch/external_applications.json` is updated correctly.
- [x] Task: Conductor - User Manual Verification 'Phase 3: Integration and End-to-End Verification' (Protocol in workflow.md)
