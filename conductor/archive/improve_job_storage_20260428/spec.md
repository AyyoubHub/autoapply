# Track: Improve Applied Jobs Storage and State Management

## Overview
Currently, the AutoApply framework tracks applied jobs using simple JSON files, making it difficult to query, group applications by runs, or understand the detailed state of each job application over time. This track aims to transition the local application history from JSON to an SQLite database. The new system will track detailed states for each job application and group them logically under specific script "runs," complete with search keywords and execution statistics.

## Functional Requirements
- **SQLite Database Integration:** Implement an SQLite database to store and manage all job application history instead of JSON files.
- **Run Tracking:** Every execution of the scraping script must create a new "Run" record containing:
  - Timestamp (Start/End time)
  - Platform (e.g., APEC)
  - Search Keywords used
  - Run Statistics (total jobs found, total applied, etc.)
- **Job State Tracking:** Each job discovered during a run must be tracked with the following potential states:
  - `Discovered / Pending`: Found but not yet processed.
  - `AI Filtered / Rejected`: Deemed irrelevant by Gemini.
  - `Applied Successfully`: The application process completed without errors.
  - `Application Failed`: An error occurred during the application process.
- **Data Migration:** Create a migration script to automatically migrate the existing JSON history (e.g., `scratch/apec_applied.json`, `scratch/external_applications.json`) into the new SQLite database.

## Non-Functional Requirements
- The database interactions should be encapsulated in a dedicated data access layer or manager class (e.g., `HistoryManager`).
- The solution must ensure database locks are handled properly during parallel operations (if any).
- The transition must not break the existing AI and application automation logic.
- **Git Operations:** Committing and pushing are explicitly disabled for this track.

## Acceptance Criteria
- [ ] A new SQLite database is successfully initialized and replaces the current JSON-based local history.
- [ ] A new "Run" entity is created in the database upon starting the script, accurately logging timestamp, keywords, and platform.
- [ ] Job applications are linked to their specific "Run" entity and accurately reflect their state (Discovered, AI Filtered, Applied, Failed).
- [ ] A migration script successfully translates old JSON data into the new SQLite schema.
- [ ] The core APEC automation workflow completes without errors using the new SQLite storage.

## Out of Scope
- Building a UI/Dashboard to view the SQLite data (this will be handled in a future track).
- Adding new scraping platforms or changing the Gemini analysis prompts.