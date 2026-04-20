# JobTeaser Application Flow & Cloudflare Evasion Analysis

This document summarizes research into JobTeaser's bot detection mechanisms, interface structure, and evasion strategies, specifically targeting automated extraction of job application forms.

## 1. How Cloudflare Detects Headless Browsers
When navigating to JobTeaser, Cloudflare's Turnstile and Datadome run a series of checks:
- **`navigator.webdriver` Flag**: Standard Selenium sets this to `true`.
- **Browser Fingerprinting**: Discrepancies in `navigator.plugins`, `navigator.languages`, or WebGL execution behavior reveal automation.
- **IP Reputation**: Even with flawless behavior simulation (like random mouse tracking or typing delays), Cloudflare hard-blocks datacenter/cloud IP addresses on deep, authenticated pages.

## 2. Evasion Strategy
Based on subagent research, the initial login portal `https://www.jobteaser.com/fr/users/sign_in` does not immediately block bots if human-like typing and delays are simulated. 
However, **Direct Page Protection** triggers a strict "Test de sécurité" upon clicking job offers. 

**The Solution:**
- **Local Execution:** Avoid cloud environments and execute the code using your local residential connection.
- **Anti-Detect Tools:** Pair `undetected-chromedriver` with **Ungoogled Chromium** (a variant stripped of Google web services and telemetry).
- *Alternative:* Use `nodriver` (a direct Chrome DevTools Protocol implementation) if `undetected-chromedriver` gets flagged.

## 3. Searching & Filters on JobTeaser
- Job lists live in `<ul class="PageContent_results__zSSNO">` elements.
- Target opportunities that display the **"Candidature simplifiée"** (Internal Apply) badge, as these don't redirect to external applicant tracking systems like Workday.
- URL Parameter Navigation works best: `?candidacy_type=INTERNAL&page=1` instead of manually finding "next page" buttons.

## 4. The "Apply" (Postuler) Structure
When clicking apply (`jobad-DetailView__CandidateActions__Buttons_apply_internal_candidacy`), JobTeaser opens a structured form modal. 

To automate applications, the script must parse the DOM dynamically before the final submission click to identify:
1. **CV Uploads**: `<input type="file" ...>`
2. **Custom Questions**: `<textarea>` inputs requiring motivation snippets.
3. **Contact Fields**: `<input type="tel">` and basic text inputs.
4. **Final Submit Action**: Clicking the confirmation element (`jobad-DetailView__ApplicationFlow__Buttons__apply_button`).
