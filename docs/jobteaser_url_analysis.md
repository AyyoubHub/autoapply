# JobTeaser Search URL Structure Analysis

This document details the exact URL parameters required to programmatically search jobs on JobTeaser, ensuring we only pull "Easy Apply" (Candidature simplifiée) jobs.

## Base URL
`https://www.jobteaser.com/fr/job-offers`

## Core Parameters

### 1. Search Query (`q`)
*   **Purpose:** The main keyword search.
*   **Usage:** `?q=java` (Must be URL-encoded).

### 2. Easy Apply Filter (`candidacy_type`)
*   **Purpose:** Filters out external redirect jobs, showing ONLY native "Candidature simplifiée" jobs.
*   **Usage:** `&candidacy_type=INTERNAL`
*   **Impact:** This is the most critical parameter. Including this ensures the automation script never encounters external site redirects, completely bypassing the need to detect and skip them in the DOM.

### 3. Pagination (`page`)
*   **Purpose:** Handles navigating through search result pages.
*   **Indexing:** JobTeaser pagination is **one-indexed**.
    *   Page 1 = `&page=1`
    *   Page 2 = `&page=2`

### 4. Sorting (`sort`)
*   **Purpose:** Orders the results.
*   **Known Values:**
    *   Date (Recency): `recency`
    *   Relevance: `relevance`
*   **Usage:** `&sort=recency`

## Advanced Filters

These parameters allow for granular filtering beyond basic keywords.

### 5. Contract Type (`contract`)
*   **Usage:** `&contract=cdi`, `&contract=internship`, etc. (Can be repeated for multiple types).

### 6. Experience Level (`work_experience_code`)
*   **Usage:** `&work_experience_code=three_to_five_years`, `&work_experience_code=young_graduate`, etc.

### 7. Job category (`job_category_ids[]`)
*   **Usage:** `&job_category_ids[]=405` — macro families in the UI (e.g. Ingénierie, Technologie). IDs change with the site; copy from the browser network tab when a filter is applied.

### 8. Job Function (`job_function_ids[]`)
*   **Usage:** `&job_function_ids[]=30` (For Software Development). See `jobteaser_filters.md` for the full ID mapping.

### 9. Language (`languages[]`)
*   **Usage:** `&languages[]=en` (For English). Note the array notation `[]`.

### 10. Study Levels (`study_levels`)
*   **Usage:** `&study_levels=4` (For Master's level).

### 11. Remote Work (`remote_types`)
*   **Usage:** `&remote_types=remote_partial` (Partial remote).


## Final Optimized Search URL Formula
To search for **"java"**, filtered for **native Easy Apply jobs**, **CDI/CDD contracts**, **3-5 years experience**, sorted by **recency**:
`https://www.jobteaser.com/fr/job-offers?candidacy_type=INTERNAL&q=java&contract=cdi&contract=cdd&work_experience_code=three_to_five_years&sort=recency&page=1`

Refer to [jobteaser_filters.md](jobteaser_filters.md) for a full catalog of all filter IDs (Duration, Start Date, Sectors, Functions, etc.).

