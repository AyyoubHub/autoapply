# APEC Search URL Structure Analysis

This document details the exact URL parameters required to programmatically search jobs on APEC, specifically focusing on isolating "Easy Apply" (native APEC) applications from external partner redirects.

## Base URL
`https://www.apec.fr/candidat/recherche-emploi.html/emploi`

## Core Parameters

### 1. Search Query (`motsCles`)
*   **Purpose:** The main keyword search (job title, technologies, company).
*   **Usage:** `?motsCles=java` (Must be URL-encoded, e.g., using `urllib.parse.quote_plus`).

### 2. Contract Type (`typesContrat`)
*   **Purpose:** Filters the type of employment contract.
*   **Known IDs:**
    *   **CDI**: `101888`
    *   **CDD**: `101889`
    *   **Alternance**: `101891`
    *   **Intérim**: `101890`
*   **Usage:** `&typesContrat=101888`

### 3. Source / Recruiter Type (`typesConvention`)
*   **Purpose:** Defines who is posting the job (direct company, recruiting agency, external partner).
*   **Known IDs:**
    *   `143684`: Entreprise (Direct Company)
    *   `143685`: Cabinet de recrutement (Recruitment Agency)
    *   `143686`: Agence d'emploi (Employment Agency)
    *   `143687`: SSII / ESN (IT Services Company)
    *   `143706`: Partenaire (External Partner Aggregator)
*   **CRITICAL FIX:** To **exclude** external partner jobs (like WelcomeToTheJungle or HelloWork redirects), the `143706` ID **must be omitted** from the URL.

### 4. Pagination (`page`)
*   **Purpose:** Handles navigating through search result pages.
*   **Indexing:** APEC pagination is **zero-indexed**.
    *   Page 1 = `&page=0`
    *   Page 2 = `&page=1`

### 5. Sorting (`sortsType`)
*   **Purpose:** Orders the results.
*   **Known Values:**
    *   Date: `DATE`
    *   Score/Relevance: `SCORE`

## Hardcoded Parameter Issue Discovered
During analysis, we discovered that the current `apec.py` script hardcodes the parameter `&niveauxExperience=101881` into the base URL. 
*   **Impact:** The ID `101881` specifically restricts the search to **"Jeune diplômé"** (recent graduates). This is why the script was processing very few jobs (e.g., only 16 jobs). This parameter must be removed unless explicitly chosen by the user.

## Final Optimized Search URL Formula
To search for **"java"**, filtered by **CDI**, **sorted by date**, restricted strictly to **native APEC jobs** (excluding partners), and allowing all experience levels:
`https://www.apec.fr/candidat/recherche-emploi.html/emploi?typesConvention=143684&typesConvention=143685&typesConvention=143686&typesConvention=143687&motsCles=java&typesContrat=101888&sortsType=DATE&page=0`
