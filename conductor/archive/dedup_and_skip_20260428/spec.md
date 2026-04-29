# Track: Deduplicate Database and Implement Skip Policies

## Overview
While the SQLite storage successfully captures job applications and states, it currently allows duplicate entries for the same job URL if found in multiple runs. This track aims to enforce URL uniqueness in the database, implement a cleanup script to deduplicate existing records, and introduce smarter, compute-saving skip policies. Finally, a 'Force' option will be added to allow overriding the skip policies when re-processing is desired.

## Functional Requirements
- **Database Deduplication:**
  - Create a script/migration to delete duplicate `job_applications` entries based on the `url`, keeping only the first (oldest) entry.
  - Modify the `job_applications` schema to enforce a `UNIQUE(url)` constraint to prevent future duplicates.
- **Smart Skip Policy:**
  - Modify `DBManager.is_applied()` (or add `should_skip()`) to check if a job should be skipped.
  - Default behavior: Skip jobs that are in a terminal state: `Applied Successfully`, `Already Applied`, or `AI Filtered / Rejected`.
  - Jobs in non-terminal or failed states (e.g., `Discovered / Pending`, `Application Failed`) will NOT be skipped, allowing the script to retry applying to them on subsequent runs.
- **Force Reprocess Option:**
  - Introduce an interactive prompt (or CLI flag/config setting) at the start of a run (APEC/JobTeaser) asking if the user wants to "Force Reprocess" previously seen jobs.
  - If "Force" is enabled, the skip policy is bypassed, and the AI/application process will run for all found jobs regardless of their state in the database.

## Non-Functional Requirements
- Ensure `add_job_application` uses `INSERT OR IGNORE` or equivalent logic to gracefully handle the new `UNIQUE` constraint without throwing errors during a run.
- The `is_applied` check must be efficient to avoid slowing down the discovery phase.

## Acceptance Criteria
- [ ] Existing duplicate job entries are removed from the database (keeping the first occurrence).
- [ ] A `UNIQUE` constraint is applied to the `url` column of the `job_applications` table.
- [ ] The core automation scripts (APEC, JobTeaser) skip jobs that were previously marked as `Applied Successfully`, `Already Applied`, or `AI Filtered / Rejected`.
- [ ] A prompt or option exists to override the skip behavior and force reprocessing.
- [ ] Unit tests are updated or created to verify the deduplication and new skip logic.