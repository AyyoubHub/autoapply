# Specification: Core APEC Automation Enhancements & Stabilization

## Goal
The goal of this track is to refine and stabilize the APEC automation workflow to achieve a high-quality, high-volume application experience. This includes enhancing job relevance through semantic analysis and improving reliability via local history tracking and more robust UI interaction.

## Scope
- **AI-Powered Semantic Filtering:** Replace or augment basic keyword matching with a deep analysis of job descriptions using Gemini-2.0-flash.
- **Local Application History:** Implement a persistence layer to track successfully applied jobs locally, preventing redundant actions and improving efficiency.
- **Robust UI Selectors:** Transition to text-based and more resilient button matching for the APEC application modal.
- **Error Recovery & Logging:** Enhance the tool's ability to self-heal from session crashes and provide clearer diagnostic feedback.

## Out of Scope
- Initial stabilization of the JobTeaser module (to be handled in a future track).
- Integration of new job platforms (LinkedIn, Indeed, etc.).
- Complex form filling beyond the standard "Easy Apply" modal.

## Success Criteria
- **High Relevance:** Gemini accurately filters out at least 95% of irrelevant job offers (e.g., mismatched seniority, contract types like freelance/internship if undesired).
- **Near-Zero Redundancy:** The local history successfully prevents 100% of duplicate application attempts for known URLs.
- **Improved Uptime:** The bot successfully completes runs of 20+ applications without manual intervention, even if a session crash occurs.
- **Resilience:** The bot survives minor APEC UI changes that would break static CSS-based selectors.

## User Manual Verification Protocol
1.  **Run Discovery:** Execute a run with multiple keywords and verify the scoring and discovery logic.
2.  **AI Check:** Observe logs to confirm Gemini is correctly filtering jobs based on title and description snippets.
3.  **Apply Verification:** Verify successful applications on the APEC website's "Candidatures envoyées" section.
4.  **History Check:** Confirm that already-applied jobs are skipped in subsequent runs, both via local JSON and on-page detection.
5.  **Robustness Check:** Artificially trigger a session loss (e.g., by closing the browser manually) and confirm the bot recovers and finishes the remaining queue.
