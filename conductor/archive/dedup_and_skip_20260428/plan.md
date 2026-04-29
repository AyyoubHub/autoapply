# Implementation Plan: Deduplicate Database and Implement Skip Policies

## Phase 1: Database Deduplication and Schema Update
- [x] Task: Create Deduplication Script
    - [x] Write a script (e.g., `scripts/deduplicate_db.py`) to delete duplicate `job_applications` entries based on `url`, retaining the first inserted record.
- [x] Task: Update Database Schema
    - [x] Modify `DBManager._init_db()` to include a `UNIQUE` constraint on the `url` column of the `job_applications` table.
    - [x] Update the `add_job_application` method to use `INSERT OR IGNORE` (or `INSERT OR REPLACE` if updating the run_id is preferred).
- [x] Task: Conductor - User Manual Verification 'Database Deduplication and Schema Update' (Protocol in workflow.md)

## Phase 2: Smart Skip Policy
- [x] Task: Update DBManager Check
    - [x] Add a `should_skip(url)` method to `DBManager` that returns `True` if the job is in a state of `Applied Successfully`, `Already Applied`, or `AI Filtered / Rejected`.
    - [x] Update `is_applied` to only check for successful application states.
- [x] Task: Update Automation Scripts
    - [x] Update `scripts/apec.py` and `scripts/jobteaser.py` to use `should_skip` instead of `is_applied`.
- [x] Task: Write Tests for Smart Skip Policy
    - [x] Add unit tests for `should_skip` in `test_db_manager.py`.
- [x] Task: Conductor - User Manual Verification 'Smart Skip Policy' (Protocol in workflow.md)

## Phase 3: Force Reprocess Option
- [x] Task: Add Force Option to Scripts
    - [x] Add an interactive prompt using `questionary` in `apec.py` and `jobteaser.py` (e.g., "Force reprocess previously seen/rejected jobs?").
    - [x] Pass the `force` flag down to the processing logic to bypass the `should_skip` check.
- [x] Task: Conductor - User Manual Verification 'Force Reprocess Option' (Protocol in workflow.md)