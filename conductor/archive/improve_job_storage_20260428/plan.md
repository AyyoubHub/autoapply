# Implementation Plan: Improve Applied Jobs Storage and State Management

*Note: Committing and pushing have been explicitly disabled for this track per user request.*

## Phase 1: Database Architecture and Setup
- [x] Task: Design Database Schema
    - [x] Create SQLite schema for `Runs` (id, start_time, end_time, keywords, platform, status, total_found, total_applied).
    - [x] Create SQLite schema for `JobApplications` (id, run_id, job_id, url, title, company, state, ai_reason, timestamp).
- [x] Task: Write Tests for Database Architecture
    - [x] Create tests for database initialization.
    - [x] Create tests for `Runs` CRUD operations.
    - [x] Create tests for `JobApplications` state updates and queries.
- [x] Task: Implement History Manager
    - [x] Create a new Python module (e.g., `scripts/db_manager.py`).
    - [x] Write initialization function to create tables if they don't exist.
    - [x] Implement CRUD operations for `Runs` (create run, finish run, update stats).
    - [x] Implement CRUD operations for `JobApplications` (add job, update state).
- [x] Task: Conductor - User Manual Verification 'Database Architecture and Setup' (Protocol in workflow.md)

## Phase 2: Core Automation Integration
- [x] Task: Write Tests for Core Automation Integration
    - [x] Update existing tests or create new ones to ensure the core workflow interacts correctly with the database.
- [x] Task: Integrate Run Tracking
    - [x] Update `main.py` or entry point to initialize a Run before the scraping loop starts.
    - [x] Update the end of the script to finalize the Run (end_time, final stats).
- [x] Task: Integrate Job State Tracking
    - [x] Update the scraping logic (e.g., `scripts/apec.py`) to insert "Discovered / Pending" jobs into the database.
    - [x] Update the AI filtering logic (e.g., `scripts/ai_agent.py`) to update job states to "AI Filtered / Rejected" or proceed.
    - [x] Update the application logic to update job states to "Applied Successfully" or "Application Failed".
- [x] Task: Conductor - User Manual Verification 'Core Automation Integration' (Protocol in workflow.md)

## Phase 3: Data Migration and Cleanup
- [x] Task: Write Tests for Data Migration
    - [x] Test migration logic with sample mock JSON data.
- [x] Task: Create Migration Script
    - [x] Create a new script (e.g., `scripts/migrate_history.py`).
    - [x] Read existing JSON files.
    - [x] Parse old data and map it to a "Legacy" Run.
    - [x] Insert old jobs with an inferred state (e.g., "Applied Successfully") into the SQLite database.
- [x] Task: Replace JSON usages and Cleanup
    - [x] Remove legacy JSON history reading/writing from the main codebase.
    - [x] Ensure all references point to the new SQLite database.
- [x] Task: Conductor - User Manual Verification 'Data Migration and Cleanup' (Protocol in workflow.md)